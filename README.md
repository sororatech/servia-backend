# servia-backend

## About ServiaAI

ServiaAI is an AI-powered hotel recruitment platform that transforms 
the way hotels attract, screen, and hire talent. Instead of spending 
hours manually reviewing CVs and coordinating interviews, ServiaAI 
automates the entire hiring process - from the moment a candidate 
applies to the final hiring decision.

Candidates register on the platform, upload their CV, and submit a 
short video introduction. ServiaAI's AI engine instantly analyzes 
each CV, scores it from 0 to 100 based on hospitality-specific 
criteria, and provides personalized feedback directly to the candidate. 
Shortlisted candidates are automatically invited for an AI-assisted 
Google Meet interview where a bot joins silently, transcribes the 
conversation in real time, and suggests follow-up questions to the 
recruiter. After the interview, a full AI report is generated with 
a hiring recommendation.

The result is a faster, fairer, and more data-driven hiring process 
that saves hotel HR teams hours of manual work while ensuring the 
best candidates are identified efficiently.

## Prerequisites
- Python 3.10 or higher
- pip
- Git

## Setup Steps

### 1. Clone the repository
git clone https://github.com/sororatech/servia-backend
cd servia-backend

### 2. Create and activate virtual environment
python -m venv venv

# Mac/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

### 3. Install dependencies
pip install -r requirements.txt

### 4. Run database migrations
python manage.py migrate

### 5. Start the development server
python manage.py runserver

## Test Command
Open your browser and go to:
http://localhost:8000

Expected result: Page shows "Hello Sorora Tech"

## Tech Stack
- Python 3.11+
- Django 4.2
- Django REST Framework
- SQLite (local development)
- PostgreSQL (production — Heroku)

## Branch Strategy
- main — production only
- staging — pre-production testing
- develop — integration branch
- feature/xxx — one branch per task

## Team
Sorora Tech — ServiaAI Project