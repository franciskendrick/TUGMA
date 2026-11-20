"""Read-only student and tutor profile aggregation and presentation helpers."""

from src.database import Database


def get_tutor_profile_data(db: Database, tutor_id: int) -> dict:
    """Collect tutor profile, rating aggregates, and certificate records."""
    profile = db.get_tutor_profile(tutor_id)
    if profile is None:
        return None

    summary = db.get_tutor_rating_summary(tutor_id)
    breakdown = db.get_tutor_rating_breakdown(tutor_id)
    certificates = db.get_tutor_certificates(tutor_id)

    return {
        "profile": dict(profile),
        "rating": {
            "overall": summary["overall_rating"] if summary else None,
            "rated_sessions": summary["rated_sessions"] if summary else 0,
            "rated_students": summary["rated_students"] if summary else 0,
            "criteria": [dict(row) for row in breakdown],
        },
        "certificates": [
            {
                **dict(row),
                "progress_value": min(row["progress_value"], row["target_value"]),
                "progress_percent": min(
                    100, round(100 * row["progress_value"] / row["target_value"])
                ),
            }
            for row in certificates
        ],
    }


STUDENT_PROFILE_TABS = ("About", "Info", "Classes")
TUTOR_PROFILE_TABS = ("About", "Info", "Classes", "Reviews", "Certificates")


def get_student_profile_data(db: Database, student_id: int) -> dict:
    """Collect student profile, registered subjects, languages, and class schedule."""
    profile = db.get_student_profile(student_id)
    if profile is None:
        return None

    return {
        "profile": dict(profile),
        "subjects": [dict(row) for row in db.get_student_subjects(student_id)],
        "languages": [row["language"] for row in db.get_student_languages(student_id)],
        "schedule": [dict(row) for row in db.get_student_class_schedule(student_id)],
        "tabs": STUDENT_PROFILE_TABS,
    }


def get_profile_tabs(active_mode: str) -> tuple:
    """Return tabs for the active profile mode, not merely available account roles."""
    return TUTOR_PROFILE_TABS if active_mode == "Tutoring" else STUDENT_PROFILE_TABS
