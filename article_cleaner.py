#!/usr/bin/env python3
"""
Article Cleaner for Legal Documents

This program cleans newly created legal articles with the following functions:
1. Remove "Artículo" from first line if present
2. Format Spanish text according to legal document best practices
3. Convert numbered lists to markdown format

IMPORTANT: This program is designed for legal documents and will NOT modify words,
only formatting, spacing, and structure.
"""

import re
import os
import glob
from typing import List, Tuple

# Import loguru for better logging
try:
    from loguru import logger
    LOGURU_AVAILABLE = True
except ImportError:
    # Fallback to print if loguru is not available
    class MockLogger:
        def info(self, msg=""): print(f"ℹ️  {msg}" if msg else "")
        def success(self, msg=""): print(f"✅ {msg}" if msg else "")
        def warning(self, msg=""): print(f"⚠️  {msg}" if msg else "")
        def error(self, msg=""): print(f"❌ {msg}" if msg else "")
        def debug(self, msg=""): print(f"🔍 {msg}" if msg else "")
    
    logger = MockLogger()
    LOGURU_AVAILABLE = False


def configure_logging(log_file: str = None, verbose: bool = False):
    """
    Configure loguru logging with custom format and optional file output.
    
    Args:
        log_file (str): Optional path to log file
        verbose (bool): Enable debug logging
    """
    if not LOGURU_AVAILABLE:
        logger.warning("Loguru not available. Install with: pip install loguru")
        return
    
    # Remove default handler
    logger.remove()
    
    # Add console handler with custom format
    log_level = "DEBUG" if verbose else "INFO"
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    # Add file handler if specified
    if log_file:
        logger.add(
            sink=log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            compression="zip"
        )
        logger.info(f"Logging to file: {log_file}")


def remove_articulo_line(content: str) -> str:
    """
    Remove the first line if it starts with 'Artículo'.
    Also remove the article number and period from the following line if present.
    
    Args:
        content (str): The article content
        
    Returns:
        str: Content with the 'Artículo' line removed and article number cleaned
    """
    lines = content.split('\n')
    
    # Skip the frontmatter (between --- markers)
    in_frontmatter = False
    content_start_idx = 0
    
    for i, line in enumerate(lines):
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
            else:
                in_frontmatter = False
                content_start_idx = i + 1
                break
    
    # Skip empty lines and find the first non-empty content line
    while content_start_idx < len(lines) and not lines[content_start_idx].strip():
        content_start_idx += 1
    
    # Check if the first non-empty content line starts with "Artículo"
    if content_start_idx < len(lines):
        first_content_line = lines[content_start_idx].strip()
        if first_content_line == 'Artículo' or first_content_line.startswith('Artículo '):
            # Remove the "Artículo" line
            logger.debug(f"Removing 'Artículo' line: {repr(first_content_line)}")
            lines.pop(content_start_idx)
            
            # Check if the next line starts with a number and period (like "1. Title")
            if content_start_idx < len(lines):
                next_line = lines[content_start_idx].strip()
                # Pattern to match: number followed by period and space at the beginning
                number_pattern = r'^\d+\.\s+'
                if re.match(number_pattern, next_line):
                    # Remove the number and period, keep the rest
                    cleaned_line = re.sub(number_pattern, '', next_line)
                    lines[content_start_idx] = cleaned_line
                    logger.debug(f"Cleaned article number from line: {repr(next_line)} -> {repr(cleaned_line)}")
    
    return '\n'.join(lines)


def fix_comma_spacing(text: str) -> str:
    """
    Fix spacing around commas according to Spanish typography rules.
    - No space before comma
    - One space after comma
    
    Args:
        text (str): Input text
        
    Returns:
        str: Text with corrected comma spacing
    """
    # Remove spaces before commas
    text = re.sub(r'\s+,', ',', text)
    
    # Ensure one space after comma (but not if followed by another punctuation)
    text = re.sub(r',(?![\s\n.,;:!?)])', ', ', text)
    
    # Fix cases where there's no space after comma
    text = re.sub(r',([^\s\n.,;:!?)])', r', \1', text)
    
    return text


def fix_period_spacing(text: str) -> str:
    """
    Fix spacing around periods according to Spanish typography rules.
    
    Args:
        text (str): Input text
        
    Returns:
        str: Text with corrected period spacing
    """
    # Remove excessive spaces before periods (but be careful with abbreviations)
    # Only remove multiple spaces before periods, not single spaces for abbreviations
    text = re.sub(r'\s{2,}\.', '.', text)
    
    # Ensure proper spacing after periods when followed by letters
    text = re.sub(r'\.([a-záéíóúñüA-ZÁÉÍÓÚÑÜ])', r'. \1', text)
    
    return text


def fix_semicolon_spacing(text: str) -> str:
    """
    Fix spacing around semicolons according to Spanish typography rules.
    
    Args:
        text (str): Input text
        
    Returns:
        str: Text with corrected semicolon spacing
    """
    # Remove spaces before semicolons
    text = re.sub(r'\s+;', ';', text)
    
    # Ensure one space after semicolon
    text = re.sub(r';(?!\s)', '; ', text)
    
    return text


def fix_colon_spacing(text: str) -> str:
    """
    Fix spacing around colons according to Spanish typography rules.
    
    Args:
        text (str): Input text
        
    Returns:
        str: Text with corrected colon spacing
    """
    # Remove spaces before colons
    text = re.sub(r'\s+:', ':', text)
    
    # Ensure one space after colon
    text = re.sub(r':(?!\s)', ': ', text)
    
    return text


def split_long_paragraphs(text: str, max_sentence_length: int = 4) -> str:
    """
    Split excessively long paragraphs into shorter ones while maintaining meaning.
    This follows Spanish legal document best practices.
    
    Args:
        text (str): Input text
        max_sentence_length (int): Maximum number of sentences per paragraph
        
    Returns:
        str: Text with appropriately split paragraphs
    """
    paragraphs = text.split('\n\n')
    result_paragraphs = []
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            result_paragraphs.append(paragraph)
            continue
            
        # Simple sentence splitting: split on '. ' followed by capital letter
        # This is conservative and won't break abbreviations
        sentences = re.split(r'\.\s+([A-ZÁÉÍÓÚÑÜ])', paragraph)
        
        # Reconstruct sentences properly
        actual_sentences = []
        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                # Add period and the capital letter that was captured
                sentence += '. ' + sentences[i + 1]
                if i + 2 < len(sentences):
                    sentence += sentences[i + 2]
                actual_sentences.append(sentence)
                i += 3
            else:
                actual_sentences.append(sentence)
                i += 1
        
        # If paragraph is not too long, keep it as is
        if len(actual_sentences) <= max_sentence_length:
            result_paragraphs.append(paragraph)
        else:
            # Split into smaller paragraphs
            current_paragraph = []
            for i, sentence in enumerate(actual_sentences):
                if sentence.strip():
                    current_paragraph.append(sentence.strip())
                    
                if len(current_paragraph) >= max_sentence_length or i == len(actual_sentences) - 1:
                    if current_paragraph:
                        # Join sentences with proper spacing
                        joined = ' '.join(current_paragraph)
                        result_paragraphs.append(joined)
                        current_paragraph = []
    
    return '\n\n'.join(result_paragraphs)


def normalize_special_characters(text: str) -> str:
    """
    Normalize special Unicode characters to ASCII equivalents.
    This helps with compatibility and removes display issues.
    
    Args:
        text (str): Input text with potential special characters
        
    Returns:
        str: Text with normalized characters
    """
    original_text = text
    
    # Smart quotes to regular quotes
    text = text.replace('\u2018', "'")  # Left single quotation mark
    text = text.replace('\u2019', "'")  # Right single quotation mark  
    text = text.replace('\u201C', '"')  # Left double quotation mark
    text = text.replace('\u201D', '"')  # Right double quotation mark
    text = text.replace('\x93', '"')    # Left double quotation mark (Windows)
    text = text.replace('\x94', '"')    # Right double quotation mark (Windows)
    
    # Em dash and en dash to regular dash
    text = text.replace('\u2014', '--')  # Em dash
    text = text.replace('\u2013', '-')   # En dash
    
    # Other common special characters
    text = text.replace('\u2026', '...')  # Horizontal ellipsis
    text = text.replace('\xa0', ' ')      # Non-breaking space
    
    if text != original_text:
        logger.debug("Normalized special Unicode characters to ASCII equivalents")
    
    return text


def format_article_subsections(content: str) -> str:
    """
    Format numbered article subsections to ensure they start on new paragraphs.
    Handles patterns like "8.1.", "8.2.", "12.1.", etc.
    
    Args:
        content (str): The article content
        
    Returns:
        str: Content with properly formatted subsections
    """
    original_content = content
    logger.debug("Starting article subsection formatting")
    
    # Pattern to match article subsections like "8.1.", "12.3.", etc.
    # This matches: number(s).number(s). followed by text
    subsection_pattern = r'(\d+\.\d+\.)'
    
    # Find all subsection markers
    subsections = re.findall(subsection_pattern, content)
    
    if subsections:
        logger.debug(f"Found {len(subsections)} article subsections: {', '.join(subsections)}")
        
        # Insert paragraph breaks before each subsection marker
        # But not if it's already at the start of a line
        content = re.sub(
            r'(?<!\n\n)(\d+\.\d+\.)',  # Not preceded by double newline
            r'\n\n\1',  # Add double newline before the subsection
            content
        )
        
        # Clean up any triple newlines that might have been created
        content = re.sub(r'\n\n\n+', '\n\n', content)
        
        logger.debug("Applied paragraph breaks before article subsections")
    else:
        logger.debug("No article subsections found to format")
    
    return content


def format_spanish_text(content: str) -> str:
    """
    Apply Spanish legal document formatting best practices.
    This function applies proper typography without changing any words.
    
    Args:
        content (str): The article content
        
    Returns:
        str: Formatted content
    """
    original_content = content
    logger.debug("Starting Spanish text formatting")
    
    # First normalize special characters
    content = normalize_special_characters(content)
    
    # Format article subsections (new function)
    content = format_article_subsections(content)
    
    # Fix spacing around punctuation marks
    content = fix_comma_spacing(content)
    content = fix_period_spacing(content)
    content = fix_semicolon_spacing(content)
    content = fix_colon_spacing(content)
    
    # Remove multiple consecutive spaces (but preserve intentional formatting)
    content = re.sub(r'[ \t]+', ' ', content)
    
    # Fix spacing around parentheses
    content = re.sub(r'\s*\(\s*', ' (', content)
    content = re.sub(r'\s*\)\s*', ') ', content)
    
    # Clean up line breaks - remove excessive blank lines but preserve paragraph structure
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    # Disable paragraph splitting for now as it's causing issues
    # content = split_long_paragraphs(content)
    
    formatted_content = content.strip()
    
    if formatted_content != original_content:
        logger.debug("Applied Spanish typography formatting rules")
    else:
        logger.debug("No formatting changes needed")
    
    return formatted_content


def detect_numbered_lists(text: str) -> List[Tuple[str, int, int]]:
    """
    Detect various patterns of numbered lists in Spanish legal text.
    Be more precise to avoid false positives like (6) in "seis (6) programas".
    
    Args:
        text (str): Input text
        
    Returns:
        List of tuples containing (pattern_type, start_pos, end_pos)
    """
    patterns = []
    
    # Pattern 1: "1) texto, 2) texto, y 3) texto" - must start with colon
    # Simple pattern that requires colon prefix to avoid false positives
    pattern1 = r'(:\s*\d+\)\s+[^;]{10,}(?:;\s*\d+\)\s+[^;]{10,})+(?:,?\s*y\s+\d+\)\s+[^;]{10,})?)'
    for match in re.finditer(pattern1, text):
        patterns.append(('numbered_parentheses', match.start(), match.end()))
    
    # Alternative pattern for comma-separated lists starting after colon
    pattern1_alt = r'(:\s*\d+\)\s+[^,]{10,}(?:,\s*\d+\)\s+[^,]{10,})+(?:,?\s*y\s+\d+\)\s+[^,]{10,})?)'
    for match in re.finditer(pattern1_alt, text):
        patterns.append(('numbered_parentheses_alt', match.start(), match.end()))
    
    # Pattern 2: "a. texto b. texto c. texto" - reduced minimum length
    pattern2 = r'([a-z][\.\)]\s+[^a-z\.]{8,}(?:\s+[a-z][\.\)]\s+[^a-z\.]{8,})+)'
    for match in re.finditer(pattern2, text):
        patterns.append(('lettered_list', match.start(), match.end()))
    
    # Pattern 3: Multiple consecutive numbered items on separate lines
    pattern3 = r'(\d+\.\s+[^\n]{8,}(?:\n\d+\.\s+[^\n]{8,}){1,})'
    for match in re.finditer(pattern3, text):
        patterns.append(('numbered_dots', match.start(), match.end()))
    
    # Pattern 4: Roman numerals with longer content - reduced minimum length
    pattern4 = r'([ivxlc]+\)\s+[^,;.]{8,}(?:,\s*[ivxlc]+\)\s+[^,;.]{8,})+)'
    for match in re.finditer(pattern4, text):
        patterns.append(('roman_numerals', match.start(), match.end()))
    
    return sorted(patterns, key=lambda x: x[1])


def convert_numbered_parentheses_to_markdown(text: str) -> str:
    """Convert "1) texto, 2) texto, y 3) texto" to numbered markdown list format."""
    original_text = text
    
    def replace_match(match):
        content = match.group(0)
        logger.debug(f"Converting numbered parentheses list: {content[:50]}...")
        
        # Remove the leading colon and space if present
        if content.startswith(':'):
            content = content[1:].strip()
        
        # Find where the actual list ends by looking for common end patterns
        # The list should end at the last item before ". Estas" or similar patterns
        end_patterns = [
            r'\.\s+Estas\s+estrategias',  # ". Estas estrategias"
            r'\.\s+Los\s+programas',     # ". Los programas"  
            r'\.\s+La\s+implementación', # ". La implementación"
            r'\.\s+Esta\s+visión',       # ". Esta visión"
        ]
        
        truncated_content = content
        for pattern in end_patterns:
            match_end = re.search(pattern, content)
            if match_end:
                # Include the period but not the following sentence
                truncated_content = content[:match_end.start() + 1]
                break
        
        # Try to split on numbered items with semicolon or comma separators
        parts = re.split(r'((?:;\s*|,\s*)?(?:y\s+)?\d+\))', truncated_content)
        
        markdown_items = []
        current_text = ""
        item_number = 1
        
        for i, part in enumerate(parts):
            # Check if this part is a number marker (with potential separators)
            if re.match(r'(?:;\s*|,\s*)?(?:y\s+)?\d+\)', part):
                # This is a number marker
                if current_text.strip():
                    # Clean up the text and add as numbered item
                    clean_text = current_text.strip().rstrip(',').rstrip(';').strip()
                    if clean_text:
                        markdown_items.append(f"{item_number}. {clean_text}")
                        item_number += 1
                current_text = ""
            else:
                current_text += part
        
        # Add the last item
        if current_text.strip():
            clean_text = current_text.strip().rstrip(',').rstrip(';').strip()
            if clean_text:
                markdown_items.append(f"{item_number}. {clean_text}")
        
        if markdown_items:
            logger.debug(f"Converted to {len(markdown_items)} markdown list items")
            # Find the remaining text after the list
            remaining_text = ""
            for pattern in end_patterns:
                match_end = re.search(pattern, content)
                if match_end:
                    remaining_text = content[match_end.start() + 1:].strip()  # Start after the period
                    break
            
            result = '\n\n' + '\n'.join(markdown_items) + '\n\n'
            if remaining_text:
                result += remaining_text
            return result
        else:
            return content
    
    # Use simple patterns that require colon prefix
    # Pattern for semicolon-separated lists
    pattern1 = r'(:\s*\d+\)\s+[^;]{10,}(?:;\s*\d+\)\s+[^;]{10,})+(?:,?\s*y\s+\d+\)\s+[^;]{10,})?)'
    text = re.sub(pattern1, replace_match, text)
    
    # Pattern for comma-separated lists  
    pattern2 = r'(:\s*\d+\)\s+[^,]{10,}(?:,\s*\d+\)\s+[^,]{10,})+(?:,?\s*y\s+\d+\)\s+[^,]{10,})?)'
    text = re.sub(pattern2, replace_match, text)
    
    if text != original_text:
        logger.debug("Completed numbered parentheses to markdown conversion")
    
    return text


def convert_lettered_lists_to_markdown(text: str) -> str:
    """Convert "a. texto b. texto" or "a) texto b) texto" to numbered markdown format."""
    def replace_match(match):
        content = match.group(0)
        
        # Split by lettered items
        items = re.split(r'([a-z][\.\)])', content)
        
        markdown_items = []
        current_text = ""
        item_number = 1
        
        for i, part in enumerate(items):
            if re.match(r'[a-z][\.\)]', part):
                if current_text.strip():
                    clean_text = current_text.strip().rstrip(',').strip()
                    if clean_text:
                        markdown_items.append(f"{item_number}. {clean_text}")
                        item_number += 1
                    current_text = ""
            else:
                current_text += part
        
        # Add the last item
        if current_text.strip():
            clean_text = current_text.strip().rstrip(',').rstrip('.').strip()
            if clean_text:
                markdown_items.append(f"{item_number}. {clean_text}")
        
        if markdown_items:
            return '\n\n' + '\n'.join(markdown_items) + '\n\n'
        else:
            return content
    
    # More aggressive pattern - reduced minimum length
    pattern = r'([a-z][\.\)]\s+[^a-z\.]{8,}(?:\s+[a-z][\.\)]\s+[^a-z\.]{8,})+)'
    return re.sub(pattern, replace_match, text)


def convert_numbered_dots_to_markdown(text: str) -> str:
    """Convert standalone "1. texto\n2. texto" to proper numbered markdown format."""
    def replace_match(match):
        content = match.group(0)
        lines = content.split('\n')
        
        markdown_items = []
        item_number = 1
        
        for line in lines:
            line = line.strip()
            if re.match(r'\d+\.\s+', line):
                # Remove the original number and dot, add sequential number
                text_content = re.sub(r'^\d+\.\s+', '', line)
                if text_content.strip():
                    markdown_items.append(f"{item_number}. {text_content}")
                    item_number += 1
            elif line:
                markdown_items.append(f"{item_number}. {line}")
                item_number += 1
        
        if markdown_items:
            return '\n\n' + '\n'.join(markdown_items) + '\n\n'
        else:
            return content
    
    # More aggressive pattern - reduced minimum length and fewer required consecutive items
    pattern = r'(\d+\.\s+[^\n]{8,}(?:\n\d+\.\s+[^\n]{8,}){1,})'
    return re.sub(pattern, replace_match, text)


def convert_numbered_lists_to_markdown(content: str) -> str:
    """
    Identify numbered lists and convert them to markdown format.
    
    Args:
        content (str): The article content
        
    Returns:
        str: Content with numbered lists converted to markdown
    """
    # Apply conversions in order (most specific to least specific)
    content = convert_numbered_dots_to_markdown(content)
    content = convert_lettered_lists_to_markdown(content)
    content = convert_numbered_parentheses_to_markdown(content)
    
    return content


def clean_article(file_path: str, validate: bool = False) -> str:
    """
    Clean a single article file by applying all cleaning functions.
    
    Args:
        file_path (str): Path to the article file
        validate (bool): Whether to run validation after cleaning
        
    Returns:
        str: Cleaned article content
    """
    logger.info(f"Processing: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # Apply cleaning functions in order
    content = remove_articulo_line(original_content)
    content = format_spanish_text(content)
    content = convert_numbered_lists_to_markdown(content)
    
    # Run validation if requested
    if validate:
        logger.info(f"🔍 Validating content preservation for {file_path}...")
        validation_result = validate_content_preservation(original_content, content)
        
        if validation_result['is_valid']:
            logger.success(f"Validation PASSED - {validation_result['preservation_percentage']}% words preserved")
        else:
            logger.warning(f"Validation NEEDS REVIEW - {validation_result['preservation_percentage']}% words preserved")
            if validation_result['differences']['missing_words']:
                logger.warning(f"   Missing words: {', '.join(validation_result['differences']['missing_words'][:5])}")
    
    return content


def process_directory(directory_path: str, dry_run: bool = True, validate: bool = False):
    """
    Process all .mdx files in a directory and its subdirectories.
    
    Args:
        directory_path (str): Path to the directory containing articles
        dry_run (bool): If True, only show what would be changed without modifying files
        validate (bool): If True, run content validation on each file
    """
    # Find all .mdx files recursively
    pattern = os.path.join(directory_path, '**', '*.mdx')
    files = glob.glob(pattern, recursive=True)
    
    logger.info(f"Found {len(files)} .mdx files to process")
    
    # Track validation results
    validation_summary = {
        'total_files': 0,
        'passed_validation': 0,
        'failed_validation': 0,
        'avg_preservation': 0.0
    }
    
    for file_path in files:
        try:
            original_content = open(file_path, 'r', encoding='utf-8').read()
            cleaned_content = clean_article(file_path, validate=validate)
            
            if original_content != cleaned_content:
                logger.success(f"✓ Changes detected in: {file_path}")
                
                if not dry_run:
                    # Create backup
                    backup_path = file_path + '.backup'
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(original_content)
                    
                    # Write cleaned content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(cleaned_content)
                    
                    logger.success(f"  ✓ File updated (backup saved as {backup_path})")
                else:
                    logger.info(f"  → Would update this file (dry run mode)")
            else:
                logger.info(f"○ No changes needed: {file_path}")
            
            # Collect validation statistics
            if validate:
                validation_result = validate_content_preservation(original_content, cleaned_content)
                validation_summary['total_files'] += 1
                validation_summary['avg_preservation'] += validation_result['preservation_percentage']
                
                if validation_result['is_valid']:
                    validation_summary['passed_validation'] += 1
                else:
                    validation_summary['failed_validation'] += 1
                
        except Exception as e:
            logger.error(f"✗ Error processing {file_path}: {e}")
    
    # Print validation summary
    if validate and validation_summary['total_files'] > 0:
        avg_preservation = validation_summary['avg_preservation'] / validation_summary['total_files']
        logger.info(f"\n📊 VALIDATION SUMMARY:")
        logger.info(f"  • Files processed: {validation_summary['total_files']}")
        logger.info(f"  • Passed validation: {validation_summary['passed_validation']}")
        logger.info(f"  • Failed validation: {validation_summary['failed_validation']}")
        logger.info(f"  • Average preservation: {avg_preservation:.1f}%")


def main():
    """
    Main function to run the article cleaner.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean legal articles for better formatting')
    parser.add_argument('directory', nargs='?', help='Directory containing article files (required unless --file is used)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be changed without modifying files')
    parser.add_argument('--file', help='Process a single file instead of directory')
    parser.add_argument('--validate', action='store_true',
                       help='Run content validation to ensure words are preserved')
    parser.add_argument('--log-file', help='Path to log file for detailed logging')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose debug logging')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimize output (only errors and critical info)')
    
    args = parser.parse_args()
    
    # Configure logging
    if args.quiet:
        configure_logging(log_file=args.log_file, verbose=False)
        if LOGURU_AVAILABLE:
            logger.remove()
            logger.add(
                sink=lambda msg: print(msg, end=""),
                format="<level>{level: <8}</level> | <level>{message}</level>",
                level="WARNING",
                colorize=True
            )
            if args.log_file:
                logger.add(
                    sink=args.log_file,
                    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
                    level="DEBUG",
                    rotation="10 MB",
                    retention="7 days"
                )
    else:
        configure_logging(log_file=args.log_file, verbose=args.verbose)
    
    # Validate arguments
    if not args.file and not args.directory:
        parser.error('Either directory or --file must be specified')
    
    logger.info("🧹 Article Cleaner for Legal Documents")
    logger.info("=" * 50)
    
    if args.file:
        # Process single file
        try:
            logger.info(f"Processing single file: {args.file}")
            original_content = open(args.file, 'r', encoding='utf-8').read()
            cleaned_content = clean_article(args.file, validate=args.validate)
            
            if not args.dry_run:
                # Create backup
                backup_path = args.file + '.backup'
                
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                with open(args.file, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                
                logger.success(f"File cleaned successfully. Backup saved as {backup_path}")
            else:
                logger.info("Dry run completed - file would be cleaned.")
                
            # Show detailed validation report for single files
            if args.validate:
                validation_result = validate_content_preservation(original_content, cleaned_content)
                print_validation_report(validation_result)
                
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            return 1
    else:
        # Process directory
        try:
            logger.info(f"Processing directory: {args.directory}")
            if args.dry_run:
                logger.info("Running in DRY RUN mode - no files will be modified")
            if args.validate:
                logger.info("Content validation enabled")
                
            process_directory(args.directory, dry_run=args.dry_run, validate=args.validate)
            logger.success("Directory processing completed successfully")
            
        except Exception as e:
            logger.error(f"Error processing directory: {e}")
            return 1
    
    return 0


def validate_content_preservation(original_text: str, cleaned_text: str) -> dict:
    """
    Validate that cleaning preserved all important words and content.
    
    Args:
        original_text (str): Original text before cleaning
        cleaned_text (str): Text after cleaning
        
    Returns:
        dict: Validation results with statistics and differences
    """
    logger.debug("Starting content validation analysis")
    
    def normalize_for_comparison(text: str) -> str:
        """Normalize text for word comparison by removing formatting artifacts."""
        # Remove frontmatter
        lines = text.split('\n')
        content_lines = []
        in_frontmatter = False
        
        for line in lines:
            if line.strip() == '---':
                in_frontmatter = not in_frontmatter
                continue
            if not in_frontmatter:
                content_lines.append(line)
        
        normalized = '\n'.join(content_lines)
        
        # Normalize special characters
        normalized = normalize_special_characters(normalized)
        
        # Remove common artifacts that shouldn't affect word comparison
        normalized = re.sub(r'^\d+\.\s+', '', normalized)  # Remove "1. " prefixes
        normalized = re.sub(r'^Artículo\s*$', '', normalized, flags=re.MULTILINE)  # Remove standalone "Artículo"
        
        return normalized
    
    def extract_words(text: str) -> list:
        """Extract meaningful words from text."""
        # Normalize text
        text = normalize_for_comparison(text)
        
        # Convert to lowercase for comparison
        text = text.lower()
        
        # Remove punctuation but keep letters with accents
        text = re.sub(r'[^\w\sáéíóúñü]', ' ', text)
        
        # Split into words and filter out empty strings and very short words
        words = [word.strip() for word in text.split() if len(word.strip()) > 1]
        
        return words
    
    # Extract words from both texts
    original_words = extract_words(original_text)
    cleaned_words = extract_words(cleaned_text)
    
    logger.debug(f"Extracted {len(original_words)} words from original text")
    logger.debug(f"Extracted {len(cleaned_words)} words from cleaned text")
    
    # Convert to sets for comparison
    original_set = set(original_words)
    cleaned_set = set(cleaned_words)
    
    # Calculate statistics
    total_original = len(original_words)
    total_cleaned = len(cleaned_words)
    unique_original = len(original_set)
    unique_cleaned = len(cleaned_set)
    
    # Find differences
    missing_words = original_set - cleaned_set  # Words in original but not in cleaned
    added_words = cleaned_set - original_set    # Words in cleaned but not in original
    common_words = original_set & cleaned_set   # Words in both
    
    logger.debug(f"Found {len(missing_words)} missing words, {len(added_words)} added words")
    
    # Calculate percentages
    if unique_original > 0:
        preservation_percentage = (len(common_words) / unique_original) * 100
    else:
        preservation_percentage = 100.0
    
    # Calculate word count similarity
    if total_original > 0:
        word_count_ratio = (total_cleaned / total_original) * 100
    else:
        word_count_ratio = 100.0
    
    # Determine validation status
    is_valid = (
        preservation_percentage >= 95.0 and  # At least 95% of words preserved
        len(missing_words) <= 5 and          # No more than 5 unique words missing
        abs(word_count_ratio - 100) <= 10    # Word count within 10% of original
    )
    
    logger.debug(f"Validation result: {'PASSED' if is_valid else 'NEEDS REVIEW'}")
    
    return {
        'is_valid': is_valid,
        'preservation_percentage': round(preservation_percentage, 2),
        'word_count_ratio': round(word_count_ratio, 2),
        'statistics': {
            'original_word_count': total_original,
            'cleaned_word_count': total_cleaned,
            'original_unique_words': unique_original,
            'cleaned_unique_words': unique_cleaned,
            'common_words': len(common_words),
            'missing_words_count': len(missing_words),
            'added_words_count': len(added_words)
        },
        'differences': {
            'missing_words': sorted(list(missing_words))[:10],  # Show first 10
            'added_words': sorted(list(added_words))[:10]       # Show first 10
        }
    }


def print_validation_report(validation_result: dict):
    """
    Print a formatted validation report.
    
    Args:
        validation_result (dict): Result from validate_content_preservation
    """
    logger.info("\n" + "="*60)
    logger.info("📊 CONTENT VALIDATION REPORT")
    logger.info("="*60)
    
    # Overall status
    status = "✅ PASSED" if validation_result['is_valid'] else "⚠️  NEEDS REVIEW"
    logger.info(f"Status: {status}")
    print()  # Empty line
    
    # Key metrics
    logger.info("📈 KEY METRICS:")
    logger.info(f"  • Word Preservation: {validation_result['preservation_percentage']}%")
    logger.info(f"  • Word Count Ratio: {validation_result['word_count_ratio']}%")
    print()  # Empty line
    
    # Detailed statistics
    stats = validation_result['statistics']
    logger.info("📊 DETAILED STATISTICS:")
    logger.info(f"  • Original words: {stats['original_word_count']} total, {stats['original_unique_words']} unique")
    logger.info(f"  • Cleaned words: {stats['cleaned_word_count']} total, {stats['cleaned_unique_words']} unique")
    logger.info(f"  • Common words: {stats['common_words']}")
    logger.info(f"  • Missing words: {stats['missing_words_count']}")
    logger.info(f"  • Added words: {stats['added_words_count']}")
    print()  # Empty line
    
    # Show differences if any
    if validation_result['differences']['missing_words']:
        logger.warning("⚠️  MISSING WORDS (sample):")
        for word in validation_result['differences']['missing_words']:
            logger.warning(f"    - {word}")
        print()  # Empty line
    
    if validation_result['differences']['added_words']:
        logger.info("➕ ADDED WORDS (sample):")
        for word in validation_result['differences']['added_words']:
            logger.info(f"    + {word}")
        print()  # Empty line
    
    # Recommendations
    logger.info("💡 RECOMMENDATIONS:")
    if validation_result['preservation_percentage'] < 95:
        logger.info("  • Review missing words - some content may have been lost")
    if abs(validation_result['word_count_ratio'] - 100) > 10:
        logger.info("  • Significant word count change detected - verify content integrity")
    if validation_result['is_valid']:
        logger.info("  • Cleaning appears successful - content is well preserved")
    
    logger.info("="*60)


if __name__ == "__main__":
    main() 