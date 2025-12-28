# Email Cleaning Design

This document describes the LLM-optimized email cleaning architecture for mbox-to-sqlite.

## Design Philosophy

**Two-Phase Workflow**: Import first, clean later
- **Phase 1 (`mbox` command)**: Import original emails unchanged - preserves all data
- **Phase 2 (`clean` command)**: Create LLM-optimized version - non-destructive, repeatable

**Benefits**:
- ✅ Original data always preserved
- ✅ Can experiment with different cleaning strategies
- ✅ Can re-run cleaning without re-importing mbox
- ✅ Can compare original vs cleaned side-by-side

---

## Architecture Overview

```
┌─────────────┐
│  archive.mbox │
│  (652 MB)   │
└──────┬──────┘
       │
       │ mbox-to-sqlite mbox emails.db archive.mbox
       │
       ▼
┌─────────────────────────────┐
│   emails.db (Original)      │
│   ─────────────────────────  │
│   messages:                  │
│   - payload (raw, 14KB avg)  │
│   - all headers              │
│   - FTS on payload          │
└──────────┬──────────────────┘
           │
           │ mbox-to-sqlite clean emails.db emails-clean.db --level standard
           │
           ▼
┌────────────────────────────────┐
│  emails-clean.db (Optimized)   │
│  ────────────────────────────   │
│  messages:                      │
│  - body_raw (14KB avg)          │
│  - body_clean (4-6KB avg) ✨    │
│  - cleaning_stats (JSON)        │
│  - all headers                  │
│  - FTS on body_clean           │
└────────────────────────────────┘
```

---

## Command Structure

### Import Command (Unchanged)

```bash
# Import with Chinese tokenizer
mbox-to-sqlite mbox emails.db archive.mbox --simple-tokenizer ./libsimple.dylib
```

**Output**: `emails.db` with original `payload` column

---

### Clean Command (New)

```bash
# Basic usage (standard level)
mbox-to-sqlite clean emails.db emails-clean.db

# With Chinese tokenizer (recommended)
mbox-to-sqlite clean emails.db emails-clean.db \
  --simple-tokenizer ./libsimple.dylib

# Aggressive cleaning
mbox-to-sqlite clean emails.db emails-clean.db \
  --level aggressive \
  --simple-tokenizer ./libsimple.dylib

# With signature database building
mbox-to-sqlite clean emails.db emails-clean.db \
  --build-signature-db
```

**Arguments**:
- `source_db`: Existing database with original emails
- `dest_db`: New database for cleaned version

**Options**:
- `--level`: `minimal`, `standard` (default), or `aggressive`
- `--simple-tokenizer`: Path to libsimple.dylib for Chinese FTS
- `--build-signature-db`: Analyze corpus to detect common signatures
- `--table`: Table name (default: `messages`)

---

## Cleaning Levels

### Level 1: Minimal

**Operations**:
1. HTML → Markdown (with `body_width=0` for Chinese)
2. Replace inline images with placeholders
3. Normalize whitespace
4. Remove email artifacts (`<mailto:>`, `<tel:>`)

**Target**: ~40% token reduction
**Safety**: Highest (no content removal)
**Use case**: When you want structure preservation with minimal risk

**Example**:
```python
# Before (HTML, 13KB)
<html><table><tr><td>產品</td><td>價格</td></tr></table></html>

# After (Markdown, 966 chars)
| 產品 | 價格 |
|------|------|
```

---

### Level 2: Standard (Default)

Everything in Minimal, **plus**:

5. Remove email signatures (pattern matching)
6. Remove CSR policy boilerplate (~500 chars in 6,453 emails)
7. Remove contact footers

**Target**: ~60% token reduction
**Safety**: High (only removes known boilerplate)
**Use case**: Recommended for most users

**Signatures Removed**:
- Standard `-- ` delimiter
- "Sent from my iPhone/iPad"
- "Get Outlook for iOS/Android"
- CSR policy footer (企業社會責任政策聲明...)
- Contact signatures (company department footers)

---

### Level 3: Aggressive

Everything in Standard, **plus**:

8. Remove quoted replies (via quotequail library)
9. Collapse forwarded message chains
10. Add attachment metadata placeholders
11. Remove marketing disclaimers

**Target**: ~70% token reduction
**Safety**: Medium (may remove context in threaded conversations)
**Use case**: When token budget is critical and you don't need full threads

**What's Removed**:
```
> Original message from...
> > Previous reply...

----- Original Message -----
From: ...
```

---

## Database Schema

### Original Database (`emails.db`)

```sql
CREATE TABLE messages (
  [message-id] TEXT PRIMARY KEY,
  [from] TEXT,
  [to] TEXT,
  subject TEXT,
  date TEXT,
  payload TEXT,  -- Original content (14KB avg)
  ... all other headers ...
);

CREATE VIRTUAL TABLE messages_fts USING FTS5 (
  payload, subject,
  tokenize='simple',
  content=[messages]
);
```

### Cleaned Database (`emails-clean.db`)

```sql
CREATE TABLE messages (
  [message-id] TEXT PRIMARY KEY,
  [from] TEXT,
  [to] TEXT,
  subject TEXT,
  date TEXT,
  body_raw TEXT,           -- Copy of original payload (for comparison)
  body_clean TEXT,         -- LLM-optimized content (4-6KB avg) ✨
  cleaning_stats TEXT,     -- JSON metadata
  ... all other headers ...
);

CREATE VIRTUAL TABLE messages_fts USING FTS5 (
  body_clean, subject,     -- FTS on CLEANED content only
  tokenize='simple',
  content=[messages]
);
```

**cleaning_stats JSON**:
```json
{
  "original_bytes": 14000,
  "clean_bytes": 4200,
  "reduction_percent": 70.0
}
```

---

## Cleaning Pipeline

### Step-by-Step Process

```python
def clean(payload):
    # 1. Extract text from HTML/multipart
    text = extract_text(payload)
    #    - Convert HTML → Markdown (body_width=0)
    #    - Replace inline images with [Inline image: ...]
    #    - Handle multipart (---PART--- separator)

    # 2. Minimal cleaning (always)
    text = minimal_clean(text)
    #    - Normalize whitespace
    #    - Remove <mailto:>, <tel:> artifacts

    # 3. Standard cleaning (if level >= standard)
    if level >= standard:
        text = remove_signatures(text)
        #    - Remove "-- " signatures
        #    - Remove "Sent from my iPhone"
        #    - Remove contact footers

        text = remove_boilerplate(text)
        #    - Remove CSR policy
        #    - Remove legal disclaimers

    # 4. Aggressive cleaning (if level == aggressive)
    if level == aggressive:
        text = remove_quoted_replies(text)  # quotequail
        text = add_attachment_placeholders(text)

    # 5. Final normalization
    text = normalize_whitespace(text)
    #    - Max 2 consecutive newlines
    #    - Trim trailing whitespace

    return text
```

---

## Critical Implementation Details

### 1. Chinese Text Handling (Gemini's Critical Warning)

**MUST configure html2text properly**:

```python
h = html2text.HTML2Text()
h.body_width = 0           # CRITICAL: No line wrapping for Chinese!
h.ignore_images = True     # Replace with placeholders
h.ignore_links = False     # Preserve links
h.unicode_snob = True      # Use Unicode
```

**Why `body_width=0`?**
- Default 78-char wrapping inserts `\n` mid-sentence in Chinese
- Breaks semantic tokenization for LLMs
- **This was flagged as a showstopper by Gemini**

---

### 2. Signature Removal Strategy

**Hybrid Approach** (recommended by both Codex & Gemini):

**A. Pattern Matching** (for known signatures):
```python
# Remove standard markers
signatures = [r'\n-- \n', r'\nSent from my iPhone']

# Remove domain-specific (CSR policy)
if 'Company CSR Policy:' in text:
    remove_until_next_section()
```

**B. Hash-Based Detection** (for corpus-specific):
```python
# Build database of common footers
for email in all_emails:
    footer_hash = md5(last_10_lines)
    footer_counts[footer_hash] += 1

# Remove only if appears in >100 emails (clearly boilerplate)
common = {hash for hash, count in footer_counts.items() if count > 100}
```

---

### 3. Quoted Reply Removal

Uses **quotequail** library (dedicated email quote parser):

```python
import quotequail

def remove_quoted_replies(text):
    try:
        unwrapped = quotequail.unwrap(text)
        return unwrapped.strip()
    except Exception:
        # Fallback: simple pattern matching
        return remove_lines_starting_with_gt(text)
```

---

### 4. Edge Cases Handled

| Edge Case | Solution |
|-----------|----------|
| **Inline images** (`cid:`) | Replace with `[Inline image: logo.png]` |
| **Attachments** | Add `[Attachment: invoice.pdf, 245KB]` (aggressive mode) |
| **Multipart emails** | Split by `---PART---`, process separately |
| **Encoding errors** | Graceful fallback to BeautifulSoup |
| **Empty payloads** | Skip cleaning, preserve metadata |
| **Forwarded chains** | Collapse `-----Original Message-----` blocks |

---

## Performance Characteristics

### Processing Speed

**10,019 emails** (archive.mbox dataset):
- Import: ~30-60 seconds
- Cleaning: ~60-120 seconds (depends on level)
- Total: ~2-3 minutes

**Batching strategy**:
- Process 1,000 emails per batch
- Progress bar for user feedback
- Minimal memory footprint

---

### Storage Impact

| Database | Size | Notes |
|----------|------|-------|
| Original (`emails.db`) | 70 MB | payload column |
| Cleaned (`emails-clean.db`) | 50-60 MB | body_raw + body_clean |
| Reduction | 15-30% | Text compresses well |

**Why keep both databases?**
- Original: Legal/compliance, debugging
- Cleaned: LLM queries, analysis
- Storage is cheap (text compresses >50%)

---

## Token Savings Analysis

### Estimated Savings (archive.mbox)

```
Original payload: 148 MB total, 14KB avg
Cleaned payload:  44-60 MB total, 4-6KB avg

By Level:
- Minimal:    ~40% reduction (14KB → 8.4KB)
- Standard:   ~60% reduction (14KB → 5.6KB) ✨ Recommended
- Aggressive: ~70% reduction (14KB → 4.2KB)
```

### Token Estimation (Mixed CJK/English)

**Conversion**: ~2 chars per token (conservative for mixed content)

```
10,019 emails × 14KB = 148 MB original
148 MB ÷ 2 = 74M tokens

Standard cleaning:
148 MB × 40% = 59 MB saved
59 MB ÷ 2 = 29.5M tokens saved ✨
```

**Practical impact**:
- Claude 3.5 Sonnet: 200K context → ~400 emails (original) vs ~1,000 emails (cleaned)
- GPT-4 Turbo: 128K context → ~250 emails (original) vs ~625 emails (cleaned)

---

## Dependencies

### New Requirements (added to setup.py)

```python
install_requires=[
    "click",
    "sqlite-utils",
    "html2text>=2020.1.16",      # HTML → Markdown
    "beautifulsoup4>=4.9.0",     # HTML parsing fallback
    "quotequail>=0.2.0",         # Quoted reply detection
]
```

### Optional (already used)

- `libsimple.dylib`: Simple tokenizer for Chinese FTS

---

## Testing Strategy

### Recommended Test Fixtures

Create test cases for:

1. **Chinese email with HTML table**
   - Verify `body_width=0` preserves table structure
   - Check token reduction

2. **English email with links**
   - Ensure links preserved in Markdown
   - Verify link text vs URL separation

3. **Multipart (plain + HTML)**
   - Test `---PART---` separator handling
   - Verify no content duplication

4. **Email with CSR footer**
   - Confirm footer removal
   - Check no false positives

5. **Forwarded thread**
   - Verify quoted content removed (aggressive)
   - Check thread context preserved (standard)

6. **Email with attachments**
   - Ensure metadata placeholders added
   - Verify payload not corrupted

---

## Usage Examples

### Basic Workflow

```bash
# Step 1: Import original
mbox-to-sqlite mbox emails.db archive.mbox --simple-tokenizer ./libsimple.dylib

# Step 2: Create cleaned version
mbox-to-sqlite clean emails.db emails-clean.db \
  --level standard \
  --simple-tokenizer ./libsimple.dylib

# Step 3: Query cleaned database
sqlite3 emails-clean.db
```

### Query Patterns

```sql
-- Compare original vs cleaned for a specific email
SELECT
  subject,
  length(body_raw) as original_chars,
  length(body_clean) as clean_chars,
  json_extract(cleaning_stats, '$.reduction_percent') as reduction
FROM messages
WHERE [message-id] = '<target-id>';

-- Find emails with best token savings
SELECT
  subject,
  json_extract(cleaning_stats, '$.reduction_percent') as reduction
FROM messages
ORDER BY reduction DESC
LIMIT 10;

-- Search cleaned content (LLM-optimized)
.load ./libsimple
SELECT subject, simple_highlight(messages_fts, 0, '[', ']') as context
FROM messages_fts
WHERE messages_fts MATCH simple_query('會議記錄')
LIMIT 5;
```

---

## Future Enhancements

Based on Codex/Gemini reviews:

1. **Attachment metadata extraction**
   - Extract filename, MIME type, size
   - Add to `body_clean` as structured data

2. **Calendar invite parsing**
   - Detect `text/calendar` parts
   - Extract event summary, time, attendees

3. **Nested message handling**
   - Hoist `message/rfc822` parts to separate rows
   - Preserve forwarded email context

4. **Configurable cleaning rules**
   - JSON config file for custom patterns
   - Per-domain signature templates

5. **Machine learning signature detection**
   - Train classifier on email corpus
   - Auto-detect variable signatures

6. **Incremental cleaning**
   - Only process new emails
   - Update existing cleaned database

---

## Design Validation

### ✅ Addresses Gemini's Critical Points

- [x] `body_width=0` for Chinese text
- [x] Keep both `body_raw` and `body_clean` columns
- [x] Add `html2text` dependency
- [x] Auditability via statistics

### ✅ Addresses Codex's Recommendations

- [x] Cleaning level presets (minimal/standard/aggressive)
- [x] Dedicated library for quoted replies (quotequail)
- [x] Edge case handling (attachments, inline images)
- [x] Non-destructive workflow (separate databases)
- [x] Batch processing for performance

### ✅ Token Reduction Target

- Target: 50-70% reduction
- Expected: 60% with standard level
- Measured: (to be validated with real run)

---

## Conclusion

This design provides a **robust, non-destructive, and repeatable** approach to optimizing email content for LLM consumption while preserving all original data. The two-command workflow gives users full control and transparency over the cleaning process.

**Key Innovations**:
1. **Separate clean command** - non-destructive, repeatable
2. **Three-level cleaning** - users choose their tradeoff
3. **Chinese-optimized** - critical `body_width=0` configuration
4. **Dual columns** - compare original vs cleaned side-by-side
5. **Statistical reporting** - measure actual token savings

This architecture was validated by both OpenAI Codex and Google Gemini with strong endorsement. 🎉
