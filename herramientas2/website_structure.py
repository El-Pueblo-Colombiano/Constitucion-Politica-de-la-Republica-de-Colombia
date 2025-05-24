import requests
from bs4 import BeautifulSoup
from collections import Counter
import warnings # To suppress the InsecureRequestWarning

# Suppress only the InsecureRequestWarning from urllib3 needed for verify=False
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings('ignore', category=InsecureRequestWarning)


URL_TO_ANALYZE = "https://sisjur.bogotajuridica.gov.co/sisjur/normas/Norma1.jsp?i=119582"

def analyze_html_structure(url):
    print(f"Analyzing HTML structure for: {url}\\n")
    try:
        # Added verify=False to bypass SSL certificate verification
        # Also added a User-Agent header, as some sites require it
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=10, verify=False, headers=headers)
        response.raise_for_status() # Check for HTTP errors like 404 or 500
        soup = BeautifulSoup(response.content, 'html.parser')

        print("\\n--- Document Title ---")
        print(soup.title.string if soup.title else "No title found")

        print("\\n--- First 500 characters of Prettified HTML Body (for a glimpse) ---")
        if soup.body:
            print(soup.body.prettify()[:500] + "...")
        else:
            print("No body tag found.")

        print("\\n--- All Unique Tag Names ---")
        all_tags = [tag.name for tag in soup.find_all(True)]
        tag_counts = Counter(all_tags)
        print(tag_counts)

        print("\\n--- All DIV elements with ID or Class (first 20) ---")
        divs = soup.find_all('div', limit=20)
        if divs:
            for i, div in enumerate(divs):
                div_id = div.get('id', 'N/A')
                div_class = div.get('class', 'N/A')
                print(f"  Div {i+1}: ID='{div_id}', Class='{div_class}'")
        else:
            print("No DIV elements found.")
            
        print("\\n--- All FONT elements with attributes (first 20) ---")
        fonts = soup.find_all('font', limit=20)
        if fonts:
            for i, font_tag in enumerate(fonts):
                attributes = font_tag.attrs
                print(f"  Font {i+1}: Attributes='{attributes}'")
                # print(f"    Text (first 50 chars): '{font_tag.get_text(strip=True)[:50]}...'")
        else:
            print("No FONT elements found.")

        print("\\n--- All P elements with attributes (first 20) ---")
        paragraphs = soup.find_all('p', limit=20)
        if paragraphs:
            for i, p_tag in enumerate(paragraphs):
                attributes = p_tag.attrs
                print(f"  Paragraph {i+1}: Attributes='{attributes}'")
                # print(f"    Text (first 50 chars): '{p_tag.get_text(strip=True)[:50]}...'")
        else:
            print("No P elements found.")


        print("\\n--- Heading Tags (H1-H6) ---")
        for i in range(1, 7):
            heading_tag = f'h{i}'
            headings = soup.find_all(heading_tag)
            if headings:
                print(f"  Found {len(headings)} <{heading_tag}> tags:")
                for j, h in enumerate(headings[:5]): # Print first 5
                    print(f"    {j+1}. Text: {h.get_text(strip=True)[:100]}") # Print up to 100 chars
            # else:
            #     print(f"  No <{heading_tag}> tags found.")

        print("\\n--- Table Elements (summary of first 5) ---")
        tables = soup.find_all('table')
        if tables:
            print(f"Found {len(tables)} <table> elements.")
            for i, table in enumerate(tables[:5]):
                print(f"  Table {i+1}:")
                print(f"    Attributes: {table.attrs}")
                print(f"    First 100 chars of table HTML: {str(table)[:100]}...")
        else:
            print("No <table> elements found.")

        print("\\n--- Elements containing the text 'Artículo' or 'ARTICULO' (case-insensitive, first 10 matches) ---")
        import re
        # Updated regex to be more specific to "ARTICULO" potentially followed by a number or "Parágrafo"
        article_text_pattern = re.compile(r'(ART[IÍ]CULO|CAPITULO|PARÁGRAFO|TITULO|LIBRO|DECRETA|RESUELVE|CONSIDERANDO)[\s\.:]', re.IGNORECASE)
        
        # Find all text nodes matching the pattern
        text_nodes = soup.find_all(string=article_text_pattern)
        
        count = 0
        if text_nodes:
            print(f"Found {len(text_nodes)} potential article/section related text nodes. Showing details for up to 10:")
            for text_node in text_nodes:
                if count >= 10:
                    break
                parent = text_node.parent
                # Try to avoid overly generic parents like 'body' or 'html' unless that's all there is
                if parent and parent.name not in ['body', 'html']:
                    # Let's look for a slightly more meaningful ancestor if the direct parent is just a formatting tag like <b> or <font>
                    ancestor_to_log = parent
                    if parent.name in ['b', 'strong', 'font', 'span', 'i', 'u'] and parent.parent and parent.parent.name not in ['body', 'html']:
                        ancestor_to_log = parent.parent

                    print(f"  Match {count+1}: Found in <{ancestor_to_log.name}> tag. Attributes: {ancestor_to_log.attrs}")
                    print(f"    Ancestor's text (first 70 chars): '{ancestor_to_log.get_text(strip=True)[:70]}...'")
                    print(f"    Text node itself (first 70 chars): '{text_node.strip()[:70]}...'")
                    count += 1
        else:
            print("No elements containing typical article/section keywords found in text nodes with the refined pattern.")
            
        print("\\n--- Attempting to find main content area heuristics ---")
        content_selectors = [
            {'id': 'contenido'}, {'id': 'main'}, {'id': 'main-content'}, {'id': 'content'},
            {'class_': 'content'}, {'class_': 'main-content'}, {'class_': 'post-content'}, # Note: class_ for BeautifulSoup
            {'tag': 'article'}, {'tag': 'main'}
        ]
        found_potential_content = False
        for selector_info in content_selectors:
            elements = []
            if 'tag' in selector_info:
                 elements = soup.find_all(selector_info['tag'])
            elif 'id' in selector_info:
                elements = soup.find_all(id=selector_info['id']) # id is a direct argument
            elif 'class_' in selector_info: # class_ is used for 'class' attribute
                elements = soup.find_all(class_=selector_info['class_'])
            
            if elements:
                found_potential_content = True
                for i, el in enumerate(elements):
                    print(f"  Potential content area found with selector {selector_info}: <{el.name}> id='{el.get('id', '')}' class='{el.get('class', '')}'")
                    break 
        if not found_potential_content:
            print("  No common content area selectors found. Manual inspection is key.")


    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during analysis: {e}")

if __name__ == "__main__":
    analyze_html_structure(URL_TO_ANALYZE)
    print("\\nAnalysis complete. Please review the output to identify key HTML structures.")
    print("Key things to look for for the scraper:")
    print("1. A main container DIV/tag that holds all relevant text and tables.")
    print("2. How articles ('Artículo X') are structured (e.g., in their own DIVs, preceded by H2/H3 tags, or within specific FONT tags).")
    print("3. The structure of TABLE tags.")
