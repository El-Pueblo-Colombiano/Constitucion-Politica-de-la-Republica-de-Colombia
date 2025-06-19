import requests
from bs4 import BeautifulSoup
import re
from loguru import logger
import os
import urllib3
import json
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_pot_bogota():
    """
    Scrapes the POT Bogota legal document from the specified URL and saves articles to files.
    Uses only element-based extraction, in a single pass, ensuring all trailing content is included in the last article.
    """
    url = "https://sisjur.bogotajuridica.gov.co/sisjur/normas/Norma1.jsp?i=119582"
    
    try:
        # Make request to the site
        response = requests.get(url, verify=False)
        response.raise_for_status()
        
        # Save raw HTML to file before parsing
        raw_data_dir = os.path.join(os.path.dirname(__file__), 'raw-data')
        os.makedirs(raw_data_dir, exist_ok=True)
        raw_html_path = os.path.join(raw_data_dir, 'pot_bogota_raw.html')
        with open(raw_html_path, 'w', encoding='utf-8') as raw_file:
            raw_file.write(response.text)
        logger.info(f"Saved raw HTML to {raw_html_path}")
        
        # Clean the HTML: keep only the <body> tag or main content div
        soup = BeautifulSoup(response.text, 'html.parser')
        main_content = None
        # Prefer the main content div if it exists
        main_content = soup.find('div', {'WordSection1': True})
        if not main_content:
            # Fallback: use the <body> tag
            main_content = soup.body
        if not main_content:
            logger.error("Could not find main content section or <body> in HTML")
            return
        # Remove all <script> and <style> tags from the main content
        for tag in main_content.find_all(['script', 'style']):
            tag.decompose()
        # Remove non-standard/plain HTML tags
        non_standard_tags = [
            'font', 'span', 'center', 'u', 'b', 'i', 'em', 'strong', 'small', 'big', 'mark', 's', 'strike', 'tt',
            'abbr', 'acronym', 'sub', 'sup', 'ins', 'del', 'dfn', 'var', 'samp', 'kbd', 'code', 'pre', 'blockquote',
            'q', 'cite', 'address', 'canvas', 'svg', 'object', 'embed', 'applet', 'basefont', 'bdo', 'bdi', 'data',
            'datalist', 'output', 'progress', 'meter', 'ruby', 'rt', 'rp', 'wbr', 'details', 'summary', 'menu',
            'menuitem', 'dialog', 'marquee', 'blink', 'noframes', 'frame', 'frameset', 'isindex', 'listing', 'plaintext', 'xmp'
        ]
        for tag in main_content.find_all(non_standard_tags):
            tag.unwrap()
        cleaned_html = str(main_content)
        cleaned_html_path = os.path.join(raw_data_dir, 'pot_bogota_raw_clean.html')
        with open(cleaned_html_path, 'w', encoding='utf-8') as clean_file:
            clean_file.write(cleaned_html)
        logger.info(f"Saved cleaned HTML to {cleaned_html_path}")
        
        # Parse cleaned HTML for element-based extraction
        soup = BeautifulSoup(cleaned_html, 'html.parser')
        # If we used <body>, try to find the main content div again
        content = soup.find('div', {'WordSection1': True}) or soup
        articles = content.find_all(['p', 'div'])
        output_dir = "pot_articles"
        os.makedirs(output_dir, exist_ok=True)
        logger.info("Processing all articles (element-based, single pass)...")
        extract_articles_from_elements(articles, output_dir)
        logger.success("Element-based extraction completed!")
        report_missing_articles(output_dir, 608)
    except requests.RequestException as e:
        logger.error(f"Error fetching URL: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

def extract_articles_from_elements(article_elements, output_dir, suffix=''):
    import re
    current_article = []
    article_number = None
    found_any_article = False
    last_detected_number = None
    for idx, element in enumerate(article_elements):
        text = element.get_text().strip()
        if not text:
            continue  # Skip empty elements
        # Preprocess: collapse all whitespace between 'Artículo' and the number
        text_for_match = re.sub(r'(Artículo)[\s\xa0]*([0-9]+)', r'Artículo \2', text, flags=re.IGNORECASE)
        article_match = re.match(r'Artículo\s*(\d+)\.?', text_for_match, re.IGNORECASE)
        if article_match:
            if current_article and article_number:
                save_article(f"{article_number}{suffix}", current_article, output_dir)
            article_number = article_match.group(1)
            current_article = [text]
            found_any_article = True
            last_detected_number = article_number
        elif article_number:
            current_article.append(text)
    # After the loop, if the last detected article is 607, keep appending all remaining elements to 607 until 608 is found, then to 608
    if last_detected_number == '607' or last_detected_number == '608':
        # Find the index where 607 started
        idx_607 = None
        for idx, element in enumerate(article_elements):
            text = element.get_text().strip()
            text_for_match = re.sub(r'(Artículo)[\s\xa0]*([0-9]+)', r'Artículo \2', text, flags=re.IGNORECASE)
            article_match = re.match(r'Artículo\s*607\.?', text_for_match, re.IGNORECASE)
            if article_match:
                idx_607 = idx
                break
        if idx_607 is not None:
            # Re-group all content after 607
            article_607 = []
            article_608 = []
            in_607 = False
            in_608 = False
            for element in article_elements[idx_607:]:
                text = element.get_text().strip()
                if not text:
                    continue
                text_for_match = re.sub(r'(Artículo)[\s\xa0]*([0-9]+)', r'Artículo \2', text, flags=re.IGNORECASE)
                match_607 = re.match(r'Artículo\s*607\.?', text_for_match, re.IGNORECASE)
                match_608 = re.match(r'Artículo\s*608\.?', text_for_match, re.IGNORECASE)
                if match_607:
                    in_607 = True
                    in_608 = False
                    article_607 = [text]
                    continue
                if match_608:
                    in_607 = False
                    in_608 = True
                    article_608 = [text]
                    continue
                if in_607:
                    article_607.append(text)
                elif in_608:
                    article_608.append(text)
            # Save both articles
            if article_607:
                save_article('607', article_607, output_dir)
            if article_608:
                save_article('608', article_608, output_dir)
    # Save last article (ensure all trailing content is included)
    if current_article and article_number and any(line.strip() for line in current_article):
        save_article(f"{article_number}{suffix}", current_article, output_dir)
    if not found_any_article:
        logger.error(f"No articles found in element-based extraction. Check the HTML structure or regex.")

def save_article(number, content, output_dir):
    """
    Saves an article to a file (always overwrites).
    """
    filename = os.path.join(output_dir, f"articulo_{number}.mdx")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(content))
    logger.info(f"Saved article {number}")

def save_articles_chunk(articles, output_dir):
    """
    Saves a chunk of articles and logs progress.
    """
    for number, content in articles:
        save_article(number, content, output_dir)
    logger.info(f"Saved a chunk of {len(articles)} articles.")

def report_missing_articles(output_dir, expected_count):
    """
    Reports missing article numbers in the output directory.
    """
    found_numbers = set()
    for filename in os.listdir(output_dir):
        match = re.match(r"articulo_(\d+)\.mdx", filename)
        if match:
            found_numbers.add(int(match.group(1)))
    missing = [str(i) for i in range(1, expected_count + 1) if i not in found_numbers]
    if missing:
        logger.warning(f"Missing articles: {', '.join(missing)}")
    else:
        logger.success("All articles are present!")

def process_article_elements(article_elements, output_dir, chunk_label=None):
    current_article = []
    article_number = None
    found_any_article = False
    articles_to_save = []
    for element in article_elements:
        text = element.get_text().strip()
        if not text:
            continue  # Skip empty elements
        article_match = re.match(r'Artículo\s+(\d+)\.?', text, re.IGNORECASE)
        if article_match:
            if current_article and article_number:
                articles_to_save.append((article_number, list(current_article)))
            article_number = article_match.group(1)
            current_article = [text]
            found_any_article = True
        elif article_number:
            current_article.append(text)
    if current_article and article_number and any(line.strip() for line in current_article):
        articles_to_save.append((article_number, list(current_article)))
    if articles_to_save:
        save_articles_chunk(articles_to_save, output_dir)
        logger.info(f"Saved {len(articles_to_save)} articles for chunk {chunk_label}.")
    elif not found_any_article:
        logger.error(f"No articles found in chunk {chunk_label}. Check the HTML structure or regex.")

def extract_plain_text_from_html(cleaned_html_path, plain_text_path):
    with open(cleaned_html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    plain_text = soup.get_text(separator='\n', strip=True)
    with open(plain_text_path, 'w', encoding='utf-8') as f:
        f.write(plain_text)
    return plain_text_path

def evaluate_article_taxonomy_from_text(plain_text_path):
    import re
    import os
    import unicodedata
    hierarchy_keywords = [
        'LIBRO', 'TÍTULO', 'CAPÍTULO', 'SUBCAPÍTULO', 'SECCIÓN', 'SUBSECCIÓN'
    ]
    hierarchy_levels = {k: i for i, k in enumerate(hierarchy_keywords)}
    # Allow for optional prefixes (e.g., 'a. ', '1. ', etc.) before the hierarchy keyword
    hierarchy_regex = {k: re.compile(rf'^([a-zA-Z0-9\.\s\-]*)({k})\b(.*)', re.IGNORECASE) for k in hierarchy_keywords}
    # Updated article regex: only match at the start of a line, with optional whitespace or prefix, and 'Artículo' (with or without accent)
    article_regex = re.compile(r'^\s*(art[ií]culo)[\s\xa0]+(\d+)\.?', re.IGNORECASE)
    with open(plain_text_path, 'r', encoding='utf-8') as f:
        lines = [re.sub(r'\s+', ' ', line.strip()) for line in f if line.strip()]

    def normalize_key(text):
        # Remove accents, lowercase, replace spaces/dots with underscores, keep only first identifier, ignore prefix
        text = text.strip()
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        text = text.lower()
        # Extract keyword and first identifier (e.g., 'LIBRO II' -> 'libro_ii'), ignoring any prefix
        m = re.match(r'(?:[a-z0-9\.\s\-]*)(libro|titulo|capitulo|subcapitulo|seccion|subseccion)[\s\.:_-]*([a-z0-9ivxunico]+)?', text)
        if m:
            keyword = m.group(1)
            ident = m.group(2) or 'unico'
            return f"{keyword}_{ident}"
        return text.replace(' ', '_').replace('.', '_')

    root = {}
    stack = [(root, -1)]  # (current_dict, level)
    last_article_number = 0
    i = 0
    while i < len(lines):
        text = lines[i]
        found_hierarchy = False
        for k in hierarchy_keywords:
            m = hierarchy_regex[k].match(text)
            # Accept if the keyword is present and in uppercase, regardless of the rest of the line
            if m and m.group(2).upper() == k:
                node_name = text.strip()
                # Look ahead for a possible all-caps label (if next line is all caps and not a hierarchy keyword)
                label = None
                j = i + 1
                while j < len(lines):
                    next_text = lines[j]
                    if not next_text:
                        j += 1
                        continue
                    if article_regex.match(next_text):
                        break
                    if any(hierarchy_regex[kk].match(next_text) for kk in hierarchy_keywords):
                        break
                    if next_text.isupper():
                        label = next_text
                        i = j  # Skip this label in the main loop
                    break
                if label:
                    node_name = f"{node_name}: {label}"
                # Normalize key
                key = normalize_key(node_name)
                level = hierarchy_levels[k]
                # Pop stack to the correct parent level (not just >=, but >)
                while stack and stack[-1][1] >= level:
                    stack.pop()
                parent_dict = stack[-1][0]
                if key not in parent_dict:
                    parent_dict[key] = {}
                # Always update the stack to reflect the current path in the hierarchy
                stack = stack[:level+1] + [(parent_dict[key], level)]
                found_hierarchy = True
                break
        # Check for article
        a = article_regex.match(text)
        if a:
            art_num = int(a.group(2))
            art_key = f"articulo_{art_num}"
            # Strict check: article numbers must be strictly ascending
            if art_num != last_article_number + 1:
                print(f"WARNING: Non-sequential article number {art_num} after {last_article_number} at line {i+1}. This may indicate a structural issue.")
            last_article_number = art_num
            # Attach to the most recent parent node in the stack that is not root
            for d, lvl in reversed(stack):
                if lvl >= 0 and isinstance(d, dict):
                    if 'articulos' not in d:
                        d['articulos'] = []
                    d['articulos'].append(art_key)
                    break
        i += 1
    # Save compact JSON
    taxonomy_json_path = os.path.join(os.path.dirname(plain_text_path), 'taxonomy_tree_compact.json')
    with open(taxonomy_json_path, 'w', encoding='utf-8') as f:
        json.dump(root, f, ensure_ascii=False, indent=2)
    print(f"Taxonomy compact tree written to {taxonomy_json_path}\n")

if __name__ == "__main__":
    scrape_pot_bogota()
    # Extract plain text and evaluate taxonomy from it
    cleaned_html_path = os.path.join(os.path.dirname(__file__), 'raw-data', 'pot_bogota_raw_clean.html')
    plain_text_path = os.path.join(os.path.dirname(__file__), 'raw-data', 'pot_bogota_raw_clean.txt')
    extract_plain_text_from_html(cleaned_html_path, plain_text_path)
    print("\n--- Article Taxonomy Evaluation (from plain text) ---\n")
    evaluate_article_taxonomy_from_text(plain_text_path)
