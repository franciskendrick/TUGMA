import sys
from pathlib import Path

# Resolve project root and append to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import Database


def run_m2_verification():
    db = Database()

    print("==========================================")
    print("      TUGMA MILESTONE 2 RETRIEVAL TEST    ")
    print("==========================================\n")

    # 1. Fetch Students
    print("[1] STUDENTS")
    students = db.fetch_all("SELECT * FROM students")
    for s in students:
        print(f"  ID: {s['student_id']} | Name: {s['name']} | Level: {s['grade_level']} | Course: {s['course']}")

    # 2. Fetch Tutors & Capacities
    print("\n[2] TUTORS & CAPACITY")
    tutors = db.fetch_all("SELECT * FROM tutors")
    for t in tutors:
        print(f"  ID: {t['tutor_id']} | Name: {t['name']} | Verified: {t['verified']} | Capacity: {t['capacity']}")

    target_student_id = 1
    target_tutor_id = 1

    # 3. Student -> Subjects
    print(f"\n[3] STUDENT {target_student_id} NEEDED SUBJECTS")
    s_subjects = db.fetch_all(
        """
        SELECT s.subject_code, s.subject_name 
        FROM student_subjects ss
        JOIN subjects s ON ss.subject_id = s.subject_id
        WHERE ss.student_id = ?
        """,
        (target_student_id,)
    )
    for sub in s_subjects:
        print(f"  - [{sub['subject_code']}] {sub['subject_name']}")

    # 4. Student -> Schedule
    print(f"\n[4] STUDENT {target_student_id} ACADEMIC SCHEDULE")
    s_schedule = db.fetch_all(
        """
        SELECT ss.day, ss.start_time, ss.end_time, s.subject_code
        FROM student_schedule ss
        JOIN subjects s ON ss.subject_id = s.subject_id
        WHERE ss.student_id = ?
        ORDER BY ss.day, ss.start_time
        """,
        (target_student_id,)
    )
    for sch in s_schedule:
        print(f"  - {sch['day']}: {sch['start_time']}-{sch['end_time']} ({sch['subject_code']})")

    # 5. Student -> Languages
    print(f"\n[5] STUDENT {target_student_id} LANGUAGES")
    s_langs = db.fetch_all("SELECT language FROM student_languages WHERE student_id = ?", (target_student_id,))
    print(f"  - {[l['language'] for l in s_langs]}")

    # 6. Tutor -> Subjects
    print(f"\n[6] TUTOR {target_tutor_id} CAN TEACH")
    t_subjects = db.fetch_all(
        """
        SELECT s.subject_code, s.subject_name 
        FROM tutor_subjects ts
        JOIN subjects s ON ts.subject_id = s.subject_id
        WHERE ts.tutor_id = ?
        """,
        (target_tutor_id,)
    )
    for sub in t_subjects:
        print(f"  - [{sub['subject_code']}] {sub['subject_name']}")

    # 7. Tutor -> Availability
    print(f"\n[7] TUTOR {target_tutor_id} AVAILABILITY")
    t_avail = db.fetch_all(
        """
        SELECT day, start_time, end_time 
        FROM tutor_availability 
        WHERE tutor_id = ?
        ORDER BY day, start_time
        """,
        (target_tutor_id,)
    )
    for av in t_avail:
        print(f"  - {av['day']}: {av['start_time']}-{av['end_time']}")

    # 8. Tutor -> Languages
    print(f"\n[8] TUTOR {target_tutor_id} LANGUAGES")
    t_langs = db.fetch_all("SELECT language FROM tutor_languages WHERE tutor_id = ?", (target_tutor_id,))
    print(f"  - {[l['language'] for l in t_langs]}")

    db.close()
    print("\n==========================================")
    print("           M2 VERIFICATION COMPLETE       ")
    print("==========================================")


if __name__ == "__main__":
    run_m2_verification()