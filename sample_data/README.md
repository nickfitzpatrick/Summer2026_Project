# Sample data

Existing small samples:

- `test_students.csv`
- `test_faculty.csv`
- `test_preferences.csv`
- `test_availability.csv`
- `test_student_requests.csv`

Full staff workflow test samples:

- `staff_test_students_40.csv`: 40-student recipient list for the Prospective Students tab.
- `staff_test_student_google_responses_40.csv`: simulated Google Sheets CSV export from the student preference form.
- `staff_test_faculty_google_responses_10.csv`: simulated Google Sheets CSV export from the faculty availability form.

Scheduler-ready test samples:

- `staff_test_scheduler_faculty_10.csv`
- `staff_test_scheduler_availability_10.csv`
- `staff_test_scheduler_preferences_40.csv`
- `staff_test_scheduler_students_40.csv`
- `staff_test_student_interests_40.csv`

Recommended testing paths:

1. Semi-automated response upload path:
   - Upload `staff_test_students_40.csv` in tab 3.
   - Upload `staff_test_student_google_responses_40.csv` as the student response CSV.
   - Upload `staff_test_faculty_google_responses_10.csv` as the faculty response CSV after entering/importing matching faculty.
   - Use parsed response data in tab 5.

2. Direct scheduler CSV path:
   - In tab 5, upload `staff_test_scheduler_faculty_10.csv`, `staff_test_scheduler_availability_10.csv`, `staff_test_scheduler_preferences_40.csv`, and optionally `staff_test_scheduler_students_40.csv`.
