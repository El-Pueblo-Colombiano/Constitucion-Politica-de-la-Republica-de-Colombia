import os
import re
import shutil
import requests # For fetching HTML
from bs4 import BeautifulSoup # For parsing HTML
import warnings # Import warnings module

# Suppress only the InsecureRequestWarning from urllib3 needed for verify=False
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# --- Helper Functions ---
def safe_roman_to_int(roman_numeral):
    if not roman_numeral:
        return 0
    roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    int_val = 0
    prev_val = 0
    for char in reversed(roman_numeral.upper()):
        val = roman_map.get(char, 0)
        if val < prev_val:
            int_val -= val
        else:
            int_val += val
        prev_val = val
    return int_val

def format_folder_name(prefix, number_roman, title_text=None):
    if number_roman:
        return f"{prefix}_{number_roman.lower()}"
    elif title_text:
        slug = title_text.lower()
        slug = re.sub(r'[\\/:*?"<>|]', '', slug) 
        slug = re.sub(r'\\s+', '_', slug)          
        slug = re.sub(r'[^\\w\\s_-]', '', slug)    
        slug = re.sub(r'[-\\s]+', '_', slug)      
        slug = slug.strip('_-')                 
        slug = slug[:60]                        
        if slug:
            return f"{prefix}_{slug}"
    return f"{prefix}_misc"


# --- Main Scraping and Processing Logic ---

def fetch_html(url):
    print(f"Fetching HTML from {url}...")
    try:
        response = requests.get(url, timeout=30, verify=False) 
        response.raise_for_status()
        try:
            html_content = response.content.decode('utf-8')
        except UnicodeDecodeError:
            print("UTF-8 decoding failed, trying latin-1...")
            html_content = response.content.decode('latin-1')
        print("HTML fetched successfully.")
        return html_content
    except requests.exceptions.RequestException as e:
        print(f"Error fetching HTML: {e}")
        return None

def extract_content_from_html(html_content):
    articles_data = []
    if not html_content:
        return articles_data

    soup = BeautifulSoup(html_content, 'html.parser')

    print("Extracting CSS from style tags...")
    all_styles_content = []
    style_tags_in_soup = soup.find_all('style')
    for style_tag in style_tags_in_soup:
        if style_tag.string:
            all_styles_content.append(style_tag.string)
    
    if all_styles_content:
        styles_file_path = os.path.join(os.path.dirname(__file__), "extracted_styles.css")
        try:
            with open(styles_file_path, 'w', encoding='utf-8') as f:
                f.write("\\n".join(all_styles_content))
            print(f"CSS content saved to {styles_file_path}")
        except IOError as e:
            print(f"Error saving CSS content: {e}")

    print("Removing style tags from HTML for content parsing...")
    for style_tag in style_tags_in_soup:
        style_tag.decompose()
    print("Style tags removed for parsing.")

    cleaned_html_path = os.path.join(os.path.dirname(__file__), "fetched_page_content_only.html")
    try:
        with open(cleaned_html_path, 'w', encoding='utf-8') as f:
            f.write(str(soup)) 
        print(f"HTML content without styles saved to {cleaned_html_path}")
    except IOError as e:
        print(f"Error saving HTML content without styles: {e}")
    
    main_content_div = soup.find('div', class_='WordSection1')
    if not main_content_div:
        print("Main content div with class 'WordSection1' not found.")
        return articles_data

    current_part_num_roman = None
    current_part_title_text = "Documento Principal" # Default for content before first PARTE
    current_title_num_roman = None
    current_title_title_text = None
    current_chapter_num_roman = None
    current_chapter_title_text = None
    
    current_article_num_str = None
    current_article_title_text = None
    current_article_content_html = []

    expecting_part_desc_title = False
    expecting_title_desc_title = False
    expecting_chapter_desc_title = False

    def finalize_article_if_active():
        nonlocal current_article_num_str, current_article_title_text, current_article_content_html
        nonlocal current_part_num_roman, current_part_title_text
        nonlocal current_title_num_roman, current_title_title_text
        nonlocal current_chapter_num_roman, current_chapter_title_text
        
        if current_article_num_str:
            article_obj = {
                "part_num_roman": current_part_num_roman,
                "part_title_text": current_part_title_text,
                "title_num_roman": current_title_num_roman,
                "title_title_text": current_title_title_text,
                "chapter_num_roman": current_chapter_num_roman,
                "chapter_title_text": current_chapter_title_text,
                "article_num_str": current_article_num_str,
                "article_title_text": current_article_title_text,
                "content_html": "".join(current_article_content_html).strip()
            }
            articles_data.append(article_obj)
        
        current_article_num_str = None # Reset for next article
        current_article_title_text = None
        current_article_content_html = []

    all_paragraphs = main_content_div.find_all('p', recursive=False)
    
    for p_tag in all_paragraphs:
        p_text_stripped = p_tag.get_text(separator=' ', strip=True)
        is_centered_bold = p_tag.get('align') == 'center' and p_tag.find('b')

        # PARTE detection
        if is_centered_bold:
            parte_match = re.search(r"PARTE\s+([IVXLCDM]+)", p_text_stripped, re.IGNORECASE)
            if parte_match:
                finalize_article_if_active()
                current_part_num_roman = parte_match.group(1).upper()
                current_part_title_text = None 
                current_title_num_roman = None
                current_title_title_text = None
                current_chapter_num_roman = None
                current_chapter_title_text = None
                expecting_part_desc_title = True
                expecting_title_desc_title = False
                expecting_chapter_desc_title = False
                continue

        # TÍTULO detection
        if is_centered_bold:
            titulo_match = re.search(r"TÍTULO\s+([IVXLCDM]+)", p_text_stripped, re.IGNORECASE)
            if titulo_match:
                finalize_article_if_active()
                current_title_num_roman = titulo_match.group(1).upper()
                current_title_title_text = None
                current_chapter_num_roman = None
                current_chapter_title_text = None
                expecting_part_desc_title = False
                expecting_title_desc_title = True
                expecting_chapter_desc_title = False
                continue

        # CAPÍTULO detection
        if is_centered_bold:
            capitulo_match = re.search(r"CAPÍTULO\s+([IVXLCDM]+)", p_text_stripped, re.IGNORECASE)
            if capitulo_match:
                finalize_article_if_active()
                current_chapter_num_roman = capitulo_match.group(1).upper()
                current_chapter_title_text = None
                expecting_part_desc_title = False
                expecting_title_desc_title = False
                expecting_chapter_desc_title = True
                continue
        
        # Descriptive title capture
        if is_centered_bold and p_text_stripped and not (len(p_text_stripped) == 0 or all(c.isspace() or c == '\\xa0' for c in p_text_stripped)):
            if expecting_part_desc_title:
                current_part_title_text = p_text_stripped
                expecting_part_desc_title = False
                continue
            elif expecting_title_desc_title:
                current_title_title_text = p_text_stripped
                expecting_title_desc_title = False
                continue
            elif expecting_chapter_desc_title:
                current_chapter_title_text = p_text_stripped
                expecting_chapter_desc_title = False
                continue
        
        # Artículo detection
        span_ancla = p_tag.find('span', class_='ancla', id=re.compile(r'^\d+$'))
        if p_text_stripped.lower().startswith('artículo') and span_ancla:
            finalize_article_if_active()
            current_article_num_str = span_ancla['id']
            
            # Try to extract title from <b> tags within the paragraph
            temp_title = None
            b_tags_in_p = p_tag.find_all('b')
            # Combine text from all <b> tags to reconstruct potential full title header
            full_b_text = " ".join([b.get_text(separator=' ', strip=True) for b in b_tags_in_p])

            # Try to match "N. Title" or "N Title" pattern from combined bold text
            title_pattern_match = re.search(rf"^{current_article_num_str}\s*[\.:]?\s*(.+)", full_b_text, re.IGNORECASE)
            if title_pattern_match:
                temp_title = title_pattern_match.group(1).strip().rstrip('.')
            else: # Fallback if number and title are in separate <b> or mixed with other text
                # Look for "Artículo N." then take subsequent bold text or general text
                article_keyword_match = re.search(r"Artículo\s*(?:[IVXLCDM]+|\d+)\s*[\.:]?", p_text_stripped, re.IGNORECASE)
                if article_keyword_match:
                    text_after_header = p_text_stripped[article_keyword_match.end():].strip()
                    # Take the first sensible part as title, often until a period or significant length
                    first_sentence_match = re.match(r"([^.]+\.)", text_after_header)
                    if first_sentence_match:
                        temp_title = first_sentence_match.group(1).strip().rstrip('.')
                    elif text_after_header: # If no period, take a chunk
                        temp_title = text_after_header.split('\n')[0].strip() # Take first line
                        if len(temp_title) > 150 : # Heuristic: if too long, likely content not title
                            temp_title = temp_title[:150].rsplit(' ',1)[0] + "..."


            current_article_title_text = temp_title if temp_title else f"Artículo {current_article_num_str}"
            
            current_article_content_html.append(str(p_tag))
            # Reset flags as an article header means the section has started
            expecting_part_desc_title = False
            expecting_title_desc_title = False
            expecting_chapter_desc_title = False
            continue

        # If an article is active, append current paragraph to its content
        if current_article_num_str is not None:
            current_article_content_html.append(str(p_tag))
        # If no article active yet, but we have part/title/chapter context, this might be intro text
        # For now, this pre-article text is not explicitly captured separately.

    finalize_article_if_active() # Finalize the very last article
    print(f"Extraction finished. Found {len(articles_data)} articles.")
    return articles_data

def save_articles_to_mdx(articles_data, base_dir="../pot-bogota-scraped"):
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(base_dir, exist_ok=True)
    print(f"Base directory '{base_dir}' prepared.")

    processed_count = 0
    for article in articles_data:
        part_num_r = article.get("part_num_roman")
        part_title_t = article.get("part_title_text") if article.get("part_title_text") else "Parte sin titulo"
        
        title_num_r = article.get("title_num_roman")
        title_title_t = article.get("title_title_text") if article.get("title_title_text") else "Titulo sin titulo"
        
        chapter_num_r = article.get("chapter_num_roman")
        chapter_title_t = article.get("chapter_title_text") if article.get("chapter_title_text") else "Capitulo sin titulo"
        
        article_num_s = article.get("article_num_str")
        article_title_t = article.get("article_title_text", f"Artículo {article_num_s}")
        content_html_str = article.get("content_html", "")

        # Clean HTML content to get plain text
        soup_content = BeautifulSoup(content_html_str, 'html.parser')
        plain_text_content = soup_content.get_text(separator='\n', strip=True)

        if not article_num_s:
            print(f"Skipping entry with missing article number: {article.get('article_title_text', 'Título Desconocido')}")
            continue

        # Create directory structure
        current_path_parts = [base_dir]
        
        # Use "Documento_Principal" if no part_num_r is set yet (e.g. for preamble before PARTE I)
        part_folder_name_str = format_folder_name("parte", part_num_r, part_title_t if part_num_r else "Documento_Principal")
        current_path_parts.append(part_folder_name_str)

        if title_num_r or (title_title_t and title_title_t != "Titulo sin titulo"):
            title_folder_name_str = format_folder_name("titulo", title_num_r, title_title_t)
            current_path_parts.append(title_folder_name_str)

        if chapter_num_r or (chapter_title_t and chapter_title_t != "Capitulo sin titulo"):
            chapter_folder_name_str = format_folder_name("capitulo", chapter_num_r, chapter_title_t)
            current_path_parts.append(chapter_folder_name_str)
        
        current_path = os.path.join(*current_path_parts)
        os.makedirs(current_path, exist_ok=True)

        # Sanitize article_title_text for filename
        safe_article_title_filename_slug = re.sub(r'[-\\s]+', '_', article_title_t.lower())
        safe_article_title_filename_slug = safe_article_title_filename_slug[:80] if safe_article_title_filename_slug else "sin_titulo"

        mdx_file_name = f"articulo_{article_num_s}.mdx"
        mdx_file_path = os.path.join(current_path, mdx_file_name)

        # Create MDX content
        frontmatter = f'''---
title: "Artículo {article_num_s}"
description: "Artículo {article_num_s} del Acuerdo 927"
---

'''
        full_mdx_content = frontmatter + plain_text_content

        try:
            with open(mdx_file_path, "w", encoding="utf-8") as f:
                f.write(full_mdx_content)
            processed_count += 1
        except IOError as e:
            print(f"Error writing MDX file {mdx_file_path}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while writing {mdx_file_path}: {e}")

    print(f"Successfully created {processed_count} MDX files in '{base_dir}'.")


# --- Main Execution ---
if __name__ == "__main__":
    TARGET_URL = "https://sisjur.bogotajuridica.gov.co/sisjur/normas/Norma1.jsp?i=155699"
    
    html_content = fetch_html(TARGET_URL)
    
    if html_content:
        with open("fetched_page.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("Saved fetched HTML to fetched_page.html for inspection.")
            
        extracted_data = extract_content_from_html(html_content)
        
        if extracted_data:
            save_articles_to_mdx(extracted_data)
            print(f"Processing complete. {len(extracted_data)} articles extracted and saved.")
        else:
            print("No articles were extracted. Please check 'fetched_page_content_only.html' for structure issues.")
    else:
        print("Failed to fetch HTML, so no content could be extracted or saved.")