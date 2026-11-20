import sqlite3

import pytest

from services.migrations import SCHEMA_PATH, SEED_PATH, migrate
from services.profile_service import get_tutor_profile_data
from src.database import Database


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "profile.db"
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.executescript(SEED_PATH.read_text(encoding="utf-8"))
    connection.commit()
    connection.close()
    database = Database(path)
    migrate(database)
    yield database
    database.close()


def test_seeded_tutor_rating_aggregation(db):
    summary = db.get_tutor_rating_summary(1)
    assert summary["rated_sessions"] == 23
    assert summary["rated_students"] == 7
    assert 4.0 <= summary["overall_rating"] <= 5.0

    breakdown = {row["criterion"]: row for row in db.get_tutor_rating_breakdown(1)}
    assert set(breakdown) == {
        "Clear explanations", "Patience", "Prepared for the session",
        "Uses worked examples", "Arrives on time",
    }
    assert breakdown["Clear explanations"]["average_rating"] > 4.8
    assert breakdown["Arrives on time"]["average_rating"] < breakdown["Clear explanations"]["average_rating"]


def test_certificate_status_and_progress(db):
    certificates = db.get_tutor_certificates(1)
    earned = [row for row in certificates if row["status"] == "earned"]
    progress = [row for row in certificates if row["status"] == "in_progress"]
    assert len(earned) == 4
    assert len(progress) == 2
    assert {row["progress_value"] for row in progress} == {3, 6}
    assert all(row["earned_date"] is not None for row in earned)
    assert all(row["earned_date"] is None for row in progress)


def test_profile_service_shapes_and_clamps_progress(db):
    data = get_tutor_profile_data(db, 1)
    assert data["profile"]["name"] == "Tutor A"
    assert data["rating"]["rated_sessions"] == 23
    always_on_time = next(c for c in data["certificates"] if c["certificate_code"] == "ALWAYS_ON_TIME")
    assert always_on_time["progress_percent"] == 60
    assert always_on_time["progress_value"] == 6
    assert get_tutor_profile_data(db, 999) is None


def test_invalid_review_score_is_rejected(db):
    review_id = db.fetch_one("SELECT review_id FROM tutor_reviews LIMIT 1")["review_id"]
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO tutor_review_scores (review_id, criterion, score) VALUES (?, ?, ?)",
            (review_id, "Patience", 6),
        )


def test_invalid_certificate_progress_is_rejected(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO tutor_certificates (tutor_id, certificate_id, status, progress_value) "
            "VALUES (1, 5, 'in_progress', -1)"
        )


def test_tutor_without_reviews_returns_empty_aggregates(db):
    summary = db.get_tutor_rating_summary(2)
    assert summary["overall_rating"] is None
    assert summary["rated_sessions"] == 0
    assert summary["rated_students"] == 0
    assert db.get_tutor_rating_breakdown(2) == []
    assert db.get_tutor_certificates(2) == []


def test_student_profile_retrieval_includes_academic_and_account_data(db):
    from services.profile_service import get_student_profile_data

    data = get_student_profile_data(db, 1)
    assert data is not None
    assert data["profile"]["name"] == "Student A"
    assert data["profile"]["course"] == "BCS"
    assert data["profile"]["bio"]
    assert data["profile"]["email"] is None  # Seed profiles need not have login accounts.
    assert data["languages"] == ["English", "Filipino"]
    assert any(row["subject_code"] == "S-CSPC212" for row in data["subjects"])
    assert any(row["day"] == "Monday" for row in data["schedule"])


def test_student_profile_tabs_exclude_tutor_features():
    from services.profile_service import get_profile_tabs

    tabs = get_profile_tabs("Learning")
    assert tabs == ("About", "Info", "Classes")
    assert "Reviews" not in tabs
    assert "Certificates" not in tabs


def test_tutor_profile_tabs_remain_unchanged():
    from services.profile_service import get_profile_tabs

    assert get_profile_tabs("Tutoring") == (
        "About", "Info", "Classes", "Reviews", "Certificates"
    )


def test_student_profile_handles_missing_optional_content(db):
    from services.profile_service import get_student_profile_data

    db.execute(
        "UPDATE students SET bio=NULL, study_notes=NULL, interests=NULL WHERE student_id=?",
        (7,),
    )
    data = get_student_profile_data(db, 7)
    assert data["profile"]["bio"] is None
    assert data["profile"]["study_notes"] is None
    assert data["profile"]["interests"] is None
    assert data["subjects"]
    assert data["schedule"]


def test_student_profile_missing_record_returns_none(db):
    from services.profile_service import get_student_profile_data

    assert get_student_profile_data(db, 999) is None
