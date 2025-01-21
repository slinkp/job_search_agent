# TEMPORARY BUG / FEATURE LIST:

## Email thread w dupe content

```
Hi, Paul. I just wanted to follow-up on my last note about the Senior or Staff level role here at Narmi...\n\n\n\nHi, Paul. I just wanted to follow-up on my last note about the Senior or Staff level role here at Narmi...\nHi, Paul. I just wanted to follow-up on my last note about the Senior or Staff level role here at Narmi...\n
```

There must be more to that??

Confirmed, there was, here's the plaintext from this thread:
https://mail.google.com/mail/u/0/?ik=33441569df&view=om&permmsgid=msg-f:1821523740927514788

```
------=_Part_4032611_593488211.1737140406079
Content-Type: text/plain;charset=UTF-8
Content-Transfer-Encoding: quoted-printable
Content-ID: text-body

Hi, Paul. I just wanted to follow-up on my last note about the Senior or St=
aff level role here at Narmi...
Hi, Paul. I just wanted to follow-up on my last note about the Senior or St=
aff level role here at Narmi...

      Evan Jones
        Reply
        https://www.linkedin.com/messaging/thread/2-ZjA2MDZhNGYtMzI4NC00MzE=
1LTkwNDctMDQzMzcwYTAzYTc1XzAxMg=3D=3D/

Dear Paul,

I'm sure you receive a lot of messages so I just wanted to follow-up about =
chatting about a Senior or Staff position on our Eng team. Let me know if y=
ou're curious or happen to know someone that would be a great fit!

Best, Evan

Evan Jones
Technical Recruiter at Narmi

   =20

----------------------------------------
```

## Email w minimal content

Surely there was more than 'Hi Paul !'
???

Yep, there was.

here's the plaintext from 1st in thread:
https://mail.google.com/mail/u/0/?ik=33441569df&view=om&permmsgid=msg-f:1821248694105197697

```
--0000000000004345f3062bae72af
Content-Type: text/plain; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

Are you considering new roles in NYC?

We're helping Thread AI look for a *Backend Engineer *with strong Java
experience - Python is nice to have.

Founded by ex-Palantir AI Product and Engineering Leads, Thread AI is
focused on building an AI-native workflow orchestration engine.

HQ is in NYC and the role is full onsite. Comp is $145K - 200K + equity.
Team size is ~10 and the company raised $6M in seed funding, backed by Shar=
dul
Shah of Index Ventures
<https://www.indexventures.com/perspectives/thread-ai-emerges-from-stealth-=
to-help-enterprises-design-implement-and-manage-ai-workflows/>
.

Interested? Let me know the earliest time we can discuss the role.


--
Kind regards,
Jency

Jennifer Bacu=C3=B1o
Technical Recruiter
Continuity Partners | New York | www.cpi-search.com
Schedule a call with me here -> *https://calendly.com/jbacuno/30min
<https://calendly.com/jbacuno/30min>*
[image: View my profile on LinkedIn]
<http://www.linkedin.com/in/jenniferbacuno>

*To see our latest roles, please check out our job portal (beta version) on
this link: molos.cpi-search.com <http://molos.cpi-search.com/>*

--0000000000004345f3062bae72af
```



Here's the log:

```
19:38:24 DEBUG libjobsearch: No cached result, running function for initial_research_company:('Hi Paul !',):{'model': 'claude-3-5-sonnet-latest'}...
19:38:24 INFO libjobsearch: Starting initial research...
19:38:24 DEBUG anthropic._base_client: Request options: {'method': 'post', 'url': '/v1/messages', 'files': None, 'json_data': {'max_tokens': 1024, 'messages': [{'role': 'user', 'content': "You are a helpful research agent researching companies.\nYou may use any context you have gathered in previous queries to answer the current question.\n\nFrom this recruiter message, extract:\n - The company name being recruited for\n - The company's website URL, if mentioned\n - The role/position being recruited for\n - The recruiter's name and contact info\n\n----- Recruiter message follows -----\n Hi Paul !\n----- End of recruiter message -----\n\nYou must always output a valid JSON object with exactly the keys specified.\ncitation_urls should always be a list of strings of URLs that contain the information above.\nIf any string json value other than a citation url is longer than 80 characters, write a shorter summary of the value\nunless otherwise clearly specified in the prompt.\nReturn ONLY the valid JSON object, nothing else.Never include any explanation or elaboration before or after the JSON object.\n\nReturn these results as a valid JSON object, with the following keys and data types:\n - company_name: string or null\n - company_url: string or null  \n - role: string or null\n - recruiter_name: string or null\n - recruiter_contact: string or null\n"}], 'model': 'claude-3-5-sonnet-latest', 'temperature': 0.7}}
```

## Auto-reply when we're going to bail out early

What do we do when there's not enough info to research?
I want to auto-reply asking for more info.
Currently we just stop without a company name and don't even save it.

```
19:39:14 DEBUG libjobsearch: Cache miss for initial_research_company:('Hiring - Django Architect - Sandy Springs GA(Hybrid)\n\n\n\nHiring - Django Architect - Sandy Springs GA(Hybrid)\nHiring - Django Architect - Sandy Springs GA(Hybrid)\nMohd Sabhee',):{'model': 'claude-3-5-sonnet-latest'}
```

We need some sort of hash so we can assign a name like `b1946ac92492d2347c6235b4d2611184`
so we can track these with the message, thread link, generate a reply, etc
but how do we make the hash consistent?
something like: normalize and md5 (sender, subject, 1st 100 chars of content)



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


# Roadmap, end to end


- [x] Build main end-to-end script that integrates all of the below
- [x] Email client
  - [x] Retrieve recruiter messages (and my replies) from gmail
  - [x] Build a RAG chain trained on those messages
    - [x] Understand the parts of the chain that I don't yet!
    - [x] What is RunnablePassThrough?
    - [ ] Look at traces (where? langsmith?) and see if I can understand the chain
  - [x] Try both claude and chatgpt, allow choosing 
  - [x] Demo of generating replies based on example new messages
  - [ ] Solve problem of linkedin email that are recruiter followup, but gmail doesn't thread them
  - [ ] Solve messages that I've already replied to on linkedin and so aren't in gmail - maybe require manually re-labeling
  - [ ] Iterate on prompt against real recruiter email, until test replies to those usually look good.
  - [ ] Extract data from attachments if any (eg .doc or .pdf)
  - [x] Extract subject from message too
- [ ] Actually send email replies
- [ ] Re-label replied messages (so we know they don't need looking at again)
- [ ] Company research: general info
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
  - [ ] Check if company already exists in sheet; if so, update rather than add
- [x] Company research: Salary data from levels.fyi
  - [x] Drive browser - chose Playwright
  - [x] Extract salary data based on company name
  - [x] Extract job level comparable to Shopify staff eng
  - [x] Integrate salary with main script, add to spreadsheet
  - [x] Integrate level with main script, add to spreadsheet
- [ ] Automatically decide whether the company is a good fit, yes/no
- [x] Company research: Find contacts in linkedin search
  - [x] Drive browser
  - [x] Search for 1st degree connections currently at company
  - [x] Integrate with end-to-end flow, add to spreadsheet
  - [x] Skip if company not a good fit
- [ ] Company research: Find contacts in recurse
  - [ ] Is there an API? Or drive browser? Is there TOS?
  - [ ] Search for 1st degree connections currently at company
  - [ ] Integrate with end-to-end flow, add to spreadsheet
  - [ ] Skip if company not a good fit
- [x] UX: Proof-of-concept command line
    - [x] Chose command line for first pass (running libjobsearch.py as a script)
    - [x] Edit reply via texteditor
- [ ] **UX!** 
  - [ ] Companies should be batched! See "Notes on workflow"
  - [x] Decide on framework for this.
    - [x] Chose SPWA using Alpine.js and Pico.css frontend
    - [x] Chose pyramid for simple REST API backend
    - [x] Persist company data
      - [x] chose sqlite db
      - [x] models.py
      - [x] simple repository implementation
  - [ ] Manually trigger checking email (with optional max)
  - [x] List pending companies
    - [x] Display known data
    - [ ] Link to original message, if any (maybe just gmail link?)
  - [x] Research button
  - [x] "Generate reply" button (and "regenerate")
    - [x] "Edit reply" button
    - [x] Display reply
      - [ ] Show recruiter message above reply
    - [ ] "Send and archive" button
  - [ ] Richer data display with links
  - [x] Async updates from backend
    - [x] Polling the API is fine
    - [x] Run research in a separate process (research_daemon.py)
    - [x] Chose a simple task model in db rather than a task queue
      - [x] task.py for task queue interface
      - [x] models.py for the actual data model
      - [x] app uses task.py to create and check on tasks
      - [x] research_daemon.py uses task.py to run and update tasks
      - [x] Chose sqlite for task db
- [ ] Work through the existing backlog with this tool
- [ ] Keep it at inbox zero until I get a job
- [ ] Profit


## Tavily strategy: One big prompt or multiple?

I wasn't sure which way to go and experimenting was inconclusive. 
So I asked Tavily! (And chatgpt and claude.)

Prompt and responses are in
tavily-prompt-strategy.md

TL;DR consider a hybrid approach of a few strategically related prompts.
