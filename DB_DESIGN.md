# Database Design

This document describes the SQLite database structure created by mbox-to-sqlite and provides query examples optimized for LLM consumption.

## ⚠️ Important: Two Database Types

mbox-to-sqlite creates **two types of databases** depending on which command you use:

### 1. Original Database (via `mbox` command)
**Purpose**: Preserve complete, unmodified email content for compliance, debugging, or archival.

**Created by**:
```bash
mbox-to-sqlite mbox emails.db archive.mbox --simple-tokenizer ./libsimple.dylib
```

**Characteristics**:
- ✅ Complete original content preserved
- ✅ All HTML markup, signatures, footers included
- ✅ Larger size (~14KB avg per email)
- ✅ Higher token consumption when queried by LLMs
- 📊 Use for: Legal compliance, full email archive, debugging

### 2. Cleaned Database (via `clean` command)
**Purpose**: Optimized for LLM consumption with reduced token waste while preserving semantic content.

**Created by**:
```bash
mbox-to-sqlite clean emails.db emails-clean.db --level standard --simple-tokenizer ./libsimple.dylib
```

**Characteristics**:
- ✅ LLM-optimized content (91% token reduction)
- ✅ HTML converted to Markdown, tables preserved
- ✅ Signatures and boilerplate removed
- ✅ Smaller size (~1.2KB avg per email)
- ✅ Both original and cleaned versions stored
- 📊 Use for: LLM queries, semantic search, analysis

---

## Database Comparison

| Feature | Original DB | Cleaned DB |
|---------|-------------|------------|
| **Payload Column** | `payload` | `body_raw` + `body_clean` |
| **Content Type** | Raw (HTML + plain text) | Markdown (optimized) |
| **Avg Size/Email** | 14 KB | 1.2 KB (body_clean) |
| **Token Count** | ~7K tokens/email | ~600 tokens/email |
| **FTS Index** | On `payload` | On `body_clean` |
| **Tables Preserved** | No (raw HTML) | Yes (Markdown) |
| **Signatures** | Included | Removed |
| **Boilerplate** | Included | Removed |
| **Use Case** | Archive, compliance | LLM analysis, search |

---

## When to Use Which Database?

### Use Original Database (`emails.db`) When:
- 📋 Legal compliance or audit requirements
- 🐛 Debugging import issues or email parsing
- 📁 Long-term archival of complete email history
- 🔍 You need exact original formatting (HTML layout, images)
- 📊 Analyzing email metadata or routing headers

### Use Cleaned Database (`emails-clean.db`) When:
- 🤖 Querying with LLMs (Claude, GPT, etc.)
- 🔎 Semantic search across email corpus
- 📈 Token-constrained analysis (need to fit more emails in context)
- 📊 Business intelligence or data analysis
- 💬 Building email-based chatbots or assistants

**Recommendation**: Create both databases and use the appropriate one for your task.

---

## Database Schemas

### Original Database Schema

**File**: `emails.db` (created by `mbox` command)

```sql
CREATE TABLE messages (
  [message-id] TEXT PRIMARY KEY,
  [from] TEXT,
  [to] TEXT,
  [cc] TEXT,
  subject TEXT,
  date TEXT,
  payload TEXT,              -- ⚠️ Original content (14KB avg, includes HTML)
  [in-reply-to] TEXT,
  references TEXT,
  [thread-topic] TEXT,
  [thread-index] TEXT,
  ... all email headers ...
);

CREATE VIRTUAL TABLE messages_fts USING FTS5 (
  payload, subject,          -- FTS on original payload
  tokenize='simple',
  content=[messages]
);
```

### Cleaned Database Schema

**File**: `emails-clean.db` (created by `clean` command)

```sql
CREATE TABLE messages (
  [message-id] TEXT PRIMARY KEY,
  [from] TEXT,
  [to] TEXT,
  [cc] TEXT,
  subject TEXT,
  date TEXT,
  body_raw TEXT,             -- Copy of original payload (for comparison)
  body_clean TEXT,           -- ✨ LLM-optimized (1.2KB avg, Markdown)
  cleaning_stats TEXT,       -- JSON: {"original_bytes": 14000, "clean_bytes": 1200, "reduction_percent": 91.4}
  [in-reply-to] TEXT,
  references TEXT,
  [thread-topic] TEXT,
  [thread-index] TEXT,
  ... all email headers ...
);

CREATE VIRTUAL TABLE messages_fts USING FTS5 (
  body_clean, subject,       -- ✨ FTS on CLEANED content only
  tokenize='simple',
  content=[messages]
);
```

---

## Key Column Descriptions

### Common Columns (Both Databases)

| Column | Description |
|--------|-------------|
| `message-id` | Primary key, unique identifier for each email |
| `from` | Email sender |
| `to` | Email recipient(s) |
| `cc` | Carbon copy recipients |
| `subject` | Email subject line |
| `date` | Email date/time |
| `in-reply-to` | Message-ID of the email being replied to |
| `references` | Space-separated list of message-IDs in the conversation thread |
| `thread-topic` | Thread subject (Microsoft Exchange) |
| `thread-index` | Thread identifier (Microsoft Exchange) |

### Original Database Only

| Column | Description |
|--------|-------------|
| `payload` | **Raw email content** (14KB avg) - includes HTML markup, signatures, all parts separated by `---PART---` |

### Cleaned Database Only

| Column | Description |
|--------|-------------|
| `body_raw` | Copy of original `payload` (for comparison/debugging) |
| `body_clean` | **LLM-optimized content** (1.2KB avg) - Markdown format, signatures removed, tables preserved |
| `cleaning_stats` | JSON metadata: `{"original_bytes": N, "clean_bytes": N, "reduction_percent": X}` |

### Email Routing & Authentication Headers

Headers with multiple values (like `received`, `authentication-results`) are concatenated with newlines:

- `received`: Complete email routing path (multiple mail servers)
- `authentication-results`: Email authentication checks (DKIM, SPF, DMARC)
- `dkim-signature`: Digital signatures for email verification
- `arc-seal`, `arc-message-signature`, `arc-authentication-results`: ARC authentication chain

### Other Headers

All email headers are stored as lowercase column names. Headers not present in a message will have NULL values.

## Full-Text Search Setup

**IMPORTANT**: For Chinese content, the database MUST be created with the `simple` tokenizer for optimal search results.

### Import Command

```bash
# Recommended: Use simple tokenizer for Chinese text
mbox-to-sqlite mbox emails.db archive.mbox --simple-tokenizer ./libsimple.dylib

# Default (English-optimized, poor for Chinese)
mbox-to-sqlite mbox emails.db archive.mbox
```

The `messages_fts` table indexes:
- `payload`: Email body content
- `subject`: Email subject line

## SQLite3 CLI Usage

All examples below are optimized for **minimal output suitable for LLM consumption**.

Query examples are provided for **both database types** - choose the appropriate database for your use case.

### Setup: Load Simple Tokenizer

For Chinese search, always load the simple tokenizer extension first:

```bash
# For original database
sqlite3 emails.db

# For cleaned database (recommended for LLM queries)
sqlite3 emails-clean.db
```

```sql
.load ./libsimple
```

---

## Query Examples by Database Type

### 🔵 Original Database Queries (`emails.db`)

Use these when you need complete original content.

#### 1. Search original emails (includes HTML, signatures)

```sql
-- Search in original payload (larger, includes all content)
SELECT [message-id], [from], subject, date
FROM messages_fts
WHERE messages_fts MATCH simple_query('會議記錄')
ORDER BY date DESC
LIMIT 10;
```

#### 2. Get complete original email

```sql
-- Retrieve full original email (HTML + plain text)
SELECT
  [message-id],
  [from],
  [to],
  subject,
  date,
  payload  -- ⚠️ Contains raw HTML, signatures, etc.
FROM messages
WHERE [message-id] = '<target-message-id>';
```

---

### 🟢 Cleaned Database Queries (`emails-clean.db`) **← Recommended for LLMs**

Use these for LLM consumption, analysis, and semantic search.

#### 1. Search cleaned emails (LLM-optimized)

```sql
-- Search in cleaned content (Markdown, no signatures)
SELECT [message-id], [from], subject, date
FROM messages_fts
WHERE messages_fts MATCH simple_query('會議記錄')
ORDER BY date DESC
LIMIT 10;
```

#### 2. Search with context highlighting

```sql
-- Show matched content with highlighting
SELECT
  subject,
  substr(simple_highlight(messages_fts, 0, '【', '】'), 1, 300) as context
FROM messages_fts
WHERE messages_fts MATCH simple_query('會議記錄')
LIMIT 5;
```

#### 3. Get LLM-optimized email content

```sql
-- ✨ Best for LLM analysis - cleaned, Markdown format
SELECT
  [message-id],
  [from],
  [to],
  subject,
  date,
  body_clean  -- ✨ Optimized: Markdown, no signatures, ~1.2KB
FROM messages
WHERE [message-id] = '<target-message-id>';
```

#### 4. Compare original vs cleaned (for debugging)

```sql
-- Side-by-side comparison
SELECT
  subject,
  length(body_raw) as original_bytes,
  length(body_clean) as cleaned_bytes,
  json_extract(cleaning_stats, '$.reduction_percent') as reduction_percent,
  substr(body_clean, 1, 200) as cleaned_preview
FROM messages
WHERE [message-id] = '<target-message-id>';
```

#### 5. Find best token savings

```sql
-- Emails with highest token reduction
SELECT
  subject,
  length(body_raw) as original,
  length(body_clean) as cleaned,
  json_extract(cleaning_stats, '$.reduction_percent') as saved_percent
FROM messages
ORDER BY saved_percent DESC
LIMIT 10;
```

---

### Common Queries (Work on Both Databases)

These queries work identically on both `emails.db` and `emails-clean.db` since they use common columns.

#### 6. Find emails from specific sender

```sql
SELECT [message-id], subject, date
FROM messages
WHERE [from] LIKE '%user@example.com%'
ORDER BY date DESC
LIMIT 20;
```

#### 7. Find emails in date range

```sql
SELECT [message-id], [from], subject, date
FROM messages
WHERE date >= '2025-12-01'
  AND date <= '2025-12-31'
ORDER BY date DESC;
```

#### 8. Count emails by sender

```sql
-- Summary of email volume by sender
SELECT [from], COUNT(*) as email_count
FROM messages
GROUP BY [from]
ORDER BY email_count DESC
LIMIT 20;
```

### Thread and Conversation Queries

These work on both databases. For LLM consumption, use `body_clean` instead of `payload`.

#### 9. Find email thread by message-id

```sql
-- For Original Database (emails.db):
-- Get the original message
SELECT [message-id], subject, [from], date, payload
FROM messages
WHERE [message-id] = '<target-message-id>';

-- Get all replies
SELECT [message-id], subject, [from], date, payload
FROM messages
WHERE [in-reply-to] = '<target-message-id>'
   OR references LIKE '%<target-message-id>%'
ORDER BY date ASC;
```

```sql
-- For Cleaned Database (emails-clean.db) - Recommended for LLMs:
-- Get the original message
SELECT [message-id], subject, [from], date, body_clean
FROM messages
WHERE [message-id] = '<target-message-id>';

-- Get all replies
SELECT [message-id], subject, [from], date, body_clean
FROM messages
WHERE [in-reply-to] = '<target-message-id>'
   OR references LIKE '%<target-message-id>%'
ORDER BY date ASC;
```

#### 7. Get complete conversation thread

```sql
-- First, find all message-ids in the thread from References header
WITH RECURSIVE thread AS (
  -- Start with a specific message
  SELECT [message-id], [in-reply-to], references, subject, [from], date, payload
  FROM messages
  WHERE [message-id] = '<starting-message-id>'

  UNION

  -- Find replies
  SELECT m.[message-id], m.[in-reply-to], m.references, m.subject, m.[from], m.date, m.payload
  FROM messages m
  INNER JOIN thread t ON (
    m.[in-reply-to] = t.[message-id]
    OR m.references LIKE '%' || t.[message-id] || '%'
  )
)
SELECT [message-id], [from], subject, date, substr(payload, 1, 200) as preview
FROM thread
ORDER BY date ASC;
```

#### 8. Find email threads by subject

```sql
-- Find all emails with similar subject (same thread)
SELECT [message-id], [from], subject, date
FROM messages
WHERE subject LIKE '%PRJ-2024%'
   OR [thread-topic] LIKE '%PRJ-2024%'
ORDER BY date ASC;
```

### Advanced Search Queries

#### 9. Search with multiple keywords (AND)

```sql
SELECT subject, date, substr(payload, 1, 200) as preview
FROM messages_fts
WHERE messages_fts MATCH simple_query('會議記錄 PRJ-2024')
ORDER BY date DESC
LIMIT 10;
```

#### 10. Search in subject only

```sql
SELECT [message-id], subject, [from], date
FROM messages
WHERE subject LIKE '%會議%'
ORDER BY date DESC
LIMIT 10;
```

#### 11. Find emails with attachments

```sql
-- Emails that likely have attachments (multipart content)
SELECT [message-id], subject, [from], date
FROM messages
WHERE [content-type] LIKE '%multipart%'
  AND [x-ms-has-attach] = 'yes'
ORDER BY date DESC;
```

#### 12. Count emails by sender

```sql
-- Summary of email volume by sender
SELECT [from], COUNT(*) as email_count
FROM messages
GROUP BY [from]
ORDER BY email_count DESC
LIMIT 20;
```

#### 13. Get recent emails (last N days)

```sql
SELECT [message-id], [from], subject, date
FROM messages
WHERE date >= date('now', '-7 days')
ORDER BY date DESC;
```

### LLM-Optimized Output Formats

#### 14. Compact summary for LLM analysis

```sql
-- Minimal fields for LLM to understand email context
SELECT
  [message-id] as id,
  [from] as sender,
  [to] as recipient,
  subject,
  date,
  substr(payload, 1, 500) as content_preview
FROM messages
WHERE subject LIKE '%專案討論%'
ORDER BY date DESC
LIMIT 10;
```

#### 15. Thread summary for LLM

```sql
-- Conversation thread in chronological order
SELECT
  [from] || ' → ' || [to] as flow,
  date,
  subject,
  substr(payload, 1, 200) as message
FROM messages
WHERE subject LIKE '%RE: PRJ-2024%'
   OR [thread-topic] LIKE '%PRJ-2024%'
ORDER BY date ASC;
```

#### 16. Email with all context for deep analysis

```sql
-- Complete email data for LLM processing
.mode json
SELECT
  [message-id],
  [from],
  [to],
  cc,
  subject,
  date,
  [in-reply-to],
  payload
FROM messages
WHERE [message-id] = '<target-id>';
```

### Useful SQLite3 Commands

```sql
-- Set output mode for readability
.mode column
.headers on
.width 30 60 20

-- Export to JSON (ideal for LLM)
.mode json
.once output.json
SELECT * FROM messages LIMIT 10;

-- Export to CSV
.mode csv
.headers on
.output emails.csv
SELECT [message-id], [from], subject, date FROM messages;
.output stdout

-- Show database info
.tables
.schema messages

-- Enable timing for performance
.timer on

-- Quit
.quit
```

## Query Tips for LLM Consumption

### General Tips

1. **Use LIMIT**: Always limit results to avoid overwhelming output
2. **Use substr()**: Truncate long text fields to preview length
3. **Select specific columns**: Don't use `SELECT *` - choose only needed fields
4. **Use JSON mode**: For structured LLM consumption, use `.mode json`
5. **Date sorting**: Always include `ORDER BY date` for chronological context
6. **Search with simple_query()**: For Chinese text, always use `simple_query()` wrapper

### Database-Specific Tips

**For Original Database (`emails.db`)**:
- Use `payload` column for content
- Expect HTML markup, signatures, and `---PART---` separators
- ~14KB avg per email, ~7K tokens
- Good for archival, compliance, debugging

**For Cleaned Database (`emails-clean.db`)** ← **Recommended for LLMs**:
- Use `body_clean` column for content (NOT `payload`!)
- Expect Markdown format, no signatures
- ~1.2KB avg per email, ~600 tokens
- Can compare with `body_raw` for validation
- Check `cleaning_stats` for reduction metrics

## Simple Tokenizer Functions

When the simple tokenizer is loaded (`.load ./libsimple`), you get these helper functions:

| Function | Purpose |
|----------|---------|
| `simple_query('text')` | Convert plain text to FTS5 query automatically |
| `simple_highlight(fts_table, column_index, '[', ']')` | Highlight matches in search results |
| `jieba_query('text')` | More precise query using jieba word segmentation |
| `simple_snippet(...)` | Extract snippets around matches |

### Example: Complete Search Workflow

```sql
-- 1. Load extension
.load ./libsimple

-- 2. Search with highlighting
.mode column
.headers on
.width 40 80

SELECT
  subject,
  simple_highlight(messages_fts, 0, '【', '】') as matched_content
FROM messages_fts
WHERE messages_fts MATCH simple_query('會議記錄')
LIMIT 5;

-- 3. Get full thread context
SELECT [message-id], [from], subject, date, payload
FROM messages
WHERE subject LIKE '%PRJ-2024%'
ORDER BY date ASC;
```

## Performance Notes

### Query Performance
- FTS queries are fast (indexed search)
- LIKE queries on non-indexed columns can be slow on large databases
- Use FTS for content search, direct column queries for metadata
- The simple tokenizer adds ~5-10% overhead but provides significantly better Chinese search

### Database Size Comparison (10,019 emails from archive.mbox)

| Database | File Size | Payload Size | Avg/Email | Notes |
|----------|-----------|--------------|-----------|-------|
| **Original** | 337 MB | 141 MB | 14 KB | Includes HTML, signatures |
| **Cleaned** | 273 MB | 12 MB | 1.2 KB | 91.5% payload reduction |
| **Reduction** | -19% | -91.5% | -91.4% | 68M tokens saved |

### LLM Context Window Impact

**With Original Database**:
- Claude 3.5 Sonnet (200K context): ~400 emails max
- GPT-4 Turbo (128K context): ~250 emails max
- Token usage: ~7K tokens/email

**With Cleaned Database**:
- Claude 3.5 Sonnet (200K context): ~1,000 emails max
- GPT-4 Turbo (128K context): ~625 emails max
- Token usage: ~600 tokens/email
- **2.5x more emails fit in same context window** ✨

---

## Quick Reference Guide

### Decision Matrix: Which Database Should I Use?

| Your Goal | Database | Column to Query |
|-----------|----------|-----------------|
| 🤖 LLM analysis/queries | **Cleaned** | `body_clean` |
| 🔎 Semantic search | **Cleaned** | `body_clean` |
| 📊 Token-efficient analysis | **Cleaned** | `body_clean` |
| 📋 Legal/compliance | **Original** | `payload` |
| 🐛 Debug parsing issues | **Original** | `payload` |
| 📁 Complete archive | **Original** | `payload` |
| 🔍 Need exact HTML layout | **Original** | `payload` |

### Common Mistakes to Avoid

❌ **DON'T**:
- Query `payload` column in cleaned database (doesn't exist!)
- Use cleaned database for legal/compliance requirements
- Skip creating the original database (always create both!)
- Forget to load `libsimple` extension for Chinese search

✅ **DO**:
- Use `body_clean` in cleaned database for LLM queries
- Create both databases (original + cleaned)
- Use `--simple-tokenizer` flag for Chinese content
- Check `cleaning_stats` to verify token savings

### Complete Workflow Example

```bash
# Step 1: Import original (preserve everything)
mbox-to-sqlite mbox emails.db archive.mbox --simple-tokenizer ./libsimple.dylib

# Step 2: Create cleaned version (LLM-optimized)
mbox-to-sqlite clean emails.db emails-clean.db \
  --level standard \
  --simple-tokenizer ./libsimple.dylib

# Step 3: Query cleaned database for LLM
sqlite3 emails-clean.db
.load ./libsimple
SELECT subject, body_clean FROM messages
WHERE messages_fts MATCH simple_query('專案討論')
LIMIT 10;
```

---

## Summary

**mbox-to-sqlite now supports two workflows**:

1. **Traditional**: `mbox` command → Original database (complete archive)
2. **LLM-Optimized**: `clean` command → Cleaned database (91% token reduction)

**Key Insight**: The cleaned database achieves **91.5% token reduction** while preserving semantic content through:
- HTML → Markdown conversion (tables preserved)
- Signature/boilerplate removal (CSR policies, contact info)
- Whitespace normalization
- Inline image placeholders

**Recommendation**: Always create both databases. Use the cleaned version for LLM queries and the original for archival/compliance.
