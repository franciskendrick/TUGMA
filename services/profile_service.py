"""Read-only tutor profile aggregation and presentation helpers."""

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
