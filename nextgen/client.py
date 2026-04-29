import logging
import mimetypes
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

import requests

from .config import CONFIG
from .models import FileTypes
from .queries import (
    GET_ASSIGNMENT_DETAILS_QUERY,
    GET_ATTENDANCE_PERCENTAGES_QUERY,
    GET_BEHAVIOUR_INCIDENTS_QUERY,
    GET_STUDENT_ASSIGNMENT_QUERY,
    GET_STUDENT_TASKS_QUERY,
    GET_USER_COURSES_QUERY,
)

logger = logging.getLogger(__name__)


class ToddleError(RuntimeError):
    pass


class ToddleClient:
    def __init__(self, token: Optional[str] = None, user_id: Optional[str] = None, org_id: Optional[str] = None):
        self.token = token
        self.user_id = user_id
        self.org_id = org_id
        self._session = requests.Session()
        self._session.headers.update(CONFIG.default_headers)

    def close(self) -> None:
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def _request(
        self,
        endpoint: str,
        payload: Union[Dict[str, Any], List[Any]],
        custom_headers: Optional[Dict[str, str]] = None,
        timeout: int = CONFIG.default_timeout,
        token: Optional[str] = None,
    ) -> Union[Dict[str, Any], List[Any]]:
        headers = dict(custom_headers or {})
        auth_token = token or self.token
        if auth_token:
            headers["authorization"] = f"Bearer {auth_token}"
        response = self._session.post(
            f"{CONFIG.base_url}{endpoint}",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _mime_type(file_name: str) -> str:
        mime_type, _ = mimetypes.guess_type(file_name)
        if mime_type:
            return mime_type
        ext = os.path.splitext(file_name)[1].lower()
        return {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".ppt": "application/vnd.ms-powerpoint",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".zip": "application/zip",
            ".rar": "application/x-rar-compressed",
            ".7z": "application/x-7z-compressed",
            ".mp3": "audio/mpeg",
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".svg": "image/svg+xml",
            ".webp": "image/webp",
        }.get(ext, "application/octet-stream")

    @staticmethod
    def _graphql_headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {"x-tod-lang": "en-US", "x-tod-source": "WEB"}
        if extra:
            headers.update(extra)
        return headers

    @staticmethod
    def _extract_first_response(data: Union[Dict[str, Any], List[Any]]) -> Dict[str, Any]:
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                return first
        if isinstance(data, dict):
            return data
        return {}

    def _graphql(self, query_name: str, variables: Dict[str, Any], query: str, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        payload = [{"operationName": query_name, "variables": variables, "query": query}]
        data = self._request("/graphql", payload, custom_headers=self._graphql_headers(extra_headers))
        return self._extract_first_response(data)

    @lru_cache(maxsize=64)
    def get_course_ids(self) -> List[str]:
        if not self.token or not self.user_id:
            raise ValueError("Token and user_id are required")
        data = self._graphql("getUserCourses", {"id": self.user_id, "type": "STUDENT"}, GET_USER_COURSES_QUERY)
        node = data.get("data", {}).get("node", {})
        return [course.get("id") for course in node.get("courses", []) if course.get("id")]

    def fetch_toddle_tasks(self, course_ids: List[str], status: str) -> Dict[str, Any]:
        if not self.token or not self.user_id:
            raise ValueError("Token and user_id are required")
        variables = {
            "userId": self.user_id,
            "type": "STUDENT",
            "filters": {"completionStatus": "TODO", "status": status.upper(), "courseIds": course_ids, "searchText": "", "projectGroupIds": []},
            "first": CONFIG.max_page_size,
            "orderByDirection": "ASC",
        }
        data = self._graphql("getStudentTasks", variables, GET_STUDENT_TASKS_QUERY, {"x-tod-lsn": "1BCF/F46D1688"})
        tasks_edges = data.get("data", {}).get("node", {}).get("tasks", {}).get("edges", [])
        homeworks: Dict[str, Dict[str, Any]] = {}
        for edge in tasks_edges:
            item = edge.get("item", {})
            if edge.get("itemType") != "STUDENT_ASSIGNMENT":
                continue
            assignment = item.get("assignment", {})
            content = assignment.get("content", {})
            title = content.get("title", {}).get("value")
            homeworks[item.get("id")] = {
                "id": item.get("id"),
                "id2": assignment.get("id"),
                "title": title,
                "coursename": assignment.get("course", {}).get("title"),
                "hwname": title,
                "duedate": assignment.get("deadline"),
                "submitted": item.get("isSubmitted"),
                "submit-status": item.get("status"),
                "hw-publish-time": assignment.get("state", {}).get("publishedAt"),
                "cansubmit": assignment.get("isStudentSubmissionEnabled"),
            }
        return {"success": True, "total_count": len(homeworks), "homeworks": homeworks}

    @staticmethod
    def from_class_code(class_code: str) -> "ToddleClient":
        payload = {"classCode": class_code, "codeType": "CODE"}
        headers = {"Origin": "https://web.toddleapp.cn", "Referer": "https://web.toddleapp.cn/"}
        session = requests.Session()
        session.headers.update(CONFIG.default_headers)
        resp = session.post(f"{CONFIG.base_url}/auth/v2/student/checkClassCode", json=payload, headers=headers, timeout=CONFIG.default_timeout)
        resp.raise_for_status()
        data = resp.json()
        items = data if isinstance(data, list) else [data]
        token = user_id = org_id = None
        for item in items:
            if not isinstance(item, dict):
                continue
            token = item.get("token") or token
            obj = item.get("data", {}) if isinstance(item.get("data", {}), dict) else {}
            user_id = obj.get("id") or user_id
            org_id = obj.get("org_id") or obj.get("organization_id") or org_id
            node = obj.get("node", {})
            if isinstance(node, dict) and node.get("__typename") == "Organization":
                org_id = node.get("id")
        session.close()
        if not token or not user_id:
            raise ToddleError("Unable to resolve token or user id")
        return ToddleClient(token=token, user_id=user_id, org_id=org_id)

    def get_submission_id(self, assignment_id: str) -> Optional[str]:
        data = self._graphql("getStudentAssignment", {"id": assignment_id}, GET_STUDENT_ASSIGNMENT_QUERY)
        return data.get("data", {}).get("node", {}).get("submissions", {}).get("edges", [{}])[0].get("id")

    def get_assignment_details(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        data = self._graphql("getAssignmentDetails", {"id": assignment_id}, GET_ASSIGNMENT_DETAILS_QUERY, {"x-tod-lsn": "1BD5/98288000"})
        assignment = data.get("data", {}).get("node")
        if not assignment:
            return None
        return {
            "id": assignment.get("id"),
            "title": assignment.get("content", {}).get("title", {}).get("value"),
            "deadline": assignment.get("deadline"),
            "publishedAt": assignment.get("publishedAt"),
            "state": assignment.get("state", {}).get("state"),
            "course": assignment.get("course", {}),
            "createdBy": assignment.get("createdBy", {}),
        }

    def get_attachments(self, assignment_id: str) -> List[Dict[str, Any]]:
        data = self._graphql("getStudentAssignment", {"id": assignment_id}, GET_STUDENT_ASSIGNMENT_QUERY)
        attachments: List[Dict[str, Any]] = []
        submissions = data.get("data", {}).get("node", {}).get("submissions", {}).get("edges", [])
        for edge in submissions:
            for group in edge.get("attachmentGroups", []):
                for attachment in group.get("attachments", []):
                    attachments.append({
                        "attachment_id": group.get("id"),
                        "file_name": attachment.get("name"),
                        "file_type": attachment.get("type"),
                        "url": attachment.get("url"),
                        "signed_url": attachment.get("signedUrl"),
                        "mime_type": attachment.get("mimeType"),
                    })
        return attachments

    def upload_file_to_assignment(
        self,
        submission_id: str,
        file_name: str,
        file_url: str,
        file_type: FileTypes,
        file_size: int,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = [{
            "operationName": "createAttachmentGroups",
            "variables": {
                "input": [{
                    "parentId": submission_id,
                    "parentType": "STUDENT_ASSIGNMENT_SUBMISSION",
                    "attachments": [{
                        "url": file_url,
                        "name": file_name,
                        "type": file_type.value,
                        "mimeType": mime_type or self._mime_type(file_name),
                        "metadata": {"size": file_size},
                    }],
                }],
            },
            "query": "mutation createAttachmentGroups($input: [AttachmentGroupInput!]) { platform { createAttachmentGroups(input: $input) { id metadata attachments { id name type mimeType url signedUrl thumbUrl title metadata streamUrl parentType isRead __typename } __typename } __typename } }",
        }]
        data = self._request(
            "/graphql",
            payload,
            custom_headers=self._graphql_headers({"cache-control": "no-cache", "pragma": "no-cache"}),
        )
        return {"success": True, "data": data, "message": "文件上传成功", "mime_type": mime_type or self._mime_type(file_name)}

    def delete_attachments(self, attachment_ids: List[str]) -> Dict[str, Any]:
        payload = [{
            "operationName": "deleteAttachmentGroups",
            "variables": {"attachmentGroupIds": attachment_ids},
            "query": "mutation deleteAttachmentGroups($attachmentGroupIds: [ID!]) { platform { deleteAttachmentGroups(input: {attachmentGroupIds: $attachmentGroupIds}) { warning isSuccess __typename } __typename } }",
        }]
        data = self._request(
            "/graphql",
            payload,
            custom_headers=self._graphql_headers({"cache-control": "no-cache", "pragma": "no-cache"}),
        )
        return {"success": True, "data": data, "message": "附件删除成功"}

    def submit_assignment(self, submission_id: str) -> Dict[str, Any]:
        payload = [{
            "operationName": "editStudentAssignmentSubmission",
            "variables": {"id": submission_id, "response": "", "status": "SUBMITTED", "checkForSimilarity": False, "isWorksheet": False},
            "query": "mutation editStudentAssignmentSubmission($id: ID!, $response: String, $status: STUDENT_ASSIGNMENT_SUBMISSION_ENUM, $statusMessage: CreateMessageInput, $checkForSimilarity: Boolean, $isWorksheet: Boolean) { platform { editStudentAssignmentSubmission(input: {id: $id, response: $response, status: $status, statusMessage: $statusMessage, checkForSimilarity: $checkForSimilarity, isWorksheet: $isWorksheet}) { id status submittedAt __typename } __typename } }",
        }]
        data = self._request("/graphql", payload, custom_headers=self._graphql_headers({"accept": "*/*", "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh-TW;q=0.6,zh;q=0.5"}))
        return {"success": True, "data": data, "message": "作业提交成功"}

    def unsubmit_assignment(self, submission_id: str) -> Dict[str, Any]:
        payload = [{
            "operationName": "editStudentAssignmentSubmission",
            "variables": {"id": submission_id, "response": "", "status": "DRAFT", "checkForSimilarity": False, "isWorksheet": False},
            "query": "mutation editStudentAssignmentSubmission($id: ID!, $response: String, $status: STUDENT_ASSIGNMENT_SUBMISSION_ENUM, $statusMessage: CreateMessageInput, $checkForSimilarity: Boolean, $isWorksheet: Boolean) { platform { editStudentAssignmentSubmission(input: {id: $id, response: $response, status: $status, statusMessage: $statusMessage, checkForSimilarity: $checkForSimilarity, isWorksheet: $isWorksheet}) { id status submittedAt __typename } __typename } }",
        }]
        data = self._request("/graphql", payload, custom_headers=self._graphql_headers({"accept": "*/*", "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh-TW;q=0.6,zh;q=0.5"}))
        return {"success": True, "data": data, "message": "作业取消提交成功"}

    def get_behaviour_incidents(self, first: int = 20) -> Dict[str, Any]:
        if not self.token or not self.org_id:
            raise ValueError("Token or OrgId not set")
        variables = {
            "id": self.org_id,
            "input": {"first": first, "filters": [{"searchText": ""}], "orderBy": "UPDATED_AT", "orderByDirection": "DESC"},
            "accessibleUsersInput": {},
        }
        data = self._graphql("getBehaviourIncidentFeed", variables, GET_BEHAVIOUR_INCIDENTS_QUERY, {"x-tod-lsn": "1BCF/F46D1688"})
        edges = data.get("data", {}).get("node", {}).get("behaviourIncidentFeed", {}).get("edges", [])
        incidents = []
        for edge in edges:
            node = edge.get("node", {})
            creator = node.get("createdBy", {})
            incidents.append({
                "id": node.get("id"),
                "uid": node.get("uid"),
                "title": node.get("title"),
                "type": node.get("category", {}).get("rootCategory", {}).get("sentiment", {}).get("label"),
                "points": node.get("severity", {}).get("level", 0),
                "created_by": " ".join(filter(None, [creator.get("firstName"), creator.get("middleName"), creator.get("lastName")])) ,
                "created_at": node.get("createdAt"),
            })
        return {"success": True, "total_count": data.get("data", {}).get("node", {}).get("behaviourIncidentFeed", {}).get("totalCount", 0), "incidents": incidents}

    def get_attendance_percentages(self, student_id: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, overall_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        student_id = student_id or self.user_id
        if not self.token or not student_id:
            raise ValueError("Token and student_id are required")

        variables = {
            "studentId": student_id,
            "filters": filters or {},
            "overAllPresenceFilter": overall_filters or filters or {},
        }
        data = self._graphql(
            "getStudentAttendanceStatisticsV2",
            variables,
            GET_ATTENDANCE_PERCENTAGES_QUERY,
            {"x-tod-lsn": "2122/C239280"},
        )

        attendance = data.get("data", {}).get("node", {}).get("attendanceV2", {})
        categories = attendance.get("categorySummary", {}).get("percentageItems", [])
        category_percentages = {}
        for item in categories:
            category = item.get("category", {})
            label = category.get("label")
            percentage = item.get("percentage")
            if label is not None and percentage is not None:
                category_percentages[label] = percentage

        overall_presence = attendance.get("overallPresence", {}).get("presenceOverview", {})

        return {
            "success": True,
            "student_id": student_id,
            "overall_presence": {
                "present": overall_presence.get("presencePercentage"),
                "absent": overall_presence.get("absencePercentage"),
                "present_count": overall_presence.get("presenceNumber"),
                "absent_count": overall_presence.get("absenceNumber"),
                "total_count": overall_presence.get("totalCount"),
            },
            "category_percentages": category_percentages,
        }
