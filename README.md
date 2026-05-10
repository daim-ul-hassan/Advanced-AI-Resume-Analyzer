# AI Resume Analyzer

`AI Resume Analyzer` is a learning-friendly web application that helps a user upload a resume, compare it against a job description, and receive a clear analysis with a score, strengths, weaknesses, and suggestions for improvement.

The project is designed to feel approachable to a student, teacher, or beginner who wants to understand what the system is doing without reading complex technical language first.

## What this project does

The app guides the user through a simple sequence:

1. Log in with a name and password.
2. Choose a visual theme.
3. Upload a resume file.
4. Build the resume vector base.
5. Paste a job description.
6. Run the analysis.
7. Review the score and improve the resume.

The analysis page gives:

- a score out of `100`
- clear strengths
- clear weaknesses
- practical recommendations to make the resume better

## Main idea behind the system

This project uses a retrieval-style workflow inspired by `RAG` and `LangChain`.

In simple words, the system does not only read the entire resume as one large block. Instead, it:

1. extracts the text from the uploaded resume
2. splits the text into smaller pieces
3. builds a searchable vector-style structure from those pieces
4. compares the resume against the job description
5. generates feedback from the most relevant parts

This makes the analysis more focused and more useful than a basic text comparison.

## What the user sees

### Starting screen

When the app first opens, the screen stays dark with white text. The user is asked for:

- name
- password
- theme

There is also a password visibility toggle so the user can show or hide the password while typing.

### Dashboard

The dashboard is the working area of the project. It allows the user to:

- upload a resume in `PDF`, `DOCX`, or `TXT`
- save the uploaded file
- build the vector base
- paste the target job description
- launch the analysis

### About page

The About section explains how the project works in a cleaner, more educational way. It includes:

- a short explanation
- a polished step-by-step flow chart
- a background activity log
- account actions at the bottom

### API key area

The left sidebar includes a separate API key bar for:

- `Gemini`
- `Groq`

These keys are stored only for the current browser session. They are cleared when the user logs out or when the browser session ends.

## Accounts and session behavior

This project now supports saved user profiles.

If a person logs in again with the same:

- name
- password

their saved workspace can be restored, including:

- selected theme
- uploaded resume state
- saved job description
- previous analysis result
- activity logs

### Logout

Logging out:

- ends the current session
- clears session-only API keys
- clears the visible job description field
- clears the previous results from the screen
- sends the user back to the starting page

### Revoke profile

The `Revoke profile` action permanently deletes the currently logged-in profile and its saved data, including:

- uploads
- logs
- vector base
- saved analysis
- saved profile information

## Project structure

```text
Resume Advanced/
├─ app/
│  ├─ main.py
│  ├─ models.py
│  ├─ services/
│  │  ├─ activity.py
│  │  ├─ parser.py
│  │  ├─ rag.py
│  │  └─ storage.py
│  └─ static/
│     ├─ app.js
│     ├─ index.html
│     └─ styles.css
├─ data/
├─ uploads/
├─ .env.example
├─ .gitignore
├─ index.py
├─ README.md
└─ requirements.txt
```

### Why the code is organized this way

- `main.py` handles the FastAPI routes
- `models.py` defines the data shapes used by the API
- `parser.py` reads resume files
- `rag.py` handles chunking, retrieval, and analysis logic
- `storage.py` keeps user profiles and saved workspace data organized
- `activity.py` manages the user-facing log history
- `app.js`, `styles.css`, and `index.html` handle the browser interface

This separation makes the project easier to understand, easier to improve, and cleaner to upload to GitHub.

## Running the project locally

### 1. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 2. Start the server

```powershell
python -m uvicorn app.main:app --reload
```

### 3. Open the app

Open this address in your browser:

```text
http://127.0.0.1:8000
```

## How to test the full workflow

Use this simple checklist:

1. Log in with a name and password.
2. Choose a theme.
3. Upload a resume file.
4. Click `Build vector base`.
5. Paste a job description.
6. Click `Launch analysis`.
7. Confirm that the score, strengths, weaknesses, and recommendations appear.
8. Refresh the page and confirm the workspace is restored.
9. Log out and confirm the screen resets.
10. Log back in and confirm saved data returns.

## Preparing for GitHub

This repo is now cleaner for version control:

- runtime cache files are ignored
- uploaded files are ignored
- saved accounts and user data are ignored
- environment secrets are ignored

That means you can push the project without accidentally uploading private user data.

## Preparing for Vercel

The project includes a simple root `index.py` entry file so the FastAPI app has a clear deployment entrypoint.

Before deployment:

1. push the repository to GitHub
2. import the repository into Vercel
3. add any environment variables you want to use later
4. deploy the project

## Important note about saved data

This app stores user workspace information in local project data files while running locally. That is useful for learning, testing, and demonstration. If the project is deployed publicly later, the data storage approach should be upgraded to a proper persistent database for production use.

## Summary

This project is now a polished educational resume-analysis app with:

- login and saved workspace restore
- session-safe API key handling
- logout and profile revocation
- cleaner logs and About page explanation
- GitHub-friendly project structure
- a deployment entrypoint for Vercel

It is meant to be understandable, presentable, and easy to continue improving.
