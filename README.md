# TL;DR

This is a tool to help me find and apply to highly relevant jobs.

It is also an excuse to learn AI techniques like RAG, and use generative coding tools to get things done.

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


# Problem 1: Automatic my recruiter email replies via gmail and RAG

Most of the recruiter mail I get is for positions that aren't a good match.
It's hard to find the good ones, and I don't want to spend a lot of time on it
manually.

I want to be able to reply to all of them quickly and politely. I want to use
RAG to generate appropriate (for me, based on my criteria!) replies to
recruiters, and then send them from my gmail account.

Is this a good time investment? Since it's an excuse to learn RAG
techniques on a practical problem I actually have, absolutely!

# Problem 2: Research agent

Researching companies is time consuming and tedious.
Data entry into my spreadsheet is tedious.
Can RAG or other AI techniques help automate this?

I have a pretty standard set of questions I want answered about companies I'm
researching. Some of them are amenable to answering in a predictable way
(eg on Linkedin or Levels); some take more exploratory digging (eg "How many
people work there?" or "What's their remote/onsite work policy?")

# Notes on workflow

I'd like this to suit me being able to deal with a batch of possible jobs
(whether found via email, tips from elsewhere, whatever) in a fairly natural
way.
Eg:

- Walk up to my computer
- Run `<the program>`
  - See some kind of summary of status, TBD
  - for example: "There are 9 un-responded recruiter pings from linkedin"
- Automated research happens
  - OK if i have to kick off each company research, there aren't that many
- List of results and action items
  - "company foo via linkedin ping"
  - actions: reply (auto w/ confirmation), defer / do nothing, archive / ignore

"Defer" raises a question of state.
Do we need some kind of db tracking status?
(Or maybe the cache is enough)

## Auto-replying when there's not enough info to research

What do we do when we don't have a company name or URL?
I want to auto-reply asking for more info.
Currently we just stop without a company name and don't even save it.
Example:

```
19:39:14 DEBUG libjobsearch: Cache miss for initial_research_company:('Hiring - Django Architect - Sandy Springs GA(Hybrid)\n\n\n\nHiring - Django Architect - Sandy Springs GA(Hybrid)\nHiring - Django Architect - Sandy Springs GA(Hybrid)\nMohd Sabhee',):{'model': 'claude-3-5-sonnet-latest'}
```

Idea: 
We need some sort of hash so we can assign a name like `(unknown company b1946ac92492d2347c6235b4d2611184)`
so we can track these with the message, thread link, generate a reply, etc
but how do we make the hash consistent?
something like: normalize and md5 (sender, subject, 1st 100 chars of content of first email in thread)

Won't work if follow-ups are not threaded, but that can't be helped.




# Roadmap, end to end


- [x] Build main end-to-end script that integrates all of the below
- [x] Email client
  - [x] Retrieve recruiter messages (and my replies) from gmail
  - [ ] Support extracting and researching companies that aren't from recruiter
        mail
    - [ ] distinguish these from recruiter companies in the company list
    - [ ] support linkedin job alert email
    - [ ] support "welcome to the jungle" job alert email
    - [ ] support https://hnhiring.me (hacker news hiring, better interface) 
  - [x] Build a RAG chain trained on those messages
    - [x] Understand the parts of the chain that I don't yet!
    - [x] What is RunnablePassThrough?
    - [ ] Look at traces (where? langsmith?) and see if I can understand the chain
  - [x] Try both claude and chatgpt, allow choosing 
  - [x] Demo of generating replies based on example new messages
  - [ ] Solve problem of linkedin email that are recruiter followup, but gmail doesn't thread them
  - [ ] Solve messages that I've already replied to on linkedin and so aren't in gmail - maybe require manually re-labeling
  - [ ] Iterate on prompt against real recruiter email, until test replies to
        those usually look good.
        - [ ] Try prompt improvement tools eg Anthropic's
  - [ ] Extract data from attachments if any (eg .doc or .pdf)
  - [x] Extract subject from message too
- [x] Actually send email replies
- [x] Re-label replied messages (so we know they don't need looking at again)
- [x] Company research: general info
  - [x] If initial research finds a different company name than was in email: log warning and update
        it. Known example: Capital Markets Placement -> iCapital
  - [x] Formalize my research steps:
  - [x] Try langchain with both anthropic and openai
  - [x] Try RecursiveUrlLoader to fetch more data from company websites
        ... this is not helping much; we're downloading entire websites and not
        finding the information we want. Hard to verify if it's even present.
  - [x] Try with Tavily search
    - [x] Lots of decisions to make here per https://blog.langchain.dev/weblangchain/
    - [ ] Report Tavily issue: Undocumented 400 character limit on get_search_context(query). Client gets a 400 error, but no indication of what's wrong.
    - [x] Tavily works great, using that!
- [x] Data model for company info (name, headcount size, funding/public status,
      remote policy, etc)
  - [x] Derive fields from my google spreadsheet
  - [x] chose Pydantic, it's pretty nice
- [x] Write a Google sheet client to store this data model in my existing sheet
  - [x] Integrate with main script
  - [x] Check if company already exists in sheet; if so, update rather than add
  - [ ] If company exists in sheet, but not in database, then pull in the sheet
        info to db, and update if needed
        - [ ] if all fields are full, mark research as done
        - [ ] see below about existing match
- [x] Company research: Salary data from levels.fyi
  - [ ] Don't override salary data if we already have it
    - [ ] Maybe a dialog in UX?
  - [x] Drive browser - chose Playwright
  - [x] Extract salary data based on company name
  - [x] Extract job level comparable to Shopify staff eng
  - [x] Integrate salary with main script, add to spreadsheet
  - [x] Integrate level with main script, add to spreadsheet
- [ ] Automatically decide whether the company is a good fit, yes/no
  - [ ] Work through the feature plan in COMPANY_FIT_PLAN.md
- [x] Company research: Find contacts in linkedin search
  - [x] Drive browser
  - [x] Search for 1st degree connections currently at company
  - [x] Integrate with end-to-end flow, add to spreadsheet
  - [x] Skip if company not a good fit
- [x] Browser-driven research: Run headless?
- [ ] Company research: Find contacts in recurse
  - [ ] Is there an API? Or drive browser? Is there TOS?
  - [ ] Search for 1st degree connections currently at company
  - [ ] Integrate with end-to-end flow, add to spreadsheet
  - [x] Skip if company not a good fit
- [x] UX: Proof-of-concept command line
    - [x] Chose command line for first pass (running libjobsearch.py as a script)
    - [x] Edit reply via texteditor
- [x] **UX!** 
  - [x] Decide on framework for this.
    - [x] Chose SPWA using Alpine.js and Pico.css frontend
    - [x] Chose pyramid for simple REST API backend
    - [x] Persist company data
      - [x] chose sqlite db
      - [x] models.py
      - [x] simple repository implementation
  - [x] Manually trigger checking email (with optional max)
      - [x] Button to scan email and select how many
      - [x] Make it optional whether we do research automatically (default: no)
      - [ ] Show more detailed progress info?
  - [x] support manually adding companies
      - [x] By URL. Likely from a job listing
      - [x] By name
  - [x] List pending companies
    - [x] Display known data
    - [x] Link to original message, if any (maybe just gmail link?)
  - [x] List companies that already have been replied to
    - [x] show whether reply was sent and date it was sent
    - [x] "send and archive" should effectively update this
  - [x] Research button
    - [x] If already researched, label it "Re-do research"
    - [x] If a research step fails, show which one(s), without blowing up the
          research process.
  - [x] "Generate reply" button (and "regenerate")
    - [x] "Edit reply" button
    - [x] Display reply
      - [x] Show recruiter message below generated reply
      - [x] Show date of recruiter message above their message,
            formatted like  "YYYY/MM/DD 3:42pm (X days ago)"
      - [x] Add link to email thread from the reply page
      - [ ] "Mark as manually replied" button
        - [ ] Optionally manual add link to an existing email thread?
    - [x] "Send and archive" button
    - [ ] "Save gmail draft" button
      - [ ] Track and show the state of this so we don't regenerate or edit and send
            when there's already a draft? Link to draft?
    - [ ] "--dry-run" command line flag to server/app, to not actually send
          messages
    - [x] similar option to research daemon to not actually send messages
  - [ ] Richer company data display, with links
  - [x] Async updates from backend
    - [x] Polling the API is fine
    - [x] Run research in a separate process (research_daemon.py)
    - [x] Chose a simple task model in db rather than a task queue
      - [x] task.py for task queue interface
      - [x] models.py for the actual data model
      - [x] app uses task.py to create and check on tasks
      - [x] research_daemon.py uses task.py to run and update tasks
      - [x] Chose sqlite for task db
    - [x] Support processing old unprocessed tasks
      - [x] Works, does oldest first
  - [x] "Ignore and archive" feature
     - [x] button, backend api, task, and task handler for this
     - [x] add function to libjobsearch: sends no message; archives the
           recruiter message
     - [x] updates status in actual spreadsheet to "70. ruled out - didn't reply"
     - [x] new "archived" icon & filter for this in web app
  - [x] Support importing companies from spreadsheet
     - [x] Add button to UX for this
     - [x] Add a background task
     - [x] It should use existing name normalization to check for duplicates
           in which case, merge the spreadsheet data into the db data and vice versa.
           (Spreadsheet data wins over DB data if both exist)
     - [x] Progress tracking and status updates during import
     - [x] Detailed results summary showing created/updated/skipped companies
     - [x] Error handling and reporting
  - [ ] Make sure we only add new companies
     - [x] Add to db only if doesn't exist
     - [ ] Check spreadsheet and db for existing match:
         - [x] by company name - normalized
         - [ ] by fuzzy match on name?
         - [ ] by message id?
         - [ ] by thread link?
         - [ ] support merging duplicates?
  - [ ] Handle multiple messages for same company??
  - [ ] Better management of background tasks
     - [ ] Probably should have a sensible cutoff age, eg don't auto-apply
           a task older than 1 day?
     - [ ] Display tasks (filterable by status) in UX
     - [ ] Actions:
       - [ ] Discard old tasks
       - [ ] Force retry failed tasks
- [ ] Q: If this app has all the same data as spreadsheet, then we can drop the
      spreadsheet
    - [ ] Make the web app more browsable / readable
    - [ ] Two sources of truth sucks; i'm currently treating the sheet as canonical
    - [ ] First pull in all the old data from the sheet
    - [ ] Make all fields easily hand-editable in the app
    - [ ] Figure out what spreadsheet features are actually useful and
          duplicate those
    - [ ] Make it trivial to modify the db schema while preserving existing
          data
          - [ ] we may need an ORM with migrations, sigh.
          - [ ] is there something that integrates well with pydantic as source
                of truth on fields / types?
- [ ] Work through the existing backlog with this tool
- [ ] Keep it at inbox zero until I get a job
- [ ] Profit


## Tavily strategy: One big prompt or multiple?

I wasn't sure which way to go and experimenting was inconclusive. 
So I asked Tavily! (And chatgpt and claude.)

Prompt and responses are in
tavily-prompt-strategy.md

TL;DR using a hybrid approach of a few strategically related prompts.

# ISSUES TO FIX
 
## Companies with jobs posted on notion get renamed "notion"
2025-04-09

Example:
i gave name "Cassidy AI" and URL
 https://cassidyresources.notion.site/work-at-cassidy-769aa699ec7a47aa9c84097bad5052ac
and it got saved with name "notion"


## Company renaming sometimes finds a worse name for research purposes

Eg:
AWS got renamed "amazon web services (AWS)"
but on levels.fyi it's just "Amazon"

Possible solution:
Allow manual name override?
And somehow mark it as override so it won't get auto-broken again?

