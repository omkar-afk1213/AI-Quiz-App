# AI Based Quiz Application

## About
This project is a full-stack Flask web application that generates AI-based multiple-choice quizzes from a user-defined topic. It uses free AI services, stores quiz results in SQLite, and gives students or learners a clean interface to take quizzes, review answers, and track their performance over time.

The app includes role-based access for administrators and regular users, a quiz generator powered by Gemini or OpenAI, and deployment guidance for free hosting on Render.

## Features
- AI-generated quiz questions using Google Gemini or OpenAI
- Login, registration, and admin/user role separation
- SQLite database with auto-initialization on first run
- Topic-based quiz generation with 5, 10, 15, or 20 questions
- Timed quiz flow with progress tracking
- Score review with explanation and answer highlights
- User quiz history and performance analysis
- Admin dashboard, user management, and AI model settings
- Bootstrap 5 responsive UI
- Free Render deployment configuration

## Free Tools Used
- Python 3.11 — FREE — https://www.python.org
- Flask — FREE — https://flask.palletsprojects.com
- SQLite — FREE — built into Python
- Bootstrap 5 — FREE — https://getbootstrap.com
- Google Gemini API — FREE — https://aistudio.google.com
- OpenAI API — FREE tier available — https://platform.openai.com
- Render.com — FREE tier — https://render.com
- GitHub — FREE — https://github.com
- VS Code — FREE — https://code.visualstudio.com
- Gunicorn — FREE — https://gunicorn.org

## Local Setup (Step by Step)
1. Install Python 3.11 from python.org (free)
2. Clone this repo: git clone https://github.com/YOUR-USERNAME/ai-quiz-app
3. cd ai-quiz-app
4. pip install -r requirements.txt
5. Copy .env.example to .env
6. Get FREE Gemini API key from https://aistudio.google.com (no credit card needed)
7. Add GEMINI_API_KEY=your_key_here to .env
8. python app.py
9. Open http://localhost:5000
10. Login with admin / Admin@123

## Get Free Gemini API Key
1. Go to https://aistudio.google.com
2. Sign in with Google account (free)
3. Click "Get API Key" → "Create API key"
4. Copy and paste into your .env file
5. No credit card, no payment required

## Get Free OpenAI API Key (Optional)
1. Go to https://platform.openai.com
2. Sign up for a free account or use a new account with free credits
3. Open API Keys and create a new key
4. Add to .env as OPENAI_API_KEY

## Deploy to Render (Free Public URL)
1. Push code to GitHub (free public repo)
2. Go to render.com and sign up for a free account
3. Click New → Web Service → Connect GitHub repo
4. Render detects render.yaml automatically
5. Add GEMINI_API_KEY in Render environment variables
6. Click Deploy
7. Your live URL: https://ai-quiz-app.onrender.com
8. Anyone can open the link and view the login page

## Default Login
- Admin: username=admin, password=Admin@123
- Create more users from Admin → Users panel

## Project Structure
- app.py — Flask entry point
- config.py — app configuration
- routes/ — authentication, admin, and quiz routes
- models/ — database and data models
- services/ — AI integration and performance analysis
- templates/ — frontend pages
- static/ — CSS and JS assets
- database/schema.sql — SQLite schema

## Notes
- The app auto-creates the SQLite database on first run.
- The default admin account is seeded automatically.
- API keys are read from environment variables and never hardcoded.
- If Gemini fails, the app automatically tries OpenAI.
