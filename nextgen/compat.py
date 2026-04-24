from .client import ToddleClient, ToddleError
from .models import FileTypes


class ToddleAPI:
    @staticmethod
    def getTokenAndUserIDFromClassCode(class_code: str):
        client = ToddleClient.from_class_code(class_code)
        return {
            "success": True,
            "token": client.token,
            "userId": client.user_id,
            "orgId": client.org_id,
        }
