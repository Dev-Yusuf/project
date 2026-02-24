# Igala Encyclopedia Feature Roadmap

## Current State

IgalaHeritage has: dictionary (words, meanings, examples, dialects), user contributions with admin approval, leaderboard, pioneers page, about page, auth, and placeholder pages for translator and API docs.

---

## Implementation Order

| Phase | Feature | Rationale |
|-------|---------|-----------|
| **1** | History | Foundation content; user submissions + admin approval; dashboard tracking |
| **2** | Feeds | Discovery layer; aggregates content from multiple models |
| **3** | Blog | Community content; immediate publish; community guidelines |
| **4** | Learning | Proverbs, stories (with audio), books, games, external resources |
| **5** | Translator | English-Igala phrase lookup |
| **Future** | Notifications | Email alerts when new history or book is added (opt-in) |

---

## Phase 1: History

**Goal:** A well-designed history section with user submissions, admin approval, bilingual content, and audio.

### Contribution Flow

- **Users submit** history articles (title, content in English and/or Igala, thumbnail, audio optional at submission).
- **Admins vet and approve** in Django admin. Rejected submissions can include notes (like dictionary).
- **Approved histories** appear on the history page.
- **Dashboard:** Approved history submissions are recorded on the user's dashboard (like dictionary contributions).

### Design

- **List page:** Clean card grid with thumbnail images. Each card shows title, short excerpt, thumbnail. Sleek, minimal layout.
- **Detail page:** Full history article with:
  - **Toggle menu** to switch between **English** and **Igala** versions.
  - Each version has its own **audio** – users can listen if they can't read or prefer audio.
  - Responsive layout; images and typography optimized for readability.

### Model

- `PendingHistory` (or `HistorySubmission`): submitted_by (FK User), title, content_english, content_igala, thumbnail, audio_english, audio_igala, status (PENDING/APPROVED/REJECTED), reviewed_by, reviewed_at, rejection_notes.
- `HistoryArticle`: Same fields as approved content; created when admin approves. Links to original submitter for dashboard tracking.
- **Rich text:** django-ckeditor for `content_english` and `content_igala`.

### Key Implementation Notes

- **Audio:** Admin or submitter uploads. Native speaker recordings preferred. TTS for Igala is limited.
- **Dashboard:** Extend existing contribution stats or add "approved_histories_count" to user profile/dashboard.
- **Toggle:** Simple tab or toggle UI (e.g. "English | Igala") that switches visible content and audio player.

---

## Phase 2: Feeds

**Goal:** A feed of random, interesting content from across the platform with endless scroll.

### Design

- **Feed page:** Vertical list of mixed content (history articles, dictionary words, proverbs, stories, blog posts).
- **Lazy loading:** Infinite scroll – load more items as user scrolls.
- **Card format:** Each item type has a consistent card layout (thumbnail, title, excerpt, type badge). Click to go to detail.

### Data Source

- Aggregate from: `Words`, `HistoryArticle`, `BlogPost`, `Proverb`, `Story` (Phase 4).
- **Unified feed item:** Serialize each source into a common shape (title, excerpt, thumbnail, url, type, created_at).

### Key Implementation Notes

- **Ordering:** Mix of recent and random for variety.
- **Pagination:** Cursor-based or offset for infinite scroll.
- **Caching:** Cache feed queries for performance.

---

## Phase 3: Blog

**Goal:** User-published blog posts with rich formatting, images, likes, comments, and sharing. **No admin approval** – publish immediately.

### Design

- **Rich editor:** Users can add images, format text (bold, italic, headings, lists), embed media.
- **Post detail:** Full post with author, date, like count, comment count, share buttons.
- **Interactions:** Like, comment thread, share (copy link, social share).

### Community Guidelines

- **Before first post:** Show community guidelines (modal or dedicated page). User must acknowledge (e.g. checkbox) to proceed.
- **Purpose:** Avoid abuse, spam, inappropriate content. Set expectations for respectful participation.
- **Enforcement:** Report button for posts; admin can hide/remove violating content.

### Model

- `BlogPost`: author (FK User), title, slug, body (rich text), cover_image, published_at, created_at, updated_at, status (draft/published).
- `BlogPostLike`: user (FK), post (FK), created_at. Unique (user, post).
- `BlogPostComment`: user (FK), post (FK), parent (FK, nullable for replies), body (text), created_at.

### Key Implementation Notes

- **Publish immediately:** No approval step. Status goes directly to published when user submits.
- **Rich text:** django-ckeditor. Configure image upload (Supabase/media).
- **Sharing:** Open Graph meta tags; share buttons (Twitter, Facebook, WhatsApp, copy link).

---

## Phase 4: Learning

**Goal:** Proverbs, stories (with audio), books, games, and external resources. **No alphabet** – users are referred to external resources for foundational learning.

### Components

1. **Proverbs**
   - Igala text, English translation, context/meaning.
   - **Audio** for each proverb (native speaker recording).
   - User submissions with admin approval (optional, or admin-only).
   - Browse by theme (e.g. leadership, family).

2. **Stories**
   - Title, Igala text, English translation, category (folktale, historical, legend).
   - **Audio** for each story (full narration).
   - User submissions with admin approval (optional, or admin-only).

3. **Igala Books**
   - Curated list: title, author, description, cover image, link to purchase or PDF (if permitted).
   - Admin-managed. Consider copyright; link to external sources rather than hosting full texts.

4. **Games**
   - **Flashcards:** Word + meaning; flip to reveal. Filter by topic/part of speech.
   - **Matching:** Match Igala word to English meaning (or vice versa).
   - **Quizzes:** Multiple choice, fill-in-blank.
   - Uses existing `Words` and `Meaning` data.

5. **Resources**
   - External links and references for learning Igala (courses, books, alphabets, etc.).
   - "Not everything can be learned on the platform" – point users to external resources.
   - Admin-managed list with title, description, url, category.

### Key Implementation Notes

- **Proverbs/Stories:** Each has `audio` (FileField). Admin or approved contributors upload.
- **Alphabet:** Removed. Users referred to resources section for foundational learning.
- **Progress (optional):** Track "words learned", "games completed" per user.

---

## Phase 5: Translator

**Goal:** Translate between English and Igala (and vice versa).

### Phase 5a: Phrase Lookup (Recommended First)

- **Input:** User enters a phrase (English or Igala).
- **Process:** Split into words, look up each in the dictionary.
- **Output:** Show each word with its meaning(s), combined into a phrase-level view. Link each word to its dictionary entry.
- **No NLP or external API required.** Uses existing dictionary data.

### Phase 5b: Full Translation (Future)

- Integrate translation API if Igala is supported, or build community glossary for common phrases.
- **Caveat:** Igala support in major APIs may be limited.

---

## Future: Email Notifications

**Goal:** Notify users when new content is added. **Opt-in only** – users enable from dashboard settings.

### Triggers

- **New history** (approved and published).
- **New book** added to Learning section.

### Implementation

- **User setting:** `notify_new_history` (bool), `notify_new_books` (bool) in user profile or settings model.
- **Dashboard:** Settings page with toggle(s) for each notification type.
- **Email:** Send transactional email when trigger fires (only to users who have opted in).
- **No in-app notifications** in initial version – email only.

### Key Implementation Notes

- **Opt-in:** Default to false. User must explicitly enable.
- **Unsubscribe:** Include link in email to turn off.
- **Respect email platform:** Use existing email service (e.g. SendGrid, Resend) when configured.

---

## Technical Stack Summary

| Component | Approach |
|-----------|----------|
| Rich text | django-ckeditor |
| Images/Audio | Existing Supabase/media setup |
| Infinite scroll | Fetch API + Intersection Observer; cursor/offset pagination |
| Likes/Comments | Django models + AJAX or HTMX |
| Games | Vanilla JS or lightweight frontend; data from Django API |
| Notifications | Email only; opt-in via user settings |

---

## File Structure (High Level)

```
main/           # Existing
dictionary/     # Existing
history/        # New app – PendingHistory, HistoryArticle, submissions, approval, dashboard tracking
blog/           # New app – BlogPost, Like, Comment, community guidelines
learning/       # New app – Proverb, Story, Book, Game, Resource (proverbs/stories with audio)
feeds/          # New app or view in main – aggregates content, feed template
# Translator: extend dictionary app or add translator view in main
# Notifications: future – user settings, email triggers
```

---

## Navbar and Landing Page Alignment

### Current State

**Navbar:** Dictionary | Leaderboard | Contribute (Submit Word, My Contributions) | Resources (Translator, API, GitHub) | About | User/Login/Register

**Landing page:** Hero (Explore Dictionary, Join Community) | Stats (Words, Audio, Contributors) | 3 cards (Dictionary, Contribute, Learn & Practice → Translator) | Pioneers | Donation | CTA

**Footer:** Projects (Dictionary, Translator, API, Leaderboard) | Company (About, Pioneers, Blog placeholder, Contact placeholder) | Newsletter

### Gaps vs New Plan

| Planned Feature | Navbar | Landing | Footer |
|-----------------|--------|---------|--------|
| History | Missing | Missing | Missing |
| Feeds | Missing | Missing | Missing |
| Blog | Missing | Missing | Placeholder link (no URL) |
| Learning | Missing (Translator under Resources) | "Learn & Practice" links only to Translator | Missing |
| Contribute: Submit History | Missing | Missing | N/A |

### Recommended Navbar Structure

To avoid clutter, use dropdowns for related items:

```
Dictionary | History | Feeds | Learning ▼ | Blog | Contribute ▼ | Resources ▼ | Leaderboard | About | User
```

**Learning dropdown:** Proverbs, Stories, Books, Games, Resources (external links)

**Contribute dropdown:** Submit Word, Submit History, My Contributions

**Resources dropdown:** Translator, API, GitHub

Alternative (fewer top-level items): group Explore (Dictionary, History, Feeds) and Learn (Learning, Translator) into dropdowns. Trade-off: fewer clicks for power users vs cleaner nav for casual visitors.

### Recommended Landing Page Updates

1. **Hero CTAs:** Add "Explore History" or "Browse Feeds" alongside "Explore Dictionary" (or a single "Explore" that goes to Feeds). Keep "Join Community".
2. **Stats:** When available, add History count, Blog posts count. Keep Words, Audio, Contributors. Consider: Words | History | Contributors | Blog Posts (or similar).
3. **Feature cards:** Expand from 3 to 4–5 cards to reflect pillars:
   - **Dictionary** (existing)
   - **History** (new) – "Discover Igala history in English and Igala, with audio."
   - **Learning** (replace "Learn & Practice") – Proverbs, stories, books, games. Link to Learning index.
   - **Blog** (new) – "Read and share stories from the community."
   - **Feeds** (optional card or integrated) – "Discover random content from across the platform." Or make Feeds the main discovery CTA.
4. **Contribute card:** Update copy to mention "Submit words or history" when History is live.
5. **Pioneers, Donation, CTA:** Keep as-is.

### Recommended Footer Updates

1. **Projects column:** Add History, Feeds, Learning (or link to Learning index). Wire Blog link to blog URL when implemented.
2. **Company:** Keep About, Pioneers. Add Contact when implemented.
3. **Newsletter:** Wire to notification signup when that feature exists (opt-in for new history/books).

### Implementation Approach

- **Phase 1 (History):** Add History to navbar, footer, and one landing card. Add "Submit History" to Contribute dropdown.
- **Phase 2 (Feeds):** Add Feeds to navbar and footer. Optionally add Feeds card or CTA on landing.
- **Phase 3 (Blog):** Add Blog to navbar, footer, landing. Wire footer Blog link.
- **Phase 4 (Learning):** Add Learning dropdown to navbar. Replace "Learn & Practice" card with Learning card. Add Learning to footer.
- **Phase 5 (Translator):** Keep under Resources; no structural change.

Use `{% url 'history_list' %}` etc. with fallbacks or conditional rendering so the nav doesn't break before a feature exists (e.g. `{% if history_url %}...{% endif %}` or ensure URLs are defined and return a "Coming soon" page).

---

## Summary

**History:** User submissions → admin approval → published on history page; recorded on dashboard. django-ckeditor, bilingual + audio, toggle UI.

**Feeds:** Mixed content, endless scroll, lazy loading.

**Blog:** Immediate publish, no approval. Community guidelines before first post to avoid abuse. Likes, comments, sharing.

**Learning:** Proverbs and stories (each with audio), books, games, external resources. No alphabet – users referred to resources.

**Translator:** Phrase lookup (split input, dictionary lookup).

**Future:** Email notifications (opt-in via dashboard) when new history or new book is added.
