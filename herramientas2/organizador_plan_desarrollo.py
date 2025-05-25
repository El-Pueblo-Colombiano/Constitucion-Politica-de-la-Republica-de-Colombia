import docx # python-docx library
import re
import os
import unicodedata
import shutil
from docx.document import Document as DocxDocumentObject # Renamed to avoid conflict
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

def slugify(value, allow_unicode=False, max_length=None): # Added max_length
    """
    Convert to lowercase, remove non-alphanumeric characters (except underscores and hyphens),
    and convert spaces to underscores. Optionally truncate to max_length.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    value = re.sub(r'[-\s]+', '_', value).strip('_')
    if max_length and len(value) > max_length: # Truncate if max_length is specified and current length exceeds
        value = value[:max_length]
    return value

def roman_to_int_simple(s):
    """Converts Roman numeral to lowercase for folder names."""
    if not s: return "" # Handle None or empty string
    return s.lower()

def iter_block_items(parent):
    """
    Yield each paragraph and table child within *parent*, in document order.
    Each returned value is an instance of either Paragraph or Table.
    Helper for extract_text_and_tables_from_docx.
    """
    if isinstance(parent, DocxDocumentObject): # Use the renamed import
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("Parent must be a Document or _Cell object")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

def extract_text_and_tables_from_docx(docx_path):
    """
    Extracts text from paragraphs and converts tables to Markdown format
    from a DOCX file.
    """
    doc = docx.Document(docx_path)
    full_content_parts = []
    for block in iter_block_items(doc): # Use the helper to iterate through paragraphs and tables
        if isinstance(block, Paragraph):
            full_content_parts.append(block.text) # Append paragraph text
        elif isinstance(block, Table):
            table_md = "\n" # Start table Markdown with a newline for separation
            if not block.rows: # Handle empty tables
                full_content_parts.append(table_md + "| Tabla vacía |\n| --- |\n\n")
                continue

            try:
                # Headers: Use text from the first row, replace internal newlines with <br>
                header_cells_text = [cell.text.strip().replace("\n", " <br> ") for cell in block.rows[0].cells]
                num_cols_header = len(header_cells_text)

                if not any(header_cells_text): # If first row is effectively empty, treat as no header
                    # Try to determine column count from a row with max cells if possible, or first data row
                    max_cols_in_table = 0
                    if len(block.rows) > 1:
                        for r_idx in range(len(block.rows)):
                            max_cols_in_table = max(max_cols_in_table, len(block.rows[r_idx].cells))
                    num_cols = max_cols_in_table if max_cols_in_table > 0 else (len(block.columns) if block.columns else 1)
                    
                    table_md += "| " + " | ".join([f"Columna {j+1}" for j in range(num_cols)]) + " |\n"
                    table_md += "| " + " | ".join(["---"] * num_cols) + " |\n"
                    start_row_index = 0 # Process all rows as data
                else:
                    table_md += "| " + " | ".join(header_cells_text) + " |\n"
                    table_md += "| " + " | ".join(["---"] * num_cols_header) + " |\n"
                    start_row_index = 1 # Data rows start from the second row
                    num_cols = num_cols_header


                # Data Rows
                for i in range(start_row_index, len(block.rows)):
                    row = block.rows[i]
                    row_cells_text = [cell.text.strip().replace("\n", " <br> ") for cell in row.cells]
                    
                    # Ensure row has same number of columns as header for valid Markdown
                    # If header was empty, use num_cols determined earlier
                    expected_cols = num_cols
                    
                    while len(row_cells_text) < expected_cols:
                        row_cells_text.append("") # Pad with empty strings
                    if len(row_cells_text) > expected_cols:
                        row_cells_text = row_cells_text[:expected_cols] # Truncate

                    table_md += "| " + " | ".join(row_cells_text) + " |\n"
                full_content_parts.append(table_md + "\n") # End table Markdown with a newline
            except IndexError:
                full_content_parts.append("\n| Error al procesar tabla: Estructura de fila/columna inesperada. |\n| --- |\n\n")
            except Exception as e:
                full_content_parts.append(f"\n| Error al procesar tabla: {e} |\n| --- |\n\n")


    return "\n".join(full_content_parts) # Join all parts with a single newline


def parse_and_create_mdx(docx_path, base_output_dir, document_name_for_description):
    """
    Parses the DOCX and creates the MDX directory structure and files.
    """
    print(f"Starting processing for DOCX: {docx_path}")

    if os.path.exists(base_output_dir):
        shutil.rmtree(base_output_dir) 
    os.makedirs(base_output_dir, exist_ok=True)
    print(f"Created base output directory: {base_output_dir}")

    full_text_with_tables = extract_text_and_tables_from_docx(docx_path) # Use new extraction function

    # Use "ACUERDA:" as the starting marker for this document
    acuerda_content_match = re.search(r"ACUERDA[:\s]*\n(.*)", full_text_with_tables, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if not acuerda_content_match:
        print("Warning: Could not find 'ACUERDA:' marker. Processing entire document.")
        content_to_process = full_text_with_tables
    else:
        content_to_process = acuerda_content_match.group(1)
        print("Found 'ACUERDA:', processing content thereafter.")

    # Regex patterns for "PARTE", "TÍTULO", "ARTÍCULO"
    parte_marker_regex = re.compile(r"^\s*PARTE\s+([IVXLCDM]+)\s*$", re.MULTILINE | re.IGNORECASE)
    titulo_marker_regex = re.compile(r"^\s*TÍTULO\s+([IVXLCDM\d]+)\s*$", re.MULTILINE | re.IGNORECASE) # Titulo can be Roman or Arabic
    articulo_start_pattern = re.compile(
        r"^(Artículo|Articulo)\s+(\d+[A-Z]?(\-[A-Z\d]+)?)\.(?:\s*\([^\n]*\))?", 
        re.MULTILINE | re.IGNORECASE
    )

    parte_name_stop_patterns = [titulo_marker_regex, articulo_start_pattern, parte_marker_regex]
    titulo_name_stop_patterns = [articulo_start_pattern, titulo_marker_regex, parte_marker_regex, re.compile(r"^\s*CAPÍTULO\s+([IVXLCDM\d]+|ÚNICO)", re.MULTILINE | re.IGNORECASE)]
    
    lines_of_content = content_to_process.split('\n')
    
    parte_blocks = []
    current_block = {"header": None, "num_roman": None, "name_lines": [], "content_lines": []}
    in_name_extraction = False

    # Segment by PARTE markers
    for line_text in lines_of_content:
        parte_match = parte_marker_regex.match(line_text.strip())
        if parte_match:
            if current_block["header"]: 
                parte_blocks.append(current_block)
            current_block = {"header": parte_match.group(0), "num_roman": parte_match.group(1), "name_lines": [], "content_lines": []}
            in_name_extraction = True
        elif current_block["header"]:
            if in_name_extraction:
                stripped_line = line_text.strip()
                is_stop = any(pattern.match(stripped_line) for pattern in parte_name_stop_patterns if pattern != parte_marker_regex)
                if is_stop or (not stripped_line.isupper() and len(stripped_line.split()) > 10 and stripped_line):
                    if current_block["name_lines"]:
                        in_name_extraction = False
                    current_block["content_lines"].append(line_text) # This line is content or the stop line itself
                elif stripped_line:
                    current_block["name_lines"].append(stripped_line)
                # else: empty line, could be part of name formatting
            else:
                current_block["content_lines"].append(line_text)
    
    if current_block["header"]:
        parte_blocks.append(current_block)

    # Process each PARTE block
    for parte_data in parte_blocks:
        if not parte_data["num_roman"]: # Skip if somehow a block without a Roman numeral was created
            print(f"  Skipping a block without PARTE numeral: {parte_data.get('header', 'Unknown header')}")
            continue

        parte_num_roman = parte_data["num_roman"]
        parte_name = " ".join(parte_data["name_lines"]).strip()
        if not parte_name: # Fallback name if extraction failed
            parte_name = f"parte_{roman_to_int_simple(parte_num_roman)}_contenido_desconocido"
        
        # Truncate slug for PARTE folder name
        sanitized_parte_name_slug = slugify(parte_name, max_length=35) # Reduced max_length
        parte_folder_name = f"parte_{roman_to_int_simple(parte_num_roman)}_{sanitized_parte_name_slug}"
        current_parte_path = os.path.join(base_output_dir, parte_folder_name)
        os.makedirs(current_parte_path, exist_ok=True)
        print(f"  Created PARTE folder: {current_parte_path}")

        parte_articulos_details_list = [] # Initialize list for PARTE index

        content_for_titulos_str = "\n".join(parte_data["content_lines"])
        
        titulo_lines_for_processing = content_for_titulos_str.split('\n')
        titulo_sections = []
        # Initialize current_titulo_block for each PARTE
        current_titulo_block = {"header": None, "num_titulo": None, "name_lines": [], "content_lines": [], "content_lines_parte_direct": []}
        in_titulo_name_extraction = False

        # Segment by Titulo markers within the current PARTE's content
        for line_text in titulo_lines_for_processing:
            titulo_match = titulo_marker_regex.match(line_text.strip())
            if titulo_match:
                if current_titulo_block["header"] or current_titulo_block["content_lines_parte_direct"]: # Save previous block
                    titulo_sections.append(current_titulo_block)
                # Reset for new Titulo
                current_titulo_block = {"header": titulo_match.group(0), "num_titulo": titulo_match.group(1), "name_lines": [], "content_lines": [], "content_lines_parte_direct": []}
                in_titulo_name_extraction = True
            elif current_titulo_block.get("header"): # If we are inside a Titulo block (header is not None)
                if in_titulo_name_extraction:
                    stripped_line = line_text.strip()
                    is_stop = any(pattern.match(stripped_line) for pattern in titulo_name_stop_patterns if pattern != titulo_marker_regex)
                    
                    if is_stop or (not stripped_line.isupper() and len(stripped_line.split()) > 10 and stripped_line and not stripped_line.startswith("CAPÍTULO")):
                        if current_titulo_block["name_lines"]: # If name lines were collected, name extraction ends
                            in_titulo_name_extraction = False
                        current_titulo_block["content_lines"].append(line_text) # This line is content
                    elif stripped_line: # Looks like a Titulo name line
                        current_titulo_block["name_lines"].append(stripped_line)
                    # else: empty line, could be part of name formatting, continue in_titulo_name_extraction
                else: # After Titulo name, it's Titulo content
                    current_titulo_block["content_lines"].append(line_text)
            else: # Content belongs to PARTE directly if no Titulo marker found yet for this PARTE
                current_titulo_block["content_lines_parte_direct"].append(line_text)
        
        # Append the last processed block (could be a Titulo or direct PARTE content)
        if current_titulo_block["header"] or current_titulo_block["content_lines_parte_direct"]:
            titulo_sections.append(current_titulo_block)
        
        processed_titulo_names = {} # To store actual Titulo names for the index

        # Process collected Titulo sections or direct PARTE content
        if not titulo_sections or all(not ts.get("header") for ts in titulo_sections): # No explicit Titulos found, or only direct content
            # Truncate slug for implicit Título folder name
            implicit_titulo_folder_name_slug = slugify(parte_name, max_length=35) # Reduced max_length
            if not implicit_titulo_folder_name_slug: # Fallback if slug is empty
                implicit_titulo_folder_name_slug = f"titulo_predeterminado_parte_{roman_to_int_simple(parte_num_roman)}"
            current_titulo_path = os.path.join(current_parte_path, implicit_titulo_folder_name_slug)
            print(f"    Attempting to create implicit Título folder: {current_titulo_path}")
            os.makedirs(current_titulo_path, exist_ok=True)
            print(f"    Created implicit Título folder (from PARTE name '{parte_name}'): {current_titulo_path}")
            processed_titulo_names[implicit_titulo_folder_name_slug] = parte_name # Use parte name for display
            # Use the original content_for_titulos_str as it contains all content of the PARTE
            articles_processed_details = extract_and_save_articles(content_for_titulos_str, current_titulo_path, articulo_start_pattern, implicit_titulo_folder_name_slug, document_name_for_description)
            parte_articulos_details_list.extend(articles_processed_details)
        else:
            for titulo_data in titulo_sections:
                if titulo_data.get("header"): # Process as an explicit Titulo
                    titulo_num = titulo_data["num_titulo"] # This can be Roman or Arabic
                    titulo_name_full_lines = titulo_data["name_lines"]
                    refined_titulo_name_parts = []
                    for line in titulo_name_full_lines:
                        # Stop name at "CAPÍTULO" if it's a structural heading
                        if re.match(r"^\s*CAPÍTULO\s+([IVXLCDM\d]+|ÚNICO)", line, re.IGNORECASE):
                            break 
                        refined_titulo_name_parts.append(line)
                    titulo_name = " ".join(refined_titulo_name_parts).strip()
                    if not titulo_name: # Fallback name
                        titulo_name = f"titulo_{slugify(titulo_num)}_contenido_desconocido"
                    
                    # Truncate slug for Título folder name
                    sanitized_titulo_name_slug = slugify(titulo_name, max_length=35) # Reduced max_length
                    # Titulo number (titulo_num) itself is usually short, slugify it without max_length
                    titulo_folder_name = f"titulo_{slugify(titulo_num)}_{sanitized_titulo_name_slug}"
                    current_titulo_path = os.path.join(current_parte_path, titulo_folder_name)
                    print(f"    Attempting to create Título folder: {current_titulo_path}")
                    os.makedirs(current_titulo_path, exist_ok=True)
                    print(f"    Created Título folder: {current_titulo_path}")
                    processed_titulo_names[titulo_folder_name] = titulo_name # Store original name for index
                    
                    content_for_articulos = "\n".join(titulo_data["content_lines"])
                    articles_processed_details = extract_and_save_articles(content_for_articulos, current_titulo_path, articulo_start_pattern, titulo_folder_name, document_name_for_description)
                    parte_articulos_details_list.extend(articles_processed_details)
                elif titulo_data.get("content_lines_parte_direct") and titulo_data["content_lines_parte_direct"]:
                    # This case handles content that was not under an explicit Titulo header but was part of a PARTE
                    # that did have other explicit Titulos. This should be less common.
                    print(f"    Warning: Found direct PARTE content block within {parte_folder_name} that wasn't a full Titulo. Processing as separate section.")
                    # Truncate slug
                    direct_content_folder_slug = slugify(parte_name + "_seccion_directa", max_length=35) # Reduced max_length
                    current_titulo_path = os.path.join(current_parte_path, direct_content_folder_slug)
                    print(f"    Attempting to create direct content folder: {current_titulo_path}")
                    os.makedirs(current_titulo_path, exist_ok=True)
                    processed_titulo_names[direct_content_folder_slug] = parte_name + " (Sección Directa)"
                    articles_processed_details = extract_and_save_articles("\n".join(titulo_data["content_lines_parte_direct"]), current_titulo_path, articulo_start_pattern, direct_content_folder_slug, document_name_for_description)
                    parte_articulos_details_list.extend(articles_processed_details)
        
        # Create _index.mdx for the PARTE
        if parte_articulos_details_list:
            index_mdx_path = os.path.join(current_parte_path, "_index.mdx")
            parte_title_for_index = parte_name if parte_name else f"Parte {roman_to_int_simple(parte_num_roman).upper()}"
            index_mdx_content = f"---\ntitle: \"Contenido de la {parte_title_for_index}\"\n---\n\n"
            index_mdx_content += f"# Contenido de la {parte_title_for_index}\n\n"
            
            articulos_by_titulo_slug = {}
            for art_detail in parte_articulos_details_list:
                tslug = art_detail['titulo_slug']
                if tslug not in articulos_by_titulo_slug:
                    articulos_by_titulo_slug[tslug] = []
                articulos_by_titulo_slug[tslug].append(art_detail)

            for titulo_s, articles_in_titulo in articulos_by_titulo_slug.items():
                # Use the stored original Titulo name if available, otherwise generate from slug
                titulo_display_name = processed_titulo_names.get(titulo_s, titulo_s.replace("_", " ").title())
                index_mdx_content += f"## {titulo_display_name}\n\n"
                for art_detail in articles_in_titulo:
                    # Ensure relative_path uses the correct titulo_slug for the link
                    relative_path = f"{art_detail['titulo_slug']}/{art_detail['slug']}" 
                    desc_for_link = art_detail['desc_snippet'] if art_detail['desc_snippet'] else f"Artículo {art_detail['num']}"
                    index_mdx_content += f"- [Artículo {art_detail['num']}: {desc_for_link}]({relative_path})\n"
                index_mdx_content += "\n"

            with open(index_mdx_path, 'w', encoding='utf-8') as f:
                f.write(index_mdx_content)
            print(f"  Created PARTE index: {index_mdx_path}")
            
    print(f"Processing finished. MDX files generated in {base_output_dir}")

def extract_and_save_articles(text_block, current_titulo_dir_path, articulo_marker_regex, titulo_slug_for_index, doc_name_for_desc):
    """
    Extracts articles from a block of text, saves them with MDX frontmatter,
    and returns details for the PARTE index.
    """
    article_matches = list(articulo_marker_regex.finditer(text_block))
    processed_article_details = []

    for i, match in enumerate(article_matches):
        art_num_raw = match.group(2) # group(2) is the (\d+[A-Z]?(-[A-Z\d]+)?) part
        art_num_slug = slugify(art_num_raw) # Article numbers are usually short, no max_length needed here

        start_of_article_content = match.start() # The match itself is the "Artículo X." line

        if i + 1 < len(article_matches):
            end_of_article_content = article_matches[i+1].start()
        else:
            end_of_article_content = len(text_block)
        
        # Extract the full text of the article, including its "Artículo X." heading
        article_full_text = text_block[start_of_article_content:end_of_article_content].strip()

        if not article_full_text:
            print(f"      Warning: Empty article content for Artículo {art_num_raw} in {current_titulo_dir_path}")
            continue
        
        # --- MDX Frontmatter ---
        # Extract body for description snippet, removing the "Artículo X." part
        article_body_for_snippet = article_full_text
        heading_match = articulo_marker_regex.match(article_full_text) 
        if heading_match:
            article_body_for_snippet = article_full_text[heading_match.end():].strip()

        # Get first sentence or a limited snippet
        first_sentence_match = re.match(r"([^\.\n]+(?:[\.\n]|$))", article_body_for_snippet)
        snippet = ""
        if first_sentence_match:
            snippet = first_sentence_match.group(1).strip().replace('\n', ' ')
            if len(snippet) > 100: # Limit snippet length
                snippet = snippet[:97] + "..."
        elif article_body_for_snippet: # Fallback if no clear sentence end
            snippet = article_body_for_snippet[:100].strip().replace('\n', ' ') + ("..." if len(article_body_for_snippet) > 100 else "")

        description_frontmatter = f"Artículo {art_num_raw} del {doc_name_for_desc}. {snippet}".strip()
        if len(description_frontmatter) > 250: # Overall max length for description
            description_frontmatter = description_frontmatter[:247] + "..."
        
        # Ensure description is valid for YAML (e.g., escape quotes if necessary, though unlikely here)
        description_frontmatter = description_frontmatter.replace("\"", "'") # Basic quote handling

        mdx_frontmatter = f"---\ntitle: \"Artículo {art_num_raw}\"\ndescription: \"{description_frontmatter}\"\n---\n\n"
        mdx_content = mdx_frontmatter + article_full_text
        # --- End MDX Frontmatter ---

        file_name = f"articulo_{art_num_slug}.mdx"
        file_path = os.path.join(current_titulo_dir_path, file_name)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(mdx_content)
        except Exception as e:
            print(f"      Error saving {file_path}: {e}")
            continue # Skip adding to index if save fails
        
        processed_article_details.append({
            'num': art_num_raw,
            'slug': file_name, # This is now the filename, e.g., articulo_1.mdx
            'desc_snippet': snippet,
            'titulo_slug': titulo_slug_for_index # Pass the slug of the parent Titulo
        })

    if article_matches:
        print(f"      Processed {len(processed_article_details)} articles in {current_titulo_dir_path}")
    return processed_article_details


if __name__ == '__main__':
    # Specific input file for this run
    docx_file_name = "Acuerdo_927_de_2024_plan_de_desarrollo.docx"
    document_description_name = "Acuerdo 927 de 2024" # For MDX frontmatter
    
    # Generate output folder name based on the input DOCX file
    output_folder_name = slugify(os.path.splitext(docx_file_name)[0]) + "_mdx_output"
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_docx_path = os.path.join(script_dir, docx_file_name)
    # The base_output_dir is now directly the generated output_folder_name inside the script_dir
    full_output_dir_path = os.path.join(script_dir, output_folder_name) 

    if not os.path.exists(full_docx_path):
        # Fallback: check current working directory if not in script's directory
        if os.path.exists(docx_file_name): 
            full_docx_path = os.path.abspath(docx_file_name)
        else:
            print(f"Error: DOCX file '{docx_file_name}' not found in script directory ({script_dir}) or current working directory.")
            print("Please ensure the DOCX file is in the same directory as the script, or provide the full path if it's elsewhere.")
            exit()
    
    print(f"Input DOCX path: {full_docx_path}")
    print(f"Output will be in folder: {full_output_dir_path}")

    parse_and_create_mdx(full_docx_path, full_output_dir_path, document_description_name)