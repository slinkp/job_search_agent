Plan for Implementing Dashboard Message Filtering.
We can do this with client-side filtering.

1. Frontend State Management

 - [ ] Add two new properties to the daily dashboard Alpine.js component:
    - [x] hideRepliedMessages: true (default)
    - [x] hideArchivedCompanies: true (default) (we might already have
          something like this)
    - [ ] Unit tests for this
 - [ ] Add state of these to URL so page reload preserves state. With test.

2. Data Model Changes
  - [ ] RecruiterMessage backend model needs a `reply_sent_at` timestamp.
        `None` by default. Expose this in API.
  - [ ] Add an `is_archived` boolean property:
        True if message has `archived_at` OR message company has `archived_at`.
        Expose this in API.

3. Filtering

 - [ ] Rename `loadUnprocessedMessages` to `loadMessages`.
 - [ ] `loadMessages` should filter messages client side, based on state from step 1.
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
