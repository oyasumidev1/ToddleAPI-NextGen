# ToddleAPI NextGen

A cleaner refactor of ToddleAPI focused on maintainability and speed.

## Highlights

- Smaller module layout
- Reusable session-backed client
- Less repeated setup code
- Cleaner config and model separation
- GraphQL query constants extracted
- Compatibility layer for legacy style access

## Structure

- `nextgen/config.py` - shared config and defaults
- `nextgen/models.py` - enums and data models
- `nextgen/queries.py` - GraphQL query constants
- `nextgen/client.py` - main client implementation
- `nextgen/compat.py` - legacy compatibility helpers
- `nextgen/__init__.py` - public exports
- `demo.py` - runnable demo of the intended workflow

## Installation

The refactor uses `requests`.

```bash
pip install requests
```

If you want to use the package directly from this folder, run Python from `ToddleAPI NextGen` so the `nextgen` package can be imported.

## Quick Start

```python
from nextgen import ToddleClient, FileTypes

client = ToddleClient.from_class_code("YOUR_CLASS_CODE")
courses = client.get_course_ids()
```

## Common Workflow

```python
from nextgen import ToddleClient

with ToddleClient.from_class_code("YOUR_CLASS_CODE") as client:
    courses = client.get_course_ids()
    tasks = client.fetch_toddle_tasks(courses, "upcoming")
    print(tasks)
```

## API Overview

### `ToddleClient.from_class_code(class_code)`
Create a logged-in client from a Toddle class code.

### `client.get_course_ids()`
Get the current student course IDs.

### `client.fetch_toddle_tasks(course_ids, status)`
Fetch homework/task data.

### `client.get_submission_id(assignment_id)`
Get the submission ID for a student assignment.

### `client.get_assignment_details(assignment_id)`
Fetch assignment details.

### `client.get_attachments(assignment_id)`
List attachments for a submission.

### `client.upload_file_to_assignment(...)`
Upload an attachment to a submission.

### `client.delete_attachments(attachment_ids)`
Delete attachment groups.

### `client.submit_assignment(submission_id)`
Submit a draft assignment.

### `client.unsubmit_assignment(submission_id)`
Revert a submission back to draft.

### `client.get_behaviour_incidents(first=20)`
Fetch behaviour incident feed data.

## Demo

A small demo script is included:

```bash
python demo.py
```

It prints the recommended flow and usage examples without making live network calls.

## Compatibility

Legacy-style access is available through `nextgen.compat` if needed for old naming patterns.

## Notes

- This package is still a refactor, so some returned structures are intentionally lightweight.
- The client reuses one `requests.Session` for better performance.
- GraphQL query strings are kept in one place for easier maintenance.
