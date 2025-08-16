Plan for Implementing Dashboard Message Filtering.
We can do this with client-side filtering.

1. Frontend State Management

 - [x] Add two new properties to the daily dashboard Alpine.js component:
    - [x] hideRepliedMessages: true (default)
    - [x] hideArchivedCompanies: true (default) (we might already have
          something like this)
    - [x] Unit tests for this
 - [x] Add state of these to URL so page reload preserves state. With test.
 - [x] Finish unit tests for the URL state persistence

2. Data Model Changes
  - [x] RecruiterMessage backend model needs a `reply_sent_at` timestamp.
        `None` by default. Expose this in API.
  - [x] Add an `is_archived` boolean property:
        True if message has `archived_at` OR message company has `archived_at`.
        Expose this in API.

3. Filtering

 - [x] Rename `loadUnprocessedMessages` to `loadMessages`.
 - [x] `loadMessages` should filter messages client side, based on state from step 1.
       (We already have logic for hiding messages with archived_at; do the
       changese there)

3. UI Implementation

 - [x] Add two toggle buttons in the dashboard view:
    - [x] "Show replied messages" / "Hide replied messages" (hidden by default)
    - [x] "Show archived" / "Hide archived" (hidden by default)
 - [x] When toggles are switched, trigger a refresh of the message list
 - [x] Position these in the dashboard header
 - [x] Follow style of existing buttons
 - [x] Write tests for this

 4. Button rename for consistency
 - [x] "Show replied messages" and "Show archived" are actions; clicking one replaces with "Hide..." button.
        This is confusing and inconsistent with similar filtering behavior on the "Company Management" page,
        where there are a series of filter buttons which are either blue (the filter is active) or white (inactive).
        Let's do that instead. Rename them to "archived" and "replied"
        - [x] "archived" should show ONLY archived messages
        - [x] Add a "not replied" button which should show ONLY un-replied messages, and un-toggle "replied"
 - [x] Add an "All" filter which shows all messages

