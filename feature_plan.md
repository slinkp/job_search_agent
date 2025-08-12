Plan for Implementing Dashboard Message Filtering.
We can do this with client-side filtering.

1. Frontend State Management

 - [x] Add two new properties to the daily dashboard Alpine.js component:
    - [x] hideRepliedMessages: true (default)
    - [x] hideArchivedCompanies: true (default) (we might already have
          something like this)
    - [ ] Unit tests for this
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

 - [ ] Add two toggle buttons in the dashboard view:
    - [ ] "Show replied messages" / "Hide replied messages" (hidden by default)
    - [ ] "Show archived" / "Hide archived" (hidden by default)
 - [ ] When toggles are switched, trigger a refresh of the message list
 - [ ] Position these in the dashboard header
 - [ ] Follow style of existing buttons
 - [ ] Write tests for this
