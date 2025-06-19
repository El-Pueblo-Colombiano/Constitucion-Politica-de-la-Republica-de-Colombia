#!/usr/bin/env python3
"""
Debug version to understand what's happening in the cleaner functions.
"""

import re
import sys

def debug_remove_articulo_line(content: str) -> str:
    """Debug version of remove_articulo_line"""
    print("=== DEBUG: remove_articulo_line ===")
    lines = content.split('\n')
    print(f"Total lines: {len(lines)}")
    
    # Skip the frontmatter (between --- markers)
    in_frontmatter = False
    content_start_idx = 0
    
    for i, line in enumerate(lines):
        print(f"Line {i}: {repr(line)}")
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
                print(f"  -> Starting frontmatter at line {i}")
            else:
                in_frontmatter = False
                content_start_idx = i + 1
                print(f"  -> Ending frontmatter at line {i}, content starts at line {content_start_idx}")
                break
    
    # Skip empty lines and find the first non-empty content line
    original_content_start = content_start_idx
    while content_start_idx < len(lines) and not lines[content_start_idx].strip():
        print(f"  -> Skipping empty line {content_start_idx}")
        content_start_idx += 1
    
    if original_content_start != content_start_idx:
        print(f"  -> Moved from line {original_content_start} to {content_start_idx} after skipping empties")
    
    # Check if the first non-empty content line starts with "Artículo"
    if content_start_idx < len(lines):
        first_content_line = lines[content_start_idx].strip()
        print(f"First non-empty content line ({content_start_idx}): {repr(first_content_line)}")
        if first_content_line == 'Artículo' or first_content_line.startswith('Artículo '):
            print(f"  -> REMOVING line {content_start_idx}: {repr(first_content_line)}")
            lines.pop(content_start_idx)
        else:
            print(f"  -> NOT removing line (doesn't match)")
    
    return '\n'.join(lines)

def debug_detect_numbered_lists(text: str):
    """Debug version of detect_numbered_lists"""
    print("\n=== DEBUG: detect_numbered_lists ===")
    
    # Look for the specific pattern we expect
    test_text = "tres estrategias: 1) mejorar la convivencia a través de la confianza ciudadanía-instituciones, cultura ciudadana y prevención de violencias; 2) fortalecer la seguridad y justicia con tecnología, recursos humanos y articulación interinstitucional, y 3) garantizar espacios públicos seguros y en mejores condiciones"
    
    if test_text in text:
        print("✓ Found expected numbered list in text")
        print(f"Sample: {test_text[:100]}...")
    else:
        print("✗ Expected numbered list not found")
    
    # Test the new patterns
    print("\n--- Testing semicolon pattern ---")
    pattern1 = r'(\d+\)\s+[^;]{10,}(?:;\s*\d+\)\s+[^;]{10,})+(?:,?\s*y\s+\d+\)\s+[^;]{10,})?)'
    matches1 = list(re.finditer(pattern1, text))
    print(f"Semicolon pattern matches: {len(matches1)}")
    
    print("\n--- Testing comma pattern ---")
    pattern2 = r'(\d+\)\s+[^,]{10,}(?:,\s*\d+\)\s+[^,]{10,})+(?:,?\s*y\s+\d+\)\s+[^.,]{10,})?)'
    matches2 = list(re.finditer(pattern2, text))
    print(f"Comma pattern matches: {len(matches2)}")
    
    for i, match in enumerate(matches2):
        print(f"Match {i+1}: {repr(match.group(0)[:200])}...")
        print(f"  Position: {match.start()}-{match.end()}")

def debug_clean_article(file_path: str):
    """Debug version of clean_article"""
    print(f"=== DEBUG: Processing {file_path} ===")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"Original content length: {len(content)} characters")
    
    # Step 1: Remove Artículo line
    print("\n--- STEP 1: Remove Artículo line ---")
    content_step1 = debug_remove_articulo_line(content)
    
    # Step 2: Check for numbered lists
    print("\n--- STEP 2: Detect numbered lists ---")
    debug_detect_numbered_lists(content_step1)
    
    return content_step1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_cleaner.py <file_path>")
        sys.exit(1)
    
    debug_clean_article(sys.argv[1]) 