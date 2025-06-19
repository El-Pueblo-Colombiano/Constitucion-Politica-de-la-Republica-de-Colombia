# Article Cleaner for Legal Documents

This program cleans newly created legal articles with three main functions:

1. **Remove "Artículo" lines** - Removes the first line if it starts with 'Artículo' and cleans article numbering
2. **Format Spanish text** - Applies Spanish legal document typography best practices without changing words
3. **Convert numbered lists** - Converts various numbered list formats to markdown format

**IMPORTANT**: This program is designed for legal documents and will NOT modify words, only formatting, spacing, and structure.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Or install loguru directly:

```bash
pip install loguru
```

## Usage

### Basic Usage

```bash
# Process all .mdx files in a directory (dry run by default)
python article_cleaner.py plan_de_desarrollo --dry-run

# Actually process and modify files
python article_cleaner.py plan_de_desarrollo

# Process a single file
python article_cleaner.py --file articulo_1.mdx

# Run with content validation
python article_cleaner.py plan_de_desarrollo --validate
```

### Logging Options

The script now includes comprehensive logging with loguru:

```bash
# Enable verbose debug logging
python article_cleaner.py plan_de_desarrollo --verbose

# Minimize output (only warnings and errors)
python article_cleaner.py plan_de_desarrollo --quiet

# Log to file with automatic rotation
python article_cleaner.py plan_de_desarrollo --log-file cleaner.log

# Combine options
python article_cleaner.py plan_de_desarrollo --validate --verbose --log-file detailed.log
```

### Demo Mode

Use the demo script to see before/after content and validation results:

```bash
python demo_cleaner.py plan_de_desarrollo/articulo_1.mdx
```

The demo script shows:

- Original content
- Cleaned content  
- Line-by-line differences
- Comprehensive validation report
- Content preservation statistics

## Features

### 1. Article Header Cleaning

Removes "Artículo" headers and cleans article numbering:

**Before:**

```
Artículo
1. Política Nacional de Innovación Pública
```

**After:**

```
Política Nacional de Innovación Pública
```

### 2. Spanish Typography Formatting

- **Punctuation spacing**: Proper spacing around commas, periods, semicolons, and colons
- **Special characters**: Converts Unicode characters (smart quotes, em dashes) to ASCII equivalents
- **Parentheses spacing**: Consistent spacing around parentheses
- **Line breaks**: Removes excessive blank lines while preserving paragraph structure
- **Article subsections**: Ensures numbered subsections (like "8.1.", "8.2.", etc.) start on new paragraphs for better readability

**Example subsection formatting:**

```
Before:
Adóptense los siguientes programas del objetivo "Bogotá avanza en seguridad": 8.1. Programa 1. Diálogo social...

After:
Adóptense los siguientes programas del objetivo "Bogotá avanza en seguridad":

8.1.
Programa 1. Diálogo social...
```

### 3. Numbered List Conversion

Converts various list formats to markdown:

**Pattern 1**: Numbered with parentheses

```
tres estrategias: 1) primera estrategia; 2) segunda estrategia, y 3) tercera estrategia.
```

→

```
tres estrategias:

1. primera estrategia
2. segunda estrategia
3. tercera estrategia
```

**Pattern 2**: Lettered lists

```
a. primera opción b. segunda opción c. tercera opción
```

→

```
1. primera opción
2. segunda opción
3. tercera opción
```

### 4. Content Validation

The validation system ensures content integrity:

- **Word preservation**: Tracks that no meaningful words are lost
- **Content statistics**: Provides detailed before/after word counts
- **Validation thresholds**:
  - ≥95% word preservation required
  - ≤5 unique words missing allowed
  - Word count within 10% of original

Example validation output:

```
📊 CONTENT VALIDATION REPORT
============================
Status: ✅ PASSED

📈 KEY METRICS:
  • Word Preservation: 100.0%
  • Word Count Ratio: 100.0%

📊 DETAILED STATISTICS:
  • Original words: 156 total, 98 unique
  • Cleaned words: 156 total, 98 unique
  • Common words: 98
  • Missing words: 0
  • Added words: 0
```

### 5. Advanced Logging

Powered by loguru with features:

- **Colored output**: Different colors for different log levels
- **Timestamps**: Track when operations occur
- **File logging**: Automatic log rotation and compression
- **Debug mode**: Detailed operation tracking
- **Quiet mode**: Minimal output for automated workflows

Example log output:

```
14:23:15 | INFO     | 🧹 Article Cleaner for Legal Documents
14:23:15 | INFO     | Processing: plan_de_desarrollo/articulo_1.mdx
14:23:15 | DEBUG    | Removing 'Artículo' line: 'Artículo'
14:23:15 | DEBUG    | Applied Spanish typography formatting rules
14:23:15 | SUCCESS  | ✓ Changes detected in: plan_de_desarrollo/articulo_1.mdx
14:23:15 | SUCCESS  | ✅ Validation PASSED - 100.0% words preserved
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `directory` | Directory containing .mdx files to process |
| `--file` | Process a single file instead of directory |
| `--dry-run` | Show what would be changed without modifying files |
| `--validate` | Run content validation to ensure words are preserved |
| `--verbose`, `-v` | Enable verbose debug logging |
| `--quiet`, `-q` | Minimize output (only errors and critical info) |
| `--log-file` | Path to log file for detailed logging |

## Safety Features

- **Automatic backups**: Original files saved as `.backup` before modification
- **Dry run mode**: Preview changes before applying them
- **Word preservation**: Validation ensures no content is lost
- **Error handling**: Graceful handling of file errors with detailed logging
- **Fallback mode**: Works even without loguru installed

## File Support

- Processes `.mdx` files (Markdown with JSX)
- Preserves frontmatter (YAML metadata between `---` markers)
- Handles UTF-8 encoding with Spanish characters
- Recursive directory processing

## Examples

### Processing a Directory

```bash
# Preview changes
python article_cleaner.py plan_de_desarrollo --dry-run --verbose

# Process with validation and logging
python article_cleaner.py plan_de_desarrollo --validate --log-file processing.log

# Quiet processing for scripts
python article_cleaner.py plan_de_desarrollo --quiet
```

### Single File Processing

```bash
# Process one file with full validation
python article_cleaner.py --file articulo_1.mdx --validate --verbose
```

### Demo Analysis

```bash
# See detailed before/after comparison
python demo_cleaner.py plan_de_desarrollo/articulo_1.mdx
```

## Dependencies

- **loguru**: Modern logging library with colors and formatting
- **Python 3.6+**: Built-in modules (re, os, glob, argparse)

The program includes a fallback mode that works without loguru, using basic print statements with emoji indicators.
