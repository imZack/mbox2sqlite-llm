# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

mbox-to-sqlite is a Python CLI tool that loads email from .mbox files into SQLite databases. It provides two workflows:

1. **`mbox` command**: Import original emails (complete archive with all HTML, signatures, etc.)
2. **`clean` command**: Create LLM-optimized database (91% token reduction while preserving semantic content)

The tool uses `sqlite-utils` for database operations, `click` for the CLI interface, Python's `mailbox` module for parsing, `html2text` for HTML→Markdown conversion, and `quotequail` for signature removal.

## Development Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install in editable mode with test dependencies
pip install -e '.[test]'
```

## Common Commands

```bash
# Run all tests
pytest

# Run a specific test
pytest tests/test_mbox_to_sqlite.py::test_mbox

# Run a specific parametrized test
pytest tests/test_mbox_to_sqlite.py::test_mbox[None]
pytest tests/test_mbox_to_sqlite.py::test_mbox[other]

# Run the CLI directly during development
python -m mbox_to_sqlite mbox <db_path> <mbox_path>

# Or via the installed command
mbox-to-sqlite mbox <db_path> <mbox_path>

# Import with Chinese tokenization (recommended for Chinese content)
mbox-to-sqlite mbox <db_path> <mbox_path> --simple-tokenizer ./libsimple.dylib

# Create LLM-optimized cleaned database
mbox-to-sqlite clean <source_db> <dest_db> --level standard --simple-tokenizer ./libsimple.dylib

# Cleaning levels: minimal (40%), standard (91%), aggressive (95%)
mbox-to-sqlite clean emails.db emails-clean.db --level aggressive
```

## Architecture

### Two-Database Design

The tool now supports a two-phase workflow:

**Phase 1: Import (`mbox` command)**
- Creates original database with complete email content
- Schema: `payload` column contains raw HTML + plain text
- Use for: archival, compliance, debugging

**Phase 2: Clean (`clean` command)**
- Creates cleaned database optimized for LLM consumption
- Schema: `body_raw` (original) + `body_clean` (optimized) + `cleaning_stats` (JSON)
- Achieves 91% token reduction through:
  - HTML → Markdown conversion (tables preserved)
  - Signature/boilerplate removal
  - Whitespace normalization
- Use for: LLM queries, semantic search, analysis

### Core Components

- **mbox_to_sqlite/cli.py**: CLI implementation with two main commands
  - Uses Click groups/commands pattern
  - `mbox` command: Imports mbox files into original database (cli.py:55-104)
  - `clean` command: Creates LLM-optimized database from original (cli.py:107-253)
  - Leverages sqlite-utils for database operations and FTS setup
  - Uses generator pattern and batch processing for efficiency

- **mbox_to_sqlite/clean.py**: Email cleaning logic module
  - `EmailCleaner` class with three cleaning levels (minimal/standard/aggressive)
  - HTML→Markdown conversion using html2text (with `body_width=0` for Chinese)
  - Signature removal using pattern matching + quotequail library
  - Whitespace normalization and boilerplate detection

### Data Processing Flow

**Import Flow (`mbox` command)**:
1. **Read mbox file**: Uses Python's `mailbox.mbox()` to parse the file
2. **Extract message data**: Converts each message to a dict via `dict(message.items())` plus payload
3. **Upsert to database**: Uses `sqlite-utils` upsert_all with `message-id` as primary key
4. **Enable FTS**: Automatically creates full-text search indexes on payload and subject fields

**Cleaning Flow (`clean` command)**:
1. **Read source database**: Loads all emails from original database
2. **Clean each email**:
   - Extract text from HTML/multipart messages
   - Convert HTML → Markdown (preserving tables)
   - Remove signatures, boilerplate, quoted replies (depends on level)
   - Normalize whitespace
3. **Batch insert**: Process 1,000 emails per batch for performance
4. **Create FTS index**: Index on `body_clean` column (optimized content)
5. **Report statistics**: Show token savings, reduction percentage

### Database Schema

**Original Database** (`emails.db` from `mbox` command):
- All email headers as lowercase columns (from, to, subject, date, etc.)
- `payload` column: Raw message body (HTML + plain text, ~14KB avg)
- Primary key on `message-id`
- FTS tables for searching `payload` and `subject`

**Cleaned Database** (`emails-clean.db` from `clean` command):
- All email headers (same as original)
- `body_raw` column: Copy of original payload (for comparison)
- `body_clean` column: LLM-optimized content (Markdown, ~1.2KB avg)
- `cleaning_stats` column: JSON metadata about token savings
- Primary key on `message-id`
- FTS tables for searching `body_clean` and `subject`

### Testing

Tests use Click's `CliRunner` with isolated filesystem to:
- Test default table name ("messages") and custom table names
- Verify FTS tables are created correctly
- Validate message parsing and database insertion
- Sample test data in `tests/enron-sample.mbox`

## Chinese Text Search with Simple Tokenizer

The project includes support for the [simple tokenizer](https://github.com/wangfenjin/simple) for better Chinese/CJK text search:

- **Location**: `libsimple.dylib` in the project root
- **Source**: Built from https://github.com/wangfenjin/simple (commit 194c144)
- **Usage**: Add `--simple-tokenizer ./libsimple.dylib` flag when importing
- **Benefits**: Provides proper word segmentation for Chinese using jieba, plus pinyin search support

### Search Examples with Simple Tokenizer

```python
import sqlite3

conn = sqlite3.connect('emails.db')
conn.enable_load_extension(True)
conn.load_extension('./libsimple')  # Without .dylib extension
conn.enable_load_extension(False)

# Use simple_query() for automatic query construction
cursor = conn.execute("""
    SELECT subject, simple_highlight(messages_fts, 0, '[', ']') as highlighted
    FROM messages_fts
    WHERE messages_fts MATCH simple_query('會議記錄')
    LIMIT 10
""")
```

The simple tokenizer provides:
- **simple_query()**: Automatic FTS query construction (no need to learn FTS5 syntax)
- **simple_highlight()**: Highlight matched terms with custom delimiters
- **jieba_query()**: More precise phrase matching using jieba segmentation
- **Pinyin support**: Can search Chinese text using pinyin

## Important Design Decisions

### Chinese Text Handling (Critical)

**MUST configure html2text with `body_width=0`** to prevent line wrapping in Chinese text. Default 78-char wrapping inserts `\n` mid-sentence in CJK languages, breaking tokenization for LLMs.

```python
h = html2text.HTML2Text()
h.body_width = 0  # CRITICAL for Chinese!
```

### Two-Database Architecture

- **Original database is never modified** - cleaning creates a new database
- **Both `body_raw` and `body_clean` stored** in cleaned database for auditability
- Can re-run cleaning with different levels without re-importing mbox
- Enables side-by-side comparison and validation

### Signature Removal Strategy

Hybrid approach (recommended by Codex/Gemini reviews):
1. **Pattern matching** for known signatures (CSR policy, contact footers)
2. **Hash-based detection** for corpus-specific repeated text (optional via `--build-signature-db`)
3. **quotequail library** for quoted reply removal (aggressive level)

### Dependencies

See `setup.py` for full list. Key additions for cleaning:
- `html2text>=2020.1.16`: HTML→Markdown conversion
- `beautifulsoup4>=4.9.0`: HTML parsing fallback
- `quotequail>=0.2.0`: Quoted reply detection

## Version and Release

Version is defined in `setup.py` (currently "0.1a0"). The project uses GitHub Actions for CI (testing on Python 3.7-3.10) and publishing to PyPI.
