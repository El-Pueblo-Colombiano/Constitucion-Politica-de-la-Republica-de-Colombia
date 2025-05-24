import requests
from bs4 import BeautifulSoup, Tag, NavigableString
import os
import re
import warnings

# Suppress only the InsecureRequestWarning from urllib3 needed for verify=False
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# --- Configuration ---
URL = "https://sisjur.bogotajuridica.gov.co/sisjur/normas/Norma1.jsp?i=119582"
OUTPUT_DIR_RELATIVE_TO_SCRIPT = "../pot-bogota" 
OUTPUT_FILENAME_IN_DIR = "document_119582_full_text.md" 

# --- Helper Function to Convert HTML Table to Markdown ---
def html_table_to_markdown(table_element):
    markdown_lines = []
    headers = []
    # Try to find headers in <thead> first
    thead = table_element.find('thead')
    if thead:
        header_elements = thead.find_all('th')
        if header_elements:
            headers = [th.get_text(strip=True).replace('\\n', ' ') for th in header_elements]
    
    # If no <thead> or <th> in <thead>, try finding <th> directly in the table (e.g., in first row of <tbody> or just <tr>)
    if not headers:
        header_elements = table_element.find_all('th')
        if header_elements:
             # Check if these th are likely part of a single header row
            parent_names = list(set(th.parent.name for th in header_elements))
            if len(parent_names) == 1 and parent_names[0] == 'tr':
                headers = [th.get_text(strip=True).replace('\\n', ' ') for th in header_elements]

    # Fallback: if no <th> at all, try to use the first row's <td> as headers
    if not headers:
        first_row = table_element.find('tr')
        if first_row:
            potential_headers = first_row.find_all('td')
            if potential_headers: # Ensure it's not an empty row
                # Heuristic: if there's more than one row or this row has content
                if len(table_element.find_all('tr')) > 1 or any(td.get_text(strip=True) for td in potential_headers):
                    headers = [cell.get_text(strip=True).replace('\\n', ' ') for cell in potential_headers]

    if headers:
        markdown_lines.append("| " + " | ".join(headers) + " |")
        markdown_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    # Process rows (try tbody first, then all tr)
    tbody = table_element.find('tbody')
    rows_container = tbody if tbody else table_element
    
    rows = rows_container.find_all('tr')

    for i, row in enumerate(rows):
        # Skip header row if we already processed it
        if headers and i == 0:
            # Check if this row was the source of the headers
            is_header_row = False
            if header_elements: # if th elements were found and used
                if row == header_elements[0].parent: is_header_row = True
            elif first_row and row == first_row: # if first row td elements were used
                is_header_row = True
            
            if is_header_row:
                continue
        
        cells = [td.get_text(strip=True).replace('\\n', ' ').replace('|','\\|') for td in row.find_all(['td', 'th'])] # include th in case of mixed rows
        if cells: # Only add row if it has cells
            markdown_lines.append("| " + " | ".join(cells) + " |")
    
    return "\\n".join(markdown_lines) + "\\n"


# --- Main Scraping Logic ---
def scrape_to_plain_text_and_markdown_tables(url, output_dir, output_filename):
    print(f"Scraping {url} for plain text and Markdown tables...")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created output directory: {output_dir}")
    output_filepath = os.path.join(output_dir, output_filename)

    text_blocks = [] # Store strings (plain text or Markdown tables)

    try:
        headers_req = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=30, verify=False, headers=headers_req)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        main_content_element = None
        center_aligned_tables = soup.find_all('table', align='center')
        for table_candidate in center_aligned_tables:
            td_candidates = table_candidate.find_all('td')
            for td_cand in td_candidates:
                style = td_cand.get('style', '')
                if 'width' in style and any(w in style for w in ['90%', '95%', '96%', '98%', '100%']):
                    main_content_element = td_cand
                    break
            if main_content_element: break
        
        if not main_content_element:
            if center_aligned_tables:
                for t in center_aligned_tables:
                    if len(t.find_all('tr')) > 2 : main_content_element = t; break
                if not main_content_element and center_aligned_tables: main_content_element = center_aligned_tables[0]

        if not main_content_element:
            keyword_pattern_fallback = re.compile(r'(DECRETO|RESOLUCIÓN|ACUERDO|LEY|CONSIDERANDO)\s+\d*', re.IGNORECASE)
            elements_with_keywords = soup.find_all(string=keyword_pattern_fallback)
            if elements_with_keywords:
                parent_container = elements_with_keywords[0]
                for _ in range(5): 
                    if parent_container.parent and parent_container.parent.name not in ['html', 'body','head']:
                        parent_container = parent_container.parent
                        if parent_container.name in ['div', 'td', 'table']: break 
                    else: break
                main_content_element = parent_container
                print(f"Warning: Main content area identified by keyword search fallback: <{main_content_element.name}>.")
            else:
                print("Error: Could not identify a specific main content area. Processing <body>.")
                main_content_element = soup.body
        
        if not main_content_element:
            print("CRITICAL ERROR: No main content element found. Aborting.")
            return

        # Tags to extract text from or process specially (like tables)
        # We want to get text content generally, preserving paragraph breaks.
        # Iterate through all descendants and decide what to do.
        
        processed_element_ids = set() # To avoid processing elements multiple times (e.g. children of a processed table)

        for element in main_content_element.find_all(True): # True gets all tags
            if id(element) in processed_element_ids:
                continue

            if element.name in ['script', 'style', 'meta', 'link', 'head', 'title', 'header', 'footer', 'nav', 'aside', 'form', 'button', 'input', 'select', 'textarea', 'img', 'svg', 'iframe']:
                processed_element_ids.add(id(element))
                for child in element.find_all(True): # Mark children too
                    processed_element_ids.add(id(child))
                continue

            if element.name == 'table':
                md_table = html_table_to_markdown(element)
                text_blocks.append(md_table)
                processed_element_ids.add(id(element))
                for child in element.find_all(True): # Mark children too
                    processed_element_ids.add(id(child))
            elif element.name == 'br':
                 # Add a single newline for <br> if the last block doesn't already end with enough newlines
                if text_blocks and not text_blocks[-1].endswith(("\n\n", "\n")):
                    text_blocks.append("\n") 
            elif element.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'li', 'span', 'font', 'b', 'i', 'u', 'strong', 'em', 'center']:
                # For these tags, extract their text content.
                # We want to avoid extracting text from a container (like a div) if its children (like p)
                # will also be processed and have their text extracted.
                # This is tricky. A simpler approach for "pure text" is to get text from more "leaf-like" nodes.
                
                # Let's get text if the element itself has direct text or is a common inline/simple block.
                # The `get_text` with a separator helps merge text across inline tags.
                # The main goal is to get each "paragraph" or "heading line" as a separate block.
                
                # Check if this element primarily contains other block elements we'd process separately.
                # If so, we skip its aggregate text to avoid duplication.
                contains_other_major_blocks = False
                if element.name == 'div': # Only for divs, p and hX should be fine
                    for child in element.find_all(['p', 'h1', 'h2', 'h3', 'table', 'ul', 'ol'], recursive=False):
                        contains_other_major_blocks = True
                        break
                
                if not contains_other_major_blocks:
                    element_text = element.get_text(separator=' ', strip=True)
                    if element_text: # Only add if there's actual stripped text
                        text_blocks.append(element_text)
                        processed_element_ids.add(id(element))
                        # When we take text from an element, assume its direct children that contributed to this text are covered.
                        # This is a simplification.
                        for child in element.children:
                            if isinstance(child, Tag):
                                processed_element_ids.add(id(child))
            
            # Any other tags are generally ignored for direct text extraction unless they are containers
            # whose children are caught by the above.

        # Join all collected blocks with double newlines for separation
        output_content = ""
        if text_blocks:
            # Filter out any purely empty strings that might have been added
            output_content = "\\n\\n".join(block for block in text_blocks if block.strip())


        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(output_content)
        print(f"Successfully scraped and saved plain text and Markdown tables to: {output_filepath}")
        print(f"The next step will be to run the organizer script on this file: {output_filepath}")


    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during scraping: {e}")
        import traceback
        traceback.print_exc()

# --- Run the Scraper ---
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    absolute_output_dir = os.path.normpath(os.path.join(script_dir, OUTPUT_DIR_RELATIVE_TO_SCRIPT))
    
    scrape_to_plain_text_and_markdown_tables(URL, absolute_output_dir, OUTPUT_FILENAME_IN_DIR)
