import click
import sqlite_utils
import mailbox
import json
from email import policy
from email.header import decode_header
from .clean import EmailCleaner, analyze_cleaning_impact


def decode_header_value(header_value):
    """Decode a MIME-encoded header value.

    Email headers like Subject can be MIME-encoded (RFC 2047) with formats like:
    =?UTF-8?B?...?= (Base64) or =?UTF-8?Q?...?= (Quoted-Printable)

    This function decodes them properly, handling charset encoding.
    """
    if not header_value:
        return header_value

    decoded_parts = []
    for part, encoding in decode_header(header_value):
        if isinstance(part, bytes):
            # Decode bytes to string using the specified encoding or fallback to utf-8
            try:
                decoded_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
            except (LookupError, AttributeError):
                decoded_parts.append(part.decode('utf-8', errors='replace'))
        else:
            # Already a string
            decoded_parts.append(part)

    return ''.join(decoded_parts)


def get_message_text(message):
    """Extract text content from an email message."""
    text_parts = []

    if message.is_multipart():
        # For multipart messages, extract text from each part
        for part in message.walk():
            content_type = part.get_content_type()
            # Get plain text or HTML parts
            if content_type == 'text/plain' or content_type == 'text/html':
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        # Try to decode with the specified charset
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            text_parts.append(payload.decode(charset, errors='replace'))
                        except (LookupError, AttributeError):
                            text_parts.append(payload.decode('utf-8', errors='replace'))
                except Exception:
                    # If decoding fails, try getting payload as string
                    payload = part.get_payload()
                    if isinstance(payload, str):
                        text_parts.append(payload)
    else:
        # For simple messages, get the payload directly
        try:
            payload = message.get_payload(decode=True)
            if payload:
                charset = message.get_content_charset() or 'utf-8'
                try:
                    text_parts.append(payload.decode(charset, errors='replace'))
                except (LookupError, AttributeError):
                    text_parts.append(payload.decode('utf-8', errors='replace'))
        except Exception:
            payload = message.get_payload()
            if isinstance(payload, str):
                text_parts.append(payload)

    return '\n\n---PART---\n\n'.join(text_parts) if text_parts else ''


@click.group()
@click.version_option()
def cli():
    "Load email from .mbox files into SQLite"


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
)
@click.argument(
    "mbox_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False, exists=True),
)
@click.option("--table", default="messages")
@click.option("--simple-tokenizer", type=click.Path(exists=True), help="Path to libsimple.dylib for Chinese tokenization")
def mbox(db_path, mbox_path, table, simple_tokenizer):
    "Import messages from an mbox file"
    db = sqlite_utils.Database(db_path)

    # Load simple tokenizer extension if provided
    if simple_tokenizer:
        db.conn.enable_load_extension(True)
        db.conn.load_extension(simple_tokenizer.replace('.dylib', '').replace('.so', ''))
        db.conn.enable_load_extension(False)

    mbox = mailbox.mbox(mbox_path)

    def to_insert():
        for message in mbox.values():
            row = {}
            # Handle duplicate headers by keeping the last value
            # and normalize header names to lowercase to avoid case conflicts
            for key, value in message.items():
                key_lower = key.lower()
                # Decode MIME-encoded headers (like Subject, From, To, etc.)
                decoded_value = decode_header_value(value)
                if key_lower in row:
                    # Combine multiple values with newlines
                    existing = row[key_lower]
                    row[key_lower] = f"{existing}\n{decoded_value}"
                else:
                    row[key_lower] = decoded_value
            row["payload"] = get_message_text(message)
            yield row

    db[table].upsert_all(to_insert(), alter=True, pk="message-id")

    if not db[table].detect_fts():
        if simple_tokenizer:
            # Use simple tokenizer for Chinese text
            db[table].enable_fts(["payload", "subject"], create_triggers=True, tokenize="simple")
        else:
            # Use default tokenizer
            db[table].enable_fts(["payload", "subject"], create_triggers=True)


@cli.command()
@click.argument("source_db", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.argument("dest_db", type=click.Path(file_okay=True, dir_okay=False))
@click.option(
    "--level",
    type=click.Choice(['minimal', 'standard', 'aggressive'], case_sensitive=False),
    default='standard',
    help="Cleaning level: minimal (HTML→MD), standard (+signatures), aggressive (+quoted replies)"
)
@click.option("--table", default="messages", help="Table name to process")
@click.option("--simple-tokenizer", type=click.Path(exists=True), help="Path to libsimple.dylib for Chinese tokenization")
@click.option("--build-signature-db", is_flag=True, help="Analyze corpus to detect common signatures")
def clean(source_db, dest_db, level, table, simple_tokenizer, build_signature_db):
    """Create a cleaned version of the database optimized for LLM consumption.

    This command reads from SOURCE_DB and creates a new DEST_DB with cleaned email content.
    The cleaned database will have both body_raw (original) and body_clean (optimized) columns.

    Examples:

        # Standard cleaning (recommended)
        mbox-to-sqlite clean emails.db emails-clean.db

        # Aggressive cleaning with Chinese tokenizer
        mbox-to-sqlite clean emails.db emails-clean.db --level aggressive --simple-tokenizer ./libsimple.dylib

        # Build signature database for better cleaning
        mbox-to-sqlite clean emails.db emails-clean.db --build-signature-db
    """
    click.echo(f"🧹 Cleaning database: {source_db} → {dest_db}")
    click.echo(f"📊 Level: {level}")

    # Open source database
    source = sqlite_utils.Database(source_db)

    if table not in source.table_names():
        click.echo(f"❌ Error: Table '{table}' not found in {source_db}", err=True)
        return

    # Count total messages
    total = source[table].count
    click.echo(f"📧 Processing {total:,} emails...")

    # Initialize cleaner
    cleaner = EmailCleaner(level=level)

    # Build signature database if requested
    if build_signature_db:
        click.echo("🔍 Analyzing corpus for common signatures...")
        all_payloads = [row['payload'] for row in source[table].rows if row.get('payload')]
        sig_count = cleaner.build_signature_database(all_payloads, min_occurrences=max(100, total // 100))
        click.echo(f"   Found {sig_count} common signature patterns")

    # Create destination database
    dest = sqlite_utils.Database(dest_db)

    # Process emails with progress bar
    processed = 0
    total_original_bytes = 0
    total_clean_bytes = 0

    with click.progressbar(source[table].rows, length=total, label='Cleaning emails') as rows:
        cleaned_rows = []

        for row in rows:
            payload = row.get('payload', '')

            if payload:
                # Clean the payload
                result = cleaner.clean(payload, message_info=row)

                # Update statistics
                total_original_bytes += result['stats']['original_bytes']
                total_clean_bytes += result['stats']['clean_bytes']

                # Create new row with both raw and clean versions
                cleaned_row = dict(row)
                cleaned_row['body_raw'] = payload
                cleaned_row['body_clean'] = result['body_clean']
                cleaned_row['cleaning_stats'] = json.dumps(result['stats'])

                # Remove old payload column
                if 'payload' in cleaned_row:
                    del cleaned_row['payload']

                cleaned_rows.append(cleaned_row)
            else:
                # No payload, just copy the row
                cleaned_row = dict(row)
                cleaned_row['body_raw'] = ''
                cleaned_row['body_clean'] = ''
                cleaned_row['cleaning_stats'] = json.dumps({
                    'original_bytes': 0,
                    'clean_bytes': 0,
                    'reduction_percent': 0
                })
                if 'payload' in cleaned_row:
                    del cleaned_row['payload']
                cleaned_rows.append(cleaned_row)

            processed += 1

            # Batch insert every 1000 rows for performance
            if len(cleaned_rows) >= 1000:
                dest[table].upsert_all(cleaned_rows, alter=True, pk="message-id")
                cleaned_rows = []

        # Insert remaining rows
        if cleaned_rows:
            dest[table].upsert_all(cleaned_rows, alter=True, pk="message-id")

    # Create FTS index on cleaned content
    click.echo("🔍 Creating full-text search index...")
    if not dest[table].detect_fts():
        if simple_tokenizer:
            # Load simple tokenizer
            dest.conn.enable_load_extension(True)
            dest.conn.load_extension(simple_tokenizer.replace('.dylib', '').replace('.so', ''))
            dest.conn.enable_load_extension(False)
            # Create FTS with simple tokenizer
            dest[table].enable_fts(["body_clean", "subject"], create_triggers=True, tokenize="simple")
            click.echo("   ✓ FTS index created with 'simple' tokenizer (optimized for Chinese)")
        else:
            dest[table].enable_fts(["body_clean", "subject"], create_triggers=True)
            click.echo("   ✓ FTS index created with default tokenizer")

    # Report statistics
    click.echo("\n✨ Cleaning complete!")
    click.echo(f"\n📊 Statistics:")
    click.echo(f"   Emails processed: {processed:,}")
    click.echo(f"   Original size: {total_original_bytes:,} bytes ({total_original_bytes / 1024 / 1024:.2f} MB)")
    click.echo(f"   Cleaned size: {total_clean_bytes:,} bytes ({total_clean_bytes / 1024 / 1024:.2f} MB)")

    if total_original_bytes > 0:
        reduction = ((total_original_bytes - total_clean_bytes) / total_original_bytes * 100)
        click.echo(f"   Token reduction: {reduction:.1f}%")

        # Estimate token savings (rough: 1 token ≈ 2 chars for mixed CJK/English)
        original_tokens = total_original_bytes // 2
        clean_tokens = total_clean_bytes // 2
        saved_tokens = original_tokens - clean_tokens

        click.echo(f"   Estimated tokens saved: {saved_tokens:,} ({original_tokens:,} → {clean_tokens:,})")

    click.echo(f"\n💾 Cleaned database saved to: {dest_db}")
    click.echo(f"\n💡 Tip: Query with `body_clean` for LLM-optimized content:")
    click.echo(f"   SELECT [message-id], subject, body_clean FROM {table} LIMIT 10;")
