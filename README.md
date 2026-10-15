# Visitors Book (Python)

A digital visitors book for reception. Staff log in, check visitors in and out,
see who is still inside today, and search past visits.

Built with Flask, raw SQL on MySQL (PyMySQL) and Tailwind CSS.

## Features

- Staff login (accounts are created with a script, there is no sign-up page)
- Check in a visitor: full name, phone, organisation, person visiting, purpose.
  Time in is recorded automatically.
- Today's visitors, newest first, with counts of visitors today and still inside
- One-click check-out (time out recorded automatically)
- Search past visits by name, phone and/or date range

## Requirements

- Python 3.12 or newer
- XAMPP (only MySQL is needed)

## Setup

1. Clone the repository and open the folder in a terminal.

2. Create and activate a virtual environment, then install the packages:

       python -m venv venv
       venv\Scripts\activate          # Windows
       source venv/bin/activate       # macOS / Linux
       pip install -r requirements.txt

3. Copy `.env.example` to `.env` and fill in the values:

       copy .env.example .env         # Windows
       cp .env.example .env           # macOS / Linux

   Generate the secret key with:

       python -c "import secrets; print(secrets.token_hex(32))"

   With a default XAMPP install, `DB_USER=root` and `DB_PASSWORD` is left empty.

4. Create the database: start MySQL in XAMPP, open http://localhost/phpmyadmin,
   go to the SQL tab and run the contents of `database/schema.sql`.

5. Create the staff account (run once):

       python database/seed_user.py

6. Run the app:

       flask --app app run

   Open http://127.0.0.1:5000/

## Default login

    Email:    admin@example.com
    Password: ChangeMe123!

Change this password for anything other than local testing.

## Project structure

    app.py                       routes, CSRF check, login check, validation
    db.py                        MySQL connection (one per request)
    database/schema.sql          creates the database and tables
    database/seed_user.py        creates the staff account
    templates/base.html          shared layout and navigation
    templates/_visits_table.html visits table shared by Today and Search
    templates/*.html             login, today, check-in and search pages