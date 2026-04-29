# ToddleAPI NextGen

A cleaner refactor of ToddleAPI focused on maintainability, speed, and easier extension.

## Highlights

- Smaller module layout
- Reusable session-backed client
- Less repeated setup code
- Cleaner config and model separation
- GraphQL query constants extracted
- Compatibility layer for legacy-style access
- Attendance summary helper included

## Installation

```bash
pip install requests
```

## Structure

- `nextgen/config.py` - shared config and defaults
- `nextgen/models.py` - enums and data models
- `nextgen/queries.py` - GraphQL query constants
- `nextgen/client.py` - main client implementation
- `nextgen/compat.py` - legacy compatibility helpers
- `nextgen/__init__.py` - public exports
- `demo.py` - runnable usage demo

## Quick Start

```python
from nextgen import ToddleClient

client = ToddleClient.from_class_code("YOUR_CLASS_CODE")
courses = client.get_course_ids()
tasks = client.fetch_toddle_tasks(courses, "upcoming")
```

## Attendance Percentages

The new `get_attendance_percentages()` helper returns a structured response based on `categorySummary`.

Example output:

```python
{
    "success": True,
    "student_id": "233465177817817775",
    "overall_presence": {
        "present": 97.32,
        "absent": 2.68,
        "present_count": 943,
        "absent_count": 26,
        "total_count": 969,
    },
    "category_percentages": {
        "Present": 94.63,
        "Late": 1.75,
        "Unexcused": 0.41,
        "Excused": 3.2,
    },
}
```

## Demo

Run the demo script to see the intended workflow:

```bash
python demo.py
```

## Example Usage

```python
from nextgen import ToddleClient

client = ToddleClient.from_class_code("YOUR_CLASS_CODE")
attendance = client.get_attendance_percentages(
    filters={
        "startDate": "2025-08-11",
        "endDate": "2026-04-29",
        "isPeriodByAttendance": True,
        "academicYearIds": "221002766829555665",
        "curriculumProgramIds": "233817334190516058",
    },
    overall_filters={
        "startDate": "2025-08-11",
        "endDate": "2026-04-29",
        "isPeriodByAttendance": True,
        "academicYearIds": "221002766829555665",
        "curriculumProgramIds": "233817334190516058",
    },
)
print(attendance["category_percentages"])
```

## Compatibility

For older code, `ToddleAPI` is still available through the compatibility layer.
