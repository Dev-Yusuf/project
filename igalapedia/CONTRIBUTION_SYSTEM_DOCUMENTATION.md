# 🏆 Community Contribution System Documentation

## Overview

The Igalapedia Community Contribution System allows users to submit Igala words, meanings, and examples for admin review and approval. Only **approved contributions** are counted towards the **leaderboard rankings**.

---

## ✅ What Has Been Implemented

### 1. **Database Models** (✅ Complete)

#### `PendingWord`
- Stores user-submitted words awaiting approval
- Fields: word, pronunciation, dialects, related_terms
- Status: PENDING, APPROVED, REJECTED
- Tracks submitter, reviewer, and timestamps

#### `PendingMeaning`
- Meanings submitted with words
- Links to PendingWord
- Has part_of_speech and meaning text

#### `PendingExample`  
- Usage examples for meanings
- Igala sentence + English translation

#### `ContributionStats`
- Tracks per-user statistics
- Counts: approved, pending, rejected submissions
- Auto-updates when admin approves/rejects

### 2. **Admin Interface** (✅ Complete)

#### Features:
- ✅ **Bulk Actions**: Approve/Reject multiple submissions at once
- ✅ **Status Badges**: Color-coded status indicators (Pending/Approved/Rejected)
- ✅ **Inline Editing**: Review meanings and examples in one view
- ✅ **User Links**: Click to see submitter profile
- ✅ **Auto-Processing**: Approved submissions automatically create Words/Meanings/Examples
- ✅ **Stats Updates**: Contribution statistics auto-update on approval/rejection

#### Admin Actions:
1. **Approve Submissions** - Creates official dictionary entries
2. **Reject Submissions** - Marks as rejected with notes
3. **Recalculate Stats** - Manually update user statistics

### 3. **Forms** (✅ Complete)

- **WordSubmissionForm** - Submit new words
- **MeaningSubmissionForm** - Add meanings
- **ExampleSubmissionForm** - Add examples
- **Formsets** - Support multiple meanings/examples per word

### 4. **Views & URLs** (✅ Complete)

- `/dictionary/submit/` - Submit new words (login required)
- `/dictionary/my-contributions/` - View your submissions (login required)
- `/dictionary/leaderboard/` - Updated to show approved contributions only

### 5. **Leaderboard Logic** (✅ Updated)

- **Ranks users by approved contributions only**
- Pending/rejected submissions don't count
- Auto-syncs with Contribution Stats
- Achievement badges based on approved count

---

## 🔄 How It Works

### User Submission Flow:

```
1. User fills out submission form
   ↓
2. Creates PendingWord with status='PENDING'
   ↓
3. Admin reviews in Django Admin
   ↓
4. Admin clicks "Approve" or "Reject"
   ↓
5a. If APPROVED:
    - Creates official Word entry
    - Creates Meanings
    - Creates Examples
    - Links approved_word to pending submission
    - Updates user's ContributionStats
    - User appears/climbs leaderboard
    
5b. If REJECTED:
    - Updates status to REJECTED
    - Adds review notes
    - Updates user's ContributionStats
    - Does NOT affect leaderboard ranking
```

### Approval Logic:

When admin approves a `PendingWord`:

1. **Creates Word** with contributor = submitter
2. **Creates Meanings** from PendingMeaning(s)
3. **Creates Examples** from PendingExample(s)
4. **Links** approved_word back to source submission
5. **Updates** user's ContributionStats
6. **Increments** approved_words_count

---

## 📊 Database Schema

### PendingWord
```python
- id (PK)
- word (CharField)
- pronunciation_file (FileField)
- dialects (CharField)
- related_terms (CharField)
- submitted_by (FK -> User)
- submitted_at (DateTime)
- status (PENDING/APPROVED/REJECTED)
- reviewed_by (FK -> User, nullable)
- reviewed_at (DateTime, nullable)
- review_notes (TextField)
- approved_word (OneToOne -> Words, nullable)
```

### PendingMeaning
```python
- id (PK)
- pending_word (FK -> PendingWord)
- meaning (CharField)
- part_of_speech (FK -> PartOfSpeech)
```

### PendingExample
```python
- id (PK)
- pending_meaning (FK -> PendingMeaning)
- igala_example (CharField)
- english_meaning (CharField)
```

### ContributionStats
```python
- id (PK)
- user (OneToOne -> User)
- approved_words_count (Integer)
- pending_words_count (Integer)
- rejected_words_count (Integer)
- total_submissions (Integer)
- first_contribution (DateTime)
- last_contribution (DateTime)
```

---

## 🎯 Next Steps (To Complete the System)

### Still TODO:

1. ✅ **Run Migrations**
   ```bash
   cd igalapedia
   python manage.py migrate
   ```

2. ⏳ **Create Templates**
   - `submit_word.html` - Word submission form
   - `my_contributions.html` - User's submission history

3. ⏳ **Add Navigation Links**
   - Add "Submit a Word" to navigation
   - Add "My Contributions" to user menu

4. ⏳ **Create CSS**
   - `submission.css` - Styling for submission pages

5. ⏳ **Testing**
   - Test submission flow
   - Test admin approval
   - Test leaderboard updates

---

## 🔐 Permissions

- **Submit Words**: Requires login (`@login_required`)
- **View Own Contributions**: Requires login
- **Approve/Reject**: Requires admin/staff access
- **View Leaderboard**: Public (no login required)

---

## 📝 Admin Usage Guide

### To Review Submissions:

1. **Go to Django Admin** (`/admin/`)
2. **Click "Pending Word Submissions"**
3. **Review submission details**:
   - Check word spelling
   - Verify meanings are accurate
   - Review examples
4. **Select submissions** to approve/reject
5. **Choose action** from dropdown:
   - "✅ Approve selected submissions"
   - "❌ Reject selected submissions"
6. **Click "Go"**

### Submissions automatically:
- Create dictionary entries (if approved)
- Update contributor stats
- Send to leaderboard (if approved)

---

## 💡 Features

### For Users:
- ✅ Submit words with pronunciation
- ✅ Add multiple meanings
- ✅ Provide usage examples
- ✅ Track submission status
- ✅ View contribution history
- ✅ Earn leaderboard rankings

### For Admins:
- ✅ Bulk approve/reject
- ✅ Review notes
- ✅ One-click publishing
- ✅ Auto-stats updates
- ✅ Inline editing
- ✅ Status tracking

---

## 🏅 Leaderboard Ranks

Based on **approved contributions only**:

| Rank | Badge | Requirement |
|------|-------|-------------|
| 1st | 🏆 Champion | Top contributor |
| 2nd | ⭐ Expert | 2nd place |
| 3rd | 🌟 Pro | 3rd place |
| - | ✨ Active | 50+ approved words |
| - | 💫 Rising | 10+ approved words |
| - | 🌱 Starter | < 10 approved words |

---

## 🎨 UI Components

### Submission Form:
- Clean, intuitive layout
- Bootstrap styling
- Form validation
- File upload support
- Success/error messages

### My Contributions:
- List of all submissions
- Status indicators
- Review feedback
- Statistics dashboard

### Leaderboard:
- Top 3 podium display
- Full rankings table
- Achievement badges
- User avatars
- CTA to submit words

---

## 🔧 Technical Notes

### Transactions:
- Word submissions use `@transaction.atomic()`
- Ensures data consistency
- Rolls back on errors

### Querysets:
- Optimized with `select_related()`
- Prevents N+1 queries
- Fast leaderboard loading

### Auto-Updates:
- Stats recalculate on approval
- Leaderboard auto-syncs
- No manual intervention needed

---

## 📈 Statistics Tracked

Per user:
- Total submissions
- Approved count
- Pending count
- Rejected count
- First contribution date
- Last contribution date

---

## 🚀 Deployment Checklist

Before going live:

- [ ] Run migrations
- [ ] Create superuser (admin account)
- [ ] Test submission flow
- [ ] Test admin approval
- [ ] Configure file storage (for audio)
- [ ] Set up email notifications (optional)
- [ ] Add submission guidelines
- [ ] Create user documentation

---

## 📞 Support

For questions about the contribution system:
- Check admin documentation
- Review this file
- Test in development first
- Monitor pending submissions regularly

---

_System designed and implemented: October 21, 2025_
_Status: Core system complete, templates pending_

