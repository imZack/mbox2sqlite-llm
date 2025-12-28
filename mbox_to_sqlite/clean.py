"""
Email payload cleaning for LLM-optimized consumption.

Provides multiple cleaning levels:
- minimal: HTML→Markdown, whitespace normalization
- standard: + signature/footer removal
- aggressive: + quoted replies, attachment metadata
"""

import re
import html2text
import hashlib
from bs4 import BeautifulSoup
from collections import Counter
import json


class EmailCleaner:
    """Clean email payloads for LLM consumption"""

    def __init__(self, level='standard'):
        """
        Initialize cleaner with specified level.

        Args:
            level: 'minimal', 'standard', or 'aggressive'
        """
        self.level = level
        self.html_converter = self._setup_html2text()
        self.signature_db = set()  # Will be populated with common signatures

    def _setup_html2text(self):
        """Configure html2text for optimal Markdown conversion"""
        h = html2text.HTML2Text()
        h.body_width = 0  # CRITICAL for Chinese - no line wrapping!
        h.ignore_images = True  # Replace with placeholders
        h.ignore_links = False  # Preserve links
        h.ignore_emphasis = False  # Keep bold/italic
        h.unicode_snob = True  # Use unicode instead of ASCII
        h.skip_internal_links = True
        return h

    def clean(self, payload, message_info=None):
        """
        Clean an email payload.

        Args:
            payload: Raw email payload (may contain HTML)
            message_info: Optional dict with metadata (for context-aware cleaning)

        Returns:
            dict: {
                'body_clean': cleaned text,
                'stats': {
                    'original_bytes': int,
                    'clean_bytes': int,
                    'reduction_percent': float
                }
            }
        """
        original_bytes = len(payload)

        # Step 1: Extract text from HTML parts (or use plain text)
        text = self._extract_text(payload)

        # Step 2: Minimal cleaning (always applied)
        text = self._minimal_clean(text)

        # Step 3: Standard cleaning (if level >= standard)
        if self.level in ('standard', 'aggressive'):
            text = self._remove_signatures(text)
            text = self._remove_boilerplate(text)

        # Step 4: Aggressive cleaning (if level == aggressive)
        if self.level == 'aggressive':
            text = self._remove_quoted_replies(text)
            text = self._add_attachment_placeholders(text, message_info)

        # Step 5: Final normalization
        text = self._normalize_whitespace(text)

        clean_bytes = len(text)
        reduction = ((original_bytes - clean_bytes) / original_bytes * 100) if original_bytes > 0 else 0

        return {
            'body_clean': text,
            'stats': {
                'original_bytes': original_bytes,
                'clean_bytes': clean_bytes,
                'reduction_percent': round(reduction, 2)
            }
        }

    def _extract_text(self, payload):
        """Extract text from HTML or return plain text"""
        # Check if payload contains HTML
        if '<html' in payload.lower() or '<div' in payload.lower() or '<p>' in payload.lower():
            # Split by ---PART--- separator (from multipart emails)
            parts = payload.split('\n\n---PART---\n\n')

            cleaned_parts = []
            for part in parts:
                part = part.strip()
                if not part:
                    continue

                # If this part is HTML, convert to markdown
                if '<' in part and '>' in part:
                    # Handle inline images before conversion
                    part = self._replace_inline_images(part)
                    try:
                        cleaned = self.html_converter.handle(part)
                        cleaned_parts.append(cleaned)
                    except Exception:
                        # Fallback to BeautifulSoup if html2text fails
                        soup = BeautifulSoup(part, 'html.parser')
                        cleaned_parts.append(soup.get_text(separator='\n', strip=True))
                else:
                    # Plain text part
                    cleaned_parts.append(part)

            return '\n\n'.join(cleaned_parts) if cleaned_parts else payload

        # Already plain text
        return payload

    def _replace_inline_images(self, html):
        """Replace inline images with placeholders"""
        # Replace cid: references
        html = re.sub(
            r'<img[^>]*src=["\']cid:([^"\']+)["\'][^>]*>',
            r'[Inline image: \1]',
            html,
            flags=re.IGNORECASE
        )
        # Replace other image tags
        html = re.sub(
            r'<img[^>]*alt=["\']([^"\']+)["\'][^>]*>',
            r'[Image: \1]',
            html,
            flags=re.IGNORECASE
        )
        return html

    def _minimal_clean(self, text):
        """Minimal cleaning: just normalize obvious issues"""
        # Remove excessive blank lines (but keep paragraph breaks)
        text = re.sub(r'\n{4,}', '\n\n\n', text)

        # Remove common email artifacts
        text = re.sub(r'<mailto:([^>]+)>', r'\1', text)
        text = re.sub(r'<tel:([^>]+)>', r'\1', text)

        return text

    def _remove_signatures(self, text):
        """Remove email signatures using pattern matching"""
        # Common signature delimiters
        signature_markers = [
            r'\n-- \n',  # Standard signature delimiter
            r'\nSent from my iPhone\s*$',
            r'\nSent from my iPad\s*$',
            r'\nGet Outlook for iOS\s*$',
            r'\nGet Outlook for Android\s*$',
        ]

        for marker in signature_markers:
            text = re.sub(marker + r'.*', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove known domain-specific signatures (e.g., contact info)
        # Example pattern for common department signatures
        # Customize this regex for your specific email corpus
        # text = re.sub(
        #     r'\n*Department Name.*?(?:E-mail|email)：?[^\s]+@[^\s]+',
        #     '',
        #     text,
        #     flags=re.DOTALL | re.IGNORECASE
        # )

        return text

    def _remove_boilerplate(self, text):
        """Remove known boilerplate text (CSR policies, disclaimers)"""
        # CSR policy removal - customize this marker for your email corpus
        csr_marker = 'Company CSR Policy:'
        if csr_marker in text:
            start = text.find(csr_marker)
            # Find natural end (usually before next email or end of text)
            # CSR policy is typically 400-500 chars
            end = start + 600

            # Look for section boundaries
            section_ends = ['\n\nFrom:', '\n\n---PART---', '\n\n\n\n']
            for end_marker in section_ends:
                pos = text.find(end_marker, start)
                if start < pos < end:
                    end = pos
                    break

            text = text[:start] + text[end:]

        # Remove duplicate CSR policies (sometimes appears twice)
        # This is handled by the hash-based approach below

        return text

    def _remove_quoted_replies(self, text):
        """Remove quoted replies and forwarded content"""
        try:
            import quotequail
            # quotequail removes quoted text
            unwrapped = quotequail.unwrap(text)
            return unwrapped.strip()
        except Exception:
            # Fallback to simple pattern matching if quotequail fails
            # Remove lines starting with >
            lines = text.split('\n')
            cleaned_lines = [line for line in lines if not line.strip().startswith('>')]

            # Remove "Original Message" blocks
            text = '\n'.join(cleaned_lines)
            text = re.sub(
                r'\n*-+\s*Original Message\s*-+.*?(?=\n\n|\Z)',
                '',
                text,
                flags=re.DOTALL | re.IGNORECASE
            )

            # Remove "Forwarded Message" blocks
            text = re.sub(
                r'\n*-+\s*Forwarded Message\s*-+.*?(?=\n\n|\Z)',
                '',
                text,
                flags=re.DOTALL | re.IGNORECASE
            )

            return text

    def _add_attachment_placeholders(self, text, message_info):
        """Add metadata placeholders for attachments"""
        # This would require message_info to contain attachment metadata
        # For now, just return text as-is
        # In the future, we could add:
        # [Attachment: invoice.pdf, 245KB, application/pdf]
        return text

    def _normalize_whitespace(self, text):
        """Final whitespace normalization"""
        # Collapse multiple spaces to single space (but preserve newlines)
        text = re.sub(r'[ \t]+', ' ', text)

        # Max 2 consecutive newlines (one blank line)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def build_signature_database(self, emails, min_occurrences=100):
        """
        Build a database of common signatures by analyzing email corpus.

        Args:
            emails: List of email payloads
            min_occurrences: Minimum times a signature must appear to be considered common
        """
        footer_hashes = Counter()
        footer_text_map = {}

        for email in emails:
            # Extract last 10 lines as potential signature
            lines = email.split('\n')
            if len(lines) > 10:
                footer = '\n'.join(lines[-10:])
                # Normalize whitespace for hashing
                footer_normalized = re.sub(r'\s+', ' ', footer).strip()

                if len(footer_normalized) > 50:  # Only consider non-trivial footers
                    footer_hash = hashlib.md5(footer_normalized.encode()).hexdigest()
                    footer_hashes[footer_hash] += 1
                    footer_text_map[footer_hash] = footer

        # Store footers that appear frequently (boilerplate)
        self.signature_db = {
            footer_text_map[h]
            for h, count in footer_hashes.items()
            if count >= min_occurrences
        }

        return len(self.signature_db)


def analyze_cleaning_impact(original, cleaned):
    """
    Analyze the impact of cleaning on an email.

    Returns:
        dict with detailed statistics
    """
    return {
        'original_chars': len(original),
        'cleaned_chars': len(cleaned),
        'reduction_chars': len(original) - len(cleaned),
        'reduction_percent': round((len(original) - len(cleaned)) / len(original) * 100, 2) if len(original) > 0 else 0,
        'original_lines': original.count('\n'),
        'cleaned_lines': cleaned.count('\n'),
        # Rough token estimate (1 token ≈ 4 chars for English, ~1.5-2 chars for Chinese)
        'estimated_original_tokens': len(original) // 2,  # Conservative for mixed content
        'estimated_cleaned_tokens': len(cleaned) // 2,
    }
