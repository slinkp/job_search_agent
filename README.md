# TL;DR

This is a tool to help me find and apply to highly relevant jobs.

It is also an excuse to learn AI techniques:
- Leverage generative tools like AI for reply auto-generation
- Leverage AI-powered tools for company research
- Possibly ML tools to classify companies as of interest, or not ("company fit")
- Use generative coding tools to get things done faster, and get better at that

## Install

Only tested on MacOS.
```console
pip install -r requirements.txt
``` 

## Run

TODO: Document the necessary environment variables you must export.
I use [direnv](https://direnv.net/) which loads them from an `.envrc` file (not provided)

```console
# In one terminal
python research_daemon.py
```

```console
# Run the web app in another terminal
python server/app.py
```

View the web app at http://localhost:8080

Both of them have command line interfaces; explore via `-h` or `--help`.

# Goals

This repository was created for 3 purposes:

1. **Help me organize my job search** - Ready for daily use
2. **Learn how to code with AI assistance tools** such as Cursor - Going well
3. **Learn how to leverage AI in my software** - RAG email replies, company fit classification - Going slowly but steadily

"Organize my job search" breaks down into a few sub-problems:

- Automate replying to inbound leads quickly and politely. I want to use
generative AI (possibly RAG techniques)  to generate appropriate replies to
recruiters, and then send them from my gmail account. I hate writing these replies so much I don't do it.

- Automate researching companies.  Research, data entry, and deciding whether a company is a decent fit for me is
also time-consuming and tedious.

# Current Status

The tool has most infrastructure in place and **is ready for daily use**. The core workflow of processing recruiter emails, researching companies, and generating replies is fully functional.

# Success Metrics (tracked weekly)

- **Leads processed** - How many job opportunities reviewed
- **Emails sent** - Automated replies to recruiters  
- **Reply quality** - How much editing needed: "Sent as-is" > "Minor edits" > "Major rewrite" > "Wrote from scratch"
- **Fit classification accuracy** - How often manual overrides are needed for good/bad company decisions

# Current Plan - Critical Path to Daily Use

## WEEK 1: Basic Daily Workflow

**Task 1**: Simplest Possible Company Fit Score
- Hardcode heuristic based on salary, remote policy, location, etc

**Task 2**: Daily dashboard with batch processing
- Show unprocessed recruiter messages (sender, subject, date)
- Batch actions: "Research selected", "Archive selected", "Reply to selected"  
- Status summary: "X unprocessed, Y researched, Z replied"


## WEEK 2: Efficiency, More Leads, Quality Tracking

**Task 3**: Handle Ambiguous Leads
- Create an "Awaiting Info" queue for leads that can't be parsed automatically (e.g., no company name).
- Add UI to manually enter missing info or trigger a pre-written "request for info" email.

**Task 4**: Basic deduplication  
- Fuzzy company name matching for new leads. Possibly store mapping of known aliases
- Manual merge UI for detected duplicates

**Task 5**: Welcome to the Jungle email integration
- Parse WttJ digest emails for company + role info
- Surface in same dashboard with source tag
- (First non-recruiter source - others later only if this proves valuable)
- Reply workflow not relevant to these so don't show that in UX

**Task 6**: Reply quality tracking
- Track edit level for each reply
- Add thumbs up/down after sending each email
  - maybe not necessary if we can infer based on how much I edited?
- Simple trends dashboard


## WEEK 3+: Measurement & Iteration
**Task 7**: Weekly metrics dashboard
- Track all success metrics defined above
- Guide future improvements based on data

**Task 8**: Fit classification baseline
- Simple heuristic scoring (keywords, salary mentions, remote policy)
- Track override rate when manually changing good/bad decisions
- Only add ML if heuristic override rate >30%

# Architecture Notes

## Current Tech Stack
- **Frontend**: Alpine.js + Pico.css (SPWA)
- **Backend**: Pyramid REST API
- **Database**: SQLite with Pydantic models
- **AI**: OpenAI/Anthropic APIs via LangChain
- **Scraping**: Playwright for levels.fyi and LinkedIn
- **Email**: Gmail API
- **Spreadsheet**: Google Sheets API (canonical data source)

Synchronizing the Google sheet with the DB is a pain point, but seems pragmatic for now
(there's a lot I can see and do in the sheet that would need to be exposed in the app
for me to do away with it, and that doesn't seem worthwhile...yet)

## Data Flow
1. **Email scanning** → RecruiterMessage objects → SQLite storage
2. **Company research** → search + scraping → Company objects  
3. **Reply generation** → RAG chain trained on past replies → Gmail API
4. **Data sync** → Google Sheets remains canonical source of truth

## Key Components
- `models.py` - Pydantic models for Company, RecruiterMessage, CompanyStatus
- `email_client.py` - Gmail API integration
- `libjobsearch.py` - Main research and reply logic
- `server/app.py` - Web UI backend
- `research_daemon.py` - Background task processor

# Issues to Fix

## Company name normalization issues
- Notion-hosted job pages get renamed to "notion"  (Example to repro: "Cassidy AI")
- AWS becomes "amazon web services (AWS)" but levels.fyi expects "Amazon"
- **Solution**: Add manual name override with persistence flag

## Bad UX with companies imported from spreadsheet

These have no recruiter message.
- clicking "generate" on the company page shows an error about no message to reply to, but it disappears too fast to see
- "generate" should just be deactivated if there's no message

# Deferred Features

These are valuable but not on the critical path to daily use:

- **Additional job sources** (LinkedIn alerts, Slack channels, HN Hiring)
- **Advanced ML for company fit classification** (Random Forest, synthetic data generation; this was left off as WIP in `company_classifier/`)
- **Additional contact sources beyond LinkIn** (Recurse connections)
- **Attachment processing** (PDF/DOC parsing)
- **Advanced monitoring** (model performance tracking)
- **Spreadsheet deprecation** (keeping sheets as canonical for now)

The focus is: **Fix the core workflow first, then iterate based on actual usage data.**

