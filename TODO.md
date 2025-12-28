# TODO

This document tracks pending tasks, known issues, and future enhancements for mbox-to-sqlite.

---

## 🔴 High Priority

### Testing

- [ ] Create comprehensive test fixtures for cleaning functionality
  - [ ] Chinese email with HTML table (verify `body_width=0` preserves structure)
  - [ ] English email with links (ensure Markdown link preservation)
  - [ ] Multipart email (plain + HTML) - verify no content duplication
  - [ ] Email with CSR footer (confirm removal without false positives)
  - [ ] Forwarded thread (test quoted reply removal in aggressive mode)
  - [ ] Email with attachments (verify metadata placeholder handling)
  - [ ] Mixed CJK/English content (token estimation accuracy)

- [ ] Update existing test suite for new `clean` command
  - [ ] Test all three cleaning levels (minimal/standard/aggressive)
  - [ ] Verify `cleaning_stats` JSON structure
  - [ ] Test `--build-signature-db` flag
  - [ ] Test with and without `--simple-tokenizer`
  - [ ] Edge case: empty payloads
  - [ ] Edge case: very large emails (>100KB)

### Documentation

- [ ] Add cleaning examples to README.md
  - [ ] Before/after token count examples
  - [ ] Use case scenarios (when to use original vs cleaned)
  - [ ] Quick start guide for two-database workflow

- [ ] Update .gitignore
  - [ ] Decide whether to commit `libsimple.dylib` or add `*.dylib` to .gitignore
  - [ ] Document how users should obtain/build the tokenizer

---

## 🟡 Medium Priority

### Code Quality

- [ ] Improve contact signature removal accuracy
  - Currently removes common signature patterns - could be more aggressive
  - Consider pattern variations (Thanks!, Best regards, etc.)
  - Make signature patterns configurable via JSON file

- [ ] Add configuration file support
  - [ ] JSON config for custom cleaning rules
  - [ ] Per-domain signature templates
  - [ ] User-defined boilerplate patterns
  - [ ] Custom HTML→Markdown settings

- [ ] Enhance error handling
  - [ ] Better error messages for malformed mbox files
  - [ ] Graceful degradation if html2text fails
  - [ ] Warning when libsimple extension not found
  - [ ] Progress bar error recovery

### Performance

- [ ] Optimize signature database building
  - Currently loads all emails into memory
  - Could use streaming approach for large corpora
  - Cache signature database between runs

- [ ] Add incremental cleaning support
  - [ ] Only process new emails added since last clean
  - [ ] Update existing cleaned database instead of recreating
  - [ ] Track cleaning version/timestamp in metadata

### CLI Enhancements

- [ ] Add `--dry-run` flag to `clean` command
  - Preview cleaning results without creating database
  - Show sample before/after comparisons
  - Estimate total token savings

- [ ] Add `--sample` flag to `clean` command
  - Clean only N random emails for testing
  - Useful for experimenting with cleaning levels

- [ ] Add comparison/diff command
  - [ ] `mbox-to-sqlite compare <original_db> <cleaned_db>`
  - Show side-by-side before/after for sample emails
  - Generate statistics report

---

## 🟢 Low Priority / Nice to Have

### Feature Enhancements (from Codex/Gemini Reviews)

- [ ] **Attachment metadata extraction**
  - Extract filename, MIME type, size from attachments
  - Add structured data to `body_clean`: `[Attachment: invoice.pdf, 245KB, application/pdf]`
  - Store attachment metadata in separate table for querying

- [ ] **Calendar invite parsing**
  - Detect `text/calendar` MIME parts
  - Extract event summary, time, location, attendees
  - Add to cleaned content as structured data

- [ ] **Nested message handling**
  - Hoist `message/rfc822` parts (forwarded emails) to separate rows
  - Preserve forwarded email context
  - Link parent and nested messages via metadata

- [ ] **Flowed text support**
  - Handle `format=flowed` RFC 3676 properly
  - De-flow wrapped paragraphs correctly

- [ ] **Image OCR support** (optional)
  - Extract text from inline images via OCR
  - Useful for scanned documents in emails
  - Make optional (requires external dependency)

### Advanced Cleaning

- [ ] **Machine learning signature detection**
  - Train classifier on email corpus
  - Auto-detect variable signatures (names change, format stays)
  - More robust than pattern matching alone

- [ ] **Quote trimming intelligence**
  - Preserve first reply in thread, remove deeper quotes
  - Context-aware quote removal (keep relevant context)
  - Don't remove quotes that add important information

- [ ] **Marketing/disclaimer removal**
  - Detect and remove legal disclaimers
  - Remove promotional footers
  - Strip email tracking pixels/links

- [ ] **Thread reconstruction**
  - Build complete thread trees
  - Deduplicate repeated content in threads
  - Generate thread summaries

### Alternative Conversion Strategies

- [ ] Test alternative HTML→Markdown libraries (from Codex review)
  - [ ] **Markdownify**: More control over rendering
  - [ ] **Pandoc**: Best fidelity (if available)
  - [ ] **Trafilatura/Readability**: Excellent boilerplate removal
  - Compare token savings and quality
  - Make library selection configurable

- [ ] **BeautifulSoup-only mode**
  - Fallback when html2text produces poor results
  - Simpler plain text extraction
  - Option for users who prefer simpler output

### Database Enhancements

- [ ] Add database metadata table
  - Track cleaning parameters used
  - Record creation timestamp, source mbox file
  - Version info for schema migrations

- [ ] Index optimization
  - Add indexes on frequently queried columns (date, from, to)
  - Analyze query patterns and optimize
  - Document index strategy

- [ ] Support for other email formats
  - [ ] Maildir support
  - [ ] PST/OST support (via external tool)
  - [ ] EML files
  - [ ] IMAP direct import

### Output Formats

- [ ] Export cleaned emails to other formats
  - [ ] JSON (for LLM consumption)
  - [ ] CSV (for spreadsheet analysis)
  - [ ] Markdown files (one per email)
  - [ ] JSONL (for streaming/batch processing)

- [ ] LLM-specific export formats
  - [ ] Claude-optimized format (XML tags for structure)
  - [ ] GPT-optimized format (JSON with role/content)
  - [ ] Embedding-optimized (chunked by semantic boundaries)

---

## 🔧 Technical Debt

### Code Organization

- [ ] Refactor `clean.py` into smaller modules
  - `clean/converters.py`: HTML→Markdown conversion
  - `clean/signatures.py`: Signature detection/removal
  - `clean/normalizers.py`: Whitespace and text normalization
  - `clean/stats.py`: Statistics and reporting

- [ ] Add type hints throughout codebase
  - [ ] Type hints for `cli.py`
  - [ ] Type hints for `clean.py`
  - [ ] mypy configuration and CI check

- [ ] Improve logging
  - [ ] Add structured logging (not just click.echo)
  - [ ] Log levels (DEBUG, INFO, WARNING, ERROR)
  - [ ] Optional verbose mode for troubleshooting

### Testing Infrastructure

- [ ] Set up CI/CD for cleaning tests
  - [ ] Add cleaning tests to GitHub Actions
  - [ ] Test across Python versions (3.7-3.11+)
  - [ ] Test with different libsimple versions

- [ ] Add performance benchmarks
  - [ ] Benchmark cleaning speed (emails/second)
  - [ ] Memory usage profiling
  - [ ] Compare cleaning levels performance

- [ ] Add integration tests
  - [ ] End-to-end workflow tests (import → clean → query)
  - [ ] Test with real-world mbox files
  - [ ] Validate FTS search quality

### Dependencies

- [ ] Pin dependency versions for reproducibility
  - Currently using `>=` which can break
  - Consider version ranges or lock files

- [ ] Evaluate quotequail alternatives
  - Library seems unmaintained
  - Consider implementing simple quote detection in-house
  - Or find more active alternative

- [ ] Make libsimple optional
  - Should work without simple tokenizer (fallback to default)
  - Better error messages when extension not available
  - Document how to build/obtain libsimple

---

## 📝 Documentation Improvements

### User Documentation

- [ ] Add tutorial/walkthrough
  - Step-by-step guide for new users
  - Common use cases (LLM analysis, email search, etc.)
  - Troubleshooting section

- [ ] Create FAQ document
  - "Why two databases?"
  - "How much disk space will I need?"
  - "Can I delete the original database after cleaning?"
  - "How do I rebuild the cleaned database?"

- [ ] Add video demo/screencast
  - Show import → clean → query workflow
  - Demonstrate token savings
  - Compare search quality with/without simple tokenizer

### Developer Documentation

- [ ] Add CONTRIBUTING.md
  - Development setup instructions
  - Code style guidelines
  - How to run tests
  - Pull request process

- [ ] Document cleaning algorithm
  - Detailed explanation of each cleaning step
  - Why certain design decisions were made
  - Performance characteristics of each level

- [ ] Add architecture diagrams
  - Data flow diagram (mbox → DB → cleaned DB)
  - Class hierarchy for cleaning module
  - Decision tree for cleaning levels

---

## 🌟 Future Ideas (Brainstorming)

### Web UI

- [ ] Simple web interface for browsing cleaned emails
  - Flask/FastAPI backend serving from SQLite
  - Search with highlighting
  - Thread view
  - Compare original vs cleaned side-by-side

### LLM Integration

- [ ] Built-in LLM query interface
  - [ ] `mbox-to-sqlite ask <db> "question about emails"`
  - Direct integration with Claude/GPT APIs
  - Automatic context management (select relevant emails)
  - Streaming responses

- [ ] Email embeddings
  - Generate embeddings for semantic search
  - Store in separate table
  - Vector similarity search for finding related emails

### Analytics

- [ ] Email analytics dashboard
  - Sender/recipient statistics
  - Time-series analysis (emails over time)
  - Thread depth analysis
  - Token usage visualization

- [ ] Cleaning quality metrics
  - False positive detection (important content removed?)
  - Compression ratio per email type
  - Table preservation accuracy
  - Link preservation rate

### Plugin System

- [ ] Plugin architecture for custom cleaners
  - Users can add custom cleaning rules
  - Third-party signature detectors
  - Custom HTML→Markdown converters
  - Domain-specific cleaning logic

---

## ✅ Completed

### Recently Completed

- [x] Implement two-database architecture (mbox + clean commands)
- [x] HTML→Markdown conversion with html2text
- [x] Chinese text handling (body_width=0)
- [x] Three cleaning levels (minimal/standard/aggressive)
- [x] Signature removal (CSR policy, contact footers)
- [x] Inline image placeholder replacement
- [x] Batch processing (1,000 emails per batch)
- [x] Progress bars and statistics reporting
- [x] FTS integration with simple tokenizer
- [x] Dual column schema (body_raw + body_clean)
- [x] Cleaning statistics (JSON metadata)
- [x] Update DB_DESIGN.md with two-database documentation
- [x] Update CLAUDE.md with new architecture
- [x] Create CLEANING_DESIGN.md with complete design doc
- [x] Integration with quotequail for quoted reply removal
- [x] Codex and Gemini design review
- [x] Build and integrate libsimple.dylib for Chinese tokenization

---

## 🐛 Known Issues

### Current Bugs/Limitations

- **Contact signature removal is incomplete**
  - Currently removes common department signature patterns
  - Some variations still slip through
  - Need more comprehensive pattern matching

- **HTML→Markdown edge cases**
  - Very complex nested tables may not convert perfectly
  - Some Office-specific HTML tags create noise
  - Inline CSS occasionally leaks through

- **quotequail dependency**
  - Library appears unmaintained (last update 2019)
  - May break on Python 3.11+
  - Consider replacing or vendoring

- **Memory usage**
  - `--build-signature-db` loads entire corpus into memory
  - May fail on very large mbox files (>1GB)
  - Need streaming approach

### Edge Cases to Test

- [ ] Email with no subject
- [ ] Email with non-UTF-8 encoding (ISO-8859-1, Big5, etc.)
- [ ] Email with broken/malformed HTML
- [ ] Email with no text content (attachments only)
- [ ] Email with deeply nested MIME structure (>10 levels)
- [ ] Email with circular references in thread headers
- [ ] Very long emails (>1MB payload)
- [ ] Emails with null bytes or control characters

---

## 📊 Metrics to Track

### Quality Metrics

- [ ] Token reduction rate by cleaning level
- [ ] Table preservation accuracy (manual review)
- [ ] Link preservation rate
- [ ] False positive rate (important content removed)
- [ ] False negative rate (boilerplate not removed)

### Performance Metrics

- [ ] Emails processed per second
- [ ] Memory usage per 1,000 emails
- [ ] Database size growth rate
- [ ] FTS query performance (original vs cleaned)
- [ ] Time to first result (import + clean + query)

### User Experience Metrics

- [ ] Setup time (install → first query)
- [ ] Documentation clarity (via user feedback)
- [ ] Error recovery rate (% of errors that are actionable)
- [ ] Feature discovery (how many users find cleaning command?)

---

## 🎯 Version Roadmap

### v0.2 (Next Release)

- [ ] Fix critical bugs from v0.1
- [ ] Complete test coverage for cleaning
- [ ] Update README with cleaning examples
- [ ] Add `--dry-run` flag
- [ ] Improve signature removal accuracy

### v0.3 (Future)

- [ ] Attachment metadata extraction
- [ ] Configuration file support
- [ ] Incremental cleaning
- [ ] Performance optimizations

### v1.0 (Stable)

- [ ] Production-ready quality
- [ ] Complete documentation
- [ ] Stable API
- [ ] Comprehensive test suite
- [ ] Performance benchmarks

---

## 📞 Community Requests

*To be filled in as users request features*

- [ ] (None yet - just released!)

---

## Notes

- This TODO is a living document - update as priorities change
- Mark items completed with [x] and move to "Completed" section
- Add dates when items are completed for tracking velocity
- Link to GitHub issues when created for specific items
