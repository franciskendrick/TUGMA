
from src.sets import SetOperations


def test_subject_intersection():
    operations = SetOperations()

    tutor_subjects = {"CAL101", "PHY101", "CS101"}
    student_needs = {"CAL101", "CHEM101"}

    result = operations.subject_intersection(
        tutor_subjects,
        student_needs
    )

    assert result == {"CAL101"}
    assert bool(result) is True


def test_language_intersection():
    operations = SetOperations()

    tutor_languages = {"English", "Filipino", "Japanese"}
    student_languages = {"Filipino", "English"}

    result = operations.language_intersection(
        tutor_languages,
        student_languages
    )

    assert result == {"English", "Filipino"}


def test_availability_intersection():
    operations = SetOperations()

    student_free = [
        {
            "day": "Monday",
            "start_time": "12:00",
            "end_time": "14:00"
        }
    ]

    tutor_available = [
        {
            "day": "Monday",
            "start_time": "12:15",
            "end_time": "13:30"
        }
    ]

    result = operations.availability_intersection(
        student_free,
        tutor_available
    )

    assert result == [
        {
            "day": "Monday",
            "start_time": "12:15",
            "end_time": "13:30"
        }
    ]


if __name__ == "__main__":
    test_subject_intersection()
    test_language_intersection()
    test_availability_intersection()

    print("All set operation tests passed.")
