# mbox-to-sqlite

Load email from .mbox files into SQLite, with Gmail export support and LLM optimization

## Why This Fork?

This is a fork of [simonw/mbox-to-sqlite](https://github.com/simonw/mbox-to-sqlite) with enhancements for real-world email processing:

**Problem**: The original tool couldn't reliably process Gmail's exported .mbox files (from Google Takeout), which have different formatting and encoding quirks.

**Solution**: Vibecoded fixes and added features I needed:
- **Gmail Export Support**: Handles Gmail Takeout .mbox files correctly
- **Chinese/CJK Text Search**: Integrated [simple tokenizer](https://github.com/wangfenjin/simple) for proper Chinese word segmentation and FTS
- **LLM Optimization**: New `clean` command creates token-optimized databases (91% token reduction) by converting HTML→Markdown, removing signatures, and normalizing whitespace
- **Two-Database Workflow**: Preserve original emails while creating cleaned versions for LLM consumption

Credits to [Simon Willison](https://github.com/simonw) for the original project.

## Installation

Install this tool using `pip`:

    pip install mbox2sqlite-llm

Or install from source:

    git clone https://github.com/imZack/mbox2sqlite-llm.git
    cd mbox2sqlite-llm
    pip install -e .

## Usage

### Quick Start

Import a Gmail Takeout .mbox file:

    mbox2sqlite-llm mbox emails.db path/to/All mail Including Spam and Trash.mbox

Create an LLM-optimized cleaned version:

    mbox2sqlite-llm clean emails.db emails-clean.db --level standard

Explore with [Datasette](https://datasette.io/):

    datasette emails-clean.db

### Chinese/CJK Text Support

For Chinese email content, use the simple tokenizer for proper word segmentation:

    # Import with Chinese FTS
    mbox2sqlite-llm mbox emails.db gmail.mbox --simple-tokenizer ./libsimple.dylib

    # Clean with Chinese FTS
    mbox2sqlite-llm clean emails.db emails-clean.db --simple-tokenizer ./libsimple.dylib

Download `libsimple.dylib` (macOS) from [wangfenjin/simple](https://github.com/wangfenjin/simple) or build from source.

### Commands

**Import emails** (preserves original content):
```bash
mbox2sqlite-llm mbox emails.db messages.mbox
```

**Clean for LLM usage** (91% token reduction):
```bash
# Standard cleaning (recommended)
mbox2sqlite-llm clean emails.db emails-clean.db --level standard

# Aggressive cleaning (95% reduction)
mbox2sqlite-llm clean emails.db emails-clean.db --level aggressive

# Minimal cleaning (40% reduction, preserves more context)
mbox2sqlite-llm clean emails.db emails-clean.db --level minimal
```

### Try It Out

Test against a sample from the [Enron corpus](https://en.wikipedia.org/wiki/Enron_Corpus):

    curl -O https://raw.githubusercontent.com/ivanhb/EMA/master/server/data/mbox/enron/mbox-enron-white-s-all.mbox
    mbox2sqlite-llm mbox enron.db mbox-enron-white-s-all.mbox
    mbox2sqlite-llm clean enron.db enron-clean.db
    datasette enron-clean.db

## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:

    cd mbox-to-sqlite
    python -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
