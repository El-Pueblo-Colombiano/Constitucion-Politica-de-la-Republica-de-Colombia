#!/usr/bin/env python3
"""
Demo script to show before and after content when cleaning an article.
Now includes validation to ensure content preservation.
"""

import sys
import io
import contextlib

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

from article_cleaner import clean_article, validate_content_preservation, print_validation_report


def configure_demo_logging():
    """Configure logging for demo mode with nicer formatting."""
    if not LOGURU_AVAILABLE:
        return
    
    # Remove default handler
    logger.remove()
    
    # Add console handler with demo-friendly format
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="<cyan>{time:HH:mm:ss}</cyan> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
        colorize=True
    )


def demo_cleaning(file_path: str):
    """Show before and after content for a file with validation."""
    configure_demo_logging()
    
    logger.info(f"🧹 DEMO: Article Cleaning Analysis")
    logger.info(f"📄 File: {file_path}")
    logger.info("=" * 60)
    
    try:
        # Read original content
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        logger.info("📖 ORIGINAL CONTENT:")
        print("-" * 50)
        print(original_content)
        print("-" * 50)
        print()
        
        # Get cleaned content without actually writing to file
        # Temporarily capture the print from clean_article
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            cleaned_content = clean_article(file_path)
        
        logger.info("✨ CLEANED CONTENT:")
        print("-" * 50)
        print(cleaned_content)
        print("-" * 50)
        print()
        
        logger.info("🔍 CHANGES ANALYSIS:")
        print("-" * 50)
        if original_content != cleaned_content:
            logger.success("✓ Content would be modified")
            
            # Show specific changes
            original_lines = original_content.split('\n')
            cleaned_lines = cleaned_content.split('\n')
            
            max_lines = max(len(original_lines), len(cleaned_lines))
            
            changes_found = False
            for i in range(max_lines):
                orig_line = original_lines[i] if i < len(original_lines) else ""
                clean_line = cleaned_lines[i] if i < len(cleaned_lines) else ""
                
                if orig_line != clean_line:
                    if not changes_found:
                        logger.info("\n📝 Line-by-line differences:")
                        changes_found = True
                    logger.info(f"Line {i+1}:")
                    logger.info(f"  OLD: {repr(orig_line)}")
                    logger.info(f"  NEW: {repr(clean_line)}")
            
            if not changes_found:
                logger.info("Changes detected but no line-by-line differences (whitespace changes)")
        else:
            logger.info("○ No changes needed")
        
        # Validation report
        logger.info("\n" + "="*60)
        logger.info("🔍 RUNNING CONTENT VALIDATION...")
        logger.info("="*60)
        
        validation_result = validate_content_preservation(original_content, cleaned_content)
        print_validation_report(validation_result)
        
        if validation_result['is_valid']:
            logger.success("🎉 Demo completed successfully - content is well preserved!")
        else:
            logger.warning("⚠️  Demo completed with validation warnings - review needed")
            
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return 1
    except Exception as e:
        logger.error(f"Error during demo: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python demo_cleaner.py <file_path>")
        print("Example: python demo_cleaner.py plan_de_desarrollo/articulo_1.mdx")
        sys.exit(1)
    
    result = demo_cleaning(sys.argv[1])
    sys.exit(result) 