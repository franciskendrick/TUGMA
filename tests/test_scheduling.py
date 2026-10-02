from src.scheduling import ScheduleManager


schedule_manager = ScheduleManager()


student_schedule = schedule_manager.get_student_schedule(1)

print("Student Schedule:")
for slot in student_schedule:
    print(
        slot["day"],
        slot["start_time"].strftime("%H:%M"),
        "-",
        slot["end_time"].strftime("%H:%M"),
        slot["subject_code"]
    )


student_free = schedule_manager.get_student_free_slots(1)

print("\nStudent Free Time:")
for slot in student_free:
    print(
        slot["day"],
        slot["start_time"].strftime("%H:%M"),
        "-",
        slot["end_time"].strftime("%H:%M")
    )


tutor_available = schedule_manager.get_tutor_available_slots(1)

print("\nTutor Availability:")
for slot in tutor_available:
    print(
        slot["day"],
        slot["start_time"].strftime("%H:%M"),
        "-",
        slot["end_time"].strftime("%H:%M")
    )


common_slots = schedule_manager.find_common_slots(
    tutor=1,
    student=1
)

print("\nCommon Available Times:")

if common_slots:
    for slot in common_slots:
        print(
            slot["day"],
            slot["start_time"].strftime("%H:%M"),
            "-",
            slot["end_time"].strftime("%H:%M")
        )
else:
    print("No common available time.")


schedule_manager.close()