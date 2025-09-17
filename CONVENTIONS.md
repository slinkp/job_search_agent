# CONVENTIONS.md

This file provides guidance to Aider
when working with code in this repository.

## Commands

### Running the Application

**Environment notes:**

Python environment is in `.direnv`.
Various environment variables are exported via direnv
and live in `.envrc`.

```bash
# Backend research daemon (in one terminal)
python research_daemon.py

# Web server (in another terminal)  
python server/app.py
```
Web app runs at http://localhost:8080

### Testing
```bash
# Run all python and javascript tests, always.
./test --no-cover
```

### Development Tools
```bash
# Code formatting (Black with 90 char line length)
black .

# Type checking (Pyright configured via pyrightconfig.json)
mypy .

# Python linting
flake8 .

# All of the above
./black-flake8-mypy .
```

## Basic development process

- Do the smallest possible step. Always.
- Ask for clarification if unsure what to do.
- Always run tests and lint fixes BEFORE committing.
- Never commit with ANY failing tests.
  If you can't fix a failing test after four attempts, give up and ask
  for guidance.
- NEVER commit frontend and backend changes at the same time.


## Architecture

This is a **job search automation tool** that processes recruiter emails, researches companies, and generates replies using AI. The system follows a multi-component architecture:

### Core Backend Components
- **`models.py`** - Pydantic models for Company, RecruiterMessage, CompanyStatus, and database interactions
- **`email_client.py`** - Gmail API integration for reading/sending emails
- **`libjobsearch.py`** - Main research and reply generation logic with RAG
- **`company_researcher.py`** - Company research automation with web scraping
- **`research_daemon.py`** - Background task processor for async operations
- **`server/app.py`** - Pyramid REST API backend
- **`tasks.py`** - Task queue management and processing

### Tech Stack
- **Backend**: Python with Pyramid web framework
- **Frontend**: Alpine.js + Pico.css (Single Page Web App)
- **Database**: SQLite with Pydantic models
- **AI**: OpenAI/Anthropic APIs via LangChain for research and reply generation  
- **Scraping**: Playwright for levels.fyi and LinkedIn data
- **APIs**: Gmail API, Google Sheets API
- **Testing**: pytest (Python), Vitest (JavaScript)

### Data Flow
1. **Email scanning** → RecruiterMessage objects → SQLite storage
2. **Company research** → AI-powered search + web scraping → Company objects
3. **Reply generation** → RAG chain using past replies → Gmail API sending
4. **Data sync** → Google Sheets as canonical source (pragmatic choice)

### Key Directories
- **`server/`** - Web application (Pyramid backend + Alpine.js frontend)
- **`company_classifier/`** - ML pipeline for company fit classification (WIP)
- **`data/`** - SQLite database and vector storage (ChromaDB)
- **`tests/`** - Python test suite 
- **`server/frontend/tests/`** - JavaScript test suite
- **`migrations/`** - Database migration scripts

### Important Context
- **Google Sheets sync**: The spreadsheet remains canonical for now due to manual data entry needs
- **Company name normalization**: Uses slugify with custom replacements (& → and)
- **AI Model Selection**: Configurable between OpenAI and Anthropic models
- **Background Processing**: Research tasks run async via daemon to avoid blocking UI
- **Email Integration**: Full Gmail API integration for both reading and sending

### Testing Notes
- Python tests use pytest with mocking via `autospec=True`
- JavaScript tests use Vitest with happy-dom
- Coverage reporting available for both stacks
- Integration tests cover the full email → research → reply workflow

## Logging

- Applications log to both console and files by default
- Log files are stored in the `logs/` directory
- Log files are rotated when they reach 10MB, with up to 5 backup files kept
- Log format includes timestamp, process name, process ID, log level, and message
- Log file names correspond to the process: `research_daemon.log`, `server.log`, etc.
