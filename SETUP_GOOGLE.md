# Google Forms setup for the staff-controlled workflow

The launch workflow is semi-automated. The app does not create Google Forms
through an API and does not send live email. Instead, it prepares the files staff
need to run the intake safely:

- form template CSV
- recipient list CSV
- email text
- short send instructions
- response CSV upload/parsing after forms are collected

This avoids Google Cloud setup, OAuth consent screens, token expiration, sender
permission issues, and Streamlit Secrets complexity.

## Student preference collection

1. In the app, open **3 Prospective students**.
2. Enter or import student names and emails.
3. Download `student_preference_form_template.csv`.
4. Build a Google Form manually using the template questions.
5. Download the student recipients CSV and email text.
6. Replace the email body's form-link placeholder with the real Google Form URL.
7. Send the email through Gmail or Outlook.
8. In Google Forms, open **Responses** and link responses to a Google Sheet.
9. After responses arrive, download the Sheet as CSV.
10. Upload that response CSV back in **3 Prospective students**.

The app converts the response CSV into:

- `preferences.csv`
- `student_interests.csv`

## Faculty availability collection

1. In the app, open **2 Build visit days** and confirm the meeting windows.
2. Open **4 Faculty availability**.
3. Enter or import faculty names and emails.
4. Download `faculty_availability_form_template.csv`.
5. Build a Google Form manually using the template questions.
6. Download the faculty recipients CSV and email text.
7. Replace the email body's form-link placeholder with the real Google Form URL.
8. Send the email through Gmail or Outlook.
9. Link the Google Form Responses tab to a Google Sheet.
10. After responses arrive, download the Sheet as CSV.
11. Upload that response CSV back in **4 Faculty availability**.

The app converts the response CSV into:

- `availability.csv`

## Why this workflow is preferred for handoff

- Staff can inspect every form and email before sending.
- No Google Cloud project is required.
- No OAuth token has to be generated, stored, refreshed, or debugged.
- Email sending remains under the staff account's normal Gmail/Outlook workflow.
- If something goes wrong, staff can fix the form or email directly.
- The CSV fallback remains visible and easy to test.

## Future enhancement

A later version could automate Google Form creation or email sending, but that
should only be added after the staff-controlled workflow has been tested with
realistic data and the team has confirmed who owns credentials, sender accounts,
and production support.
