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

def slugify(value, allow_unicode=False, max_length=None):
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
                if not any(header_cells_text): # If first row is empty, treat as no header
                    num_cols = len(block.columns)
                    table_md += "| " + " | ".join([f"Columna {j+1}" for j in range(num_cols)]) + " |\n"
                    table_md += "| " + " | ".join(["---"] * num_cols) + " |\n"
                    start_row_index = 0
                else:
                    table_md += "| " + " | ".join(header_cells_text) + " |\n"
                    table_md += "| " + " | ".join(["---"] * len(header_cells_text)) + " |\n"
                    start_row_index = 1 # Data rows start from the second row

                # Data Rows
                for i in range(start_row_index, len(block.rows)):
                    row = block.rows[i]
                    row_cells_text = [cell.text.strip().replace("\n", " <br> ") for cell in row.cells]
                    
                    # Ensure row has same number of columns as header for valid Markdown
                    # If header was empty, use num_cols determined earlier
                    expected_cols = len(header_cells_text) if header_cells_text and any(header_cells_text) else num_cols
                    
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


def parse_and_create_mdx(docx_path, base_output_dir):
    """
    Parses the DOCX and creates the MDX directory structure and files.
    """
    print(f"Starting processing for DOCX: {docx_path}")

    if os.path.exists(base_output_dir):
        shutil.rmtree(base_output_dir) 
    os.makedirs(base_output_dir, exist_ok=True)
    print(f"Created base output directory: {base_output_dir}")

    full_text_with_tables = extract_text_and_tables_from_docx(docx_path) # Use new extraction function

    decreto_content_match = re.search(r"DECRETA[:\s]*\n(.*)", full_text_with_tables, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if not decreto_content_match:
        print("Warning: Could not find 'DECRETA:' marker. Processing entire document.")
        content_to_process = full_text_with_tables
    else:
        content_to_process = decreto_content_match.group(1)
        print("Found 'DECRETA:', processing content thereafter.")

    libro_marker_regex = re.compile(r"^\s*LIBRO\s+([IVXLCDM]+)\s*$", re.MULTILINE | re.IGNORECASE)
    titulo_marker_regex = re.compile(r"^\s*TÍTULO\s+(\d+)\s*$", re.MULTILINE | re.IGNORECASE)
    articulo_start_pattern = re.compile(
        r"^(Artículo|Articulo)\s+(\d+[A-Z]?(\-[A-Z\d]+)?)\.(?:\s*\([^\n]*\))?", 
        re.MULTILINE | re.IGNORECASE
    )

    libro_name_stop_patterns = [titulo_marker_regex, articulo_start_pattern, libro_marker_regex]
    titulo_name_stop_patterns = [articulo_start_pattern, titulo_marker_regex, libro_marker_regex, re.compile(r"^\s*CAPÍTULO\s+([IVXLCDM\d]+|ÚNICO)", re.MULTILINE | re.IGNORECASE)]
    
    lines_of_content = content_to_process.split('\n')
    
    libro_blocks = []
    current_block = {"header": None, "num_roman": None, "name_lines": [], "content_lines": []}
    in_name_extraction = False

    for line_text in lines_of_content:
        libro_match = libro_marker_regex.match(line_text.strip())
        if libro_match:
            if current_block["header"]: 
                libro_blocks.append(current_block)
            current_block = {"header": libro_match.group(0), "num_roman": libro_match.group(1), "name_lines": [], "content_lines": []}
            in_name_extraction = True
        elif current_block["header"]:
            if in_name_extraction:
                stripped_line = line_text.strip()
                is_stop = any(pattern.match(stripped_line) for pattern in libro_name_stop_patterns if pattern != libro_marker_regex)
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
        libro_blocks.append(current_block)

    for libro_data in libro_blocks:
        if not libro_data["num_roman"]:
            print(f"  Skipping a block without Libro numeral: {libro_data.get('header', 'Unknown header')}")
            continue

        libro_num_roman = libro_data["num_roman"]
        libro_name = " ".join(libro_data["name_lines"]).strip()
        if not libro_name:
            libro_name = f"libro_{roman_to_int_simple(libro_num_roman)}_contenido_desconocido"
        
        sanitized_libro_name_slug = slugify(libro_name, max_length=50) 
        libro_folder_name = f"libro_{roman_to_int_simple(libro_num_roman)}_{sanitized_libro_name_slug}"
        current_libro_path = os.path.join(base_output_dir, libro_folder_name)
        os.makedirs(current_libro_path, exist_ok=True)
        print(f"  Created Libro folder: {current_libro_path}")

        libro_articulos_details_list = [] # Initialize list for Libro index

        content_for_titulos_str = "\n".join(libro_data["content_lines"])
        
        titulo_lines_for_processing = content_for_titulos_str.split('\n')
        titulo_sections = []
        current_titulo_block = {"header": None, "num_arabic": None, "name_lines": [], "content_lines": [], "content_lines_libro_direct": []}
        in_titulo_name_extraction = False

        for line_text in titulo_lines_for_processing:
            titulo_match = titulo_marker_regex.match(line_text.strip())
            if titulo_match:
                if current_titulo_block["header"] or current_titulo_block["content_lines_libro_direct"]:
                    titulo_sections.append(current_titulo_block)
                current_titulo_block = {"header": titulo_match.group(0), "num_arabic": titulo_match.group(1), "name_lines": [], "content_lines": [], "content_lines_libro_direct": []}
                in_titulo_name_extraction = True
            elif current_titulo_block.get("header"):
                if in_titulo_name_extraction:
                    stripped_line = line_text.strip()
                    is_stop = any(pattern.match(stripped_line) for pattern in titulo_name_stop_patterns if pattern != titulo_marker_regex)
                    if is_stop or (not stripped_line.isupper() and len(stripped_line.split()) > 10 and stripped_line and not stripped_line.startswith("CAPÍTULO")):
                        if current_titulo_block["name_lines"]:
                            in_titulo_name_extraction = False
                        current_titulo_block["content_lines"].append(line_text)
                    elif stripped_line:
                        current_titulo_block["name_lines"].append(stripped_line)
                else:
                    current_titulo_block["content_lines"].append(line_text)
            else: 
                current_titulo_block["content_lines_libro_direct"].append(line_text)
        
        if current_titulo_block["header"] or current_titulo_block["content_lines_libro_direct"]:
            titulo_sections.append(current_titulo_block)
        
        processed_titulo_names = {} # To store actual Titulo names for the index

        if not titulo_sections or all(not ts.get("header") for ts in titulo_sections):
            implicit_titulo_folder_name_slug = slugify(libro_name, max_length=50) 
            if not implicit_titulo_folder_name_slug:
                implicit_titulo_folder_name_slug = f"titulo_predeterminado_libro_{roman_to_int_simple(libro_num_roman)}"
            current_titulo_path = os.path.join(current_libro_path, implicit_titulo_folder_name_slug)
            os.makedirs(current_titulo_path, exist_ok=True)
            print(f"    Created implicit Título folder (from Libro name '{libro_name}'): {current_titulo_path}")
            processed_titulo_names[implicit_titulo_folder_name_slug] = libro_name # Use libro name for display
            articles_processed_details = extract_and_save_articles(content_for_titulos_str, current_titulo_path, articulo_start_pattern, implicit_titulo_folder_name_slug)
            libro_articulos_details_list.extend(articles_processed_details)
        else:
            for titulo_data in titulo_sections:
                if titulo_data.get("header"):
                    titulo_num_arabic = titulo_data["num_arabic"]
                    titulo_name_full_lines = titulo_data["name_lines"]
                    refined_titulo_name_parts = []
                    for line in titulo_name_full_lines:
                        if re.match(r"^\s*CAPÍTULO\s+([IVXLCDM\d]+|ÚNICO)", line, re.IGNORECASE):
                            break
                        refined_titulo_name_parts.append(line)
                    titulo_name = " ".join(refined_titulo_name_parts).strip()
                    if not titulo_name:
                        titulo_name = f"titulo_{titulo_num_arabic}_contenido_desconocido"
                    
                    sanitized_titulo_name_slug = slugify(titulo_name, max_length=50)
                    titulo_folder_name = f"titulo_{titulo_num_arabic}_{sanitized_titulo_name_slug}"
                    current_titulo_path = os.path.join(current_libro_path, titulo_folder_name)
                    os.makedirs(current_titulo_path, exist_ok=True)
                    print(f"    Created Título folder: {current_titulo_path}")
                    processed_titulo_names[titulo_folder_name] = titulo_name # Store original name
                    
                    content_for_articulos = "\n".join(titulo_data["content_lines"])
                    articles_processed_details = extract_and_save_articles(content_for_articulos, current_titulo_path, articulo_start_pattern, titulo_folder_name)
                    libro_articulos_details_list.extend(articles_processed_details)
                elif titulo_data.get("content_lines_libro_direct") and titulo_data["content_lines_libro_direct"]:
                    print(f"    Warning: Found direct libro content block within {libro_folder_name} that wasn't a full Titulo. Processing as separate section.")
                    direct_content_folder_slug = slugify(libro_name + "_seccion_directa", max_length=50)
                    current_titulo_path = os.path.join(current_libro_path, direct_content_folder_slug)
                    os.makedirs(current_titulo_path, exist_ok=True)
                    processed_titulo_names[direct_content_folder_slug] = libro_name + " (Sección Directa)"
                    articles_processed_details = extract_and_save_articles("\n".join(titulo_data["content_lines_libro_direct"]), current_titulo_path, articulo_start_pattern, direct_content_folder_slug)
                    libro_articulos_details_list.extend(articles_processed_details)
        
        # Create _index.mdx for the Libro
        if libro_articulos_details_list:
            index_mdx_path = os.path.join(current_libro_path, "_index.mdx")
            libro_title_for_index = libro_name if libro_name else f"Libro {roman_to_int_simple(libro_num_roman).upper()}"
            index_mdx_content = f"---\ntitle: \"Contenido del {libro_title_for_index}\"\n---\n\n"
            index_mdx_content += f"# Contenido del {libro_title_for_index}\n\n"
            
            articulos_by_titulo_slug = {}
            for art_detail in libro_articulos_details_list:
                tslug = art_detail['titulo_slug']
                if tslug not in articulos_by_titulo_slug:
                    articulos_by_titulo_slug[tslug] = []
                articulos_by_titulo_slug[tslug].append(art_detail)

            for titulo_s, articles_in_titulo in articulos_by_titulo_slug.items():
                # Use the stored original Titulo name if available, otherwise generate from slug
                titulo_display_name = processed_titulo_names.get(titulo_s, titulo_s.replace("_", " ").title())
                index_mdx_content += f"## {titulo_display_name}\n\n"
                for art_detail in articles_in_titulo:
                    relative_path = f"{art_detail['titulo_slug']}/{art_detail['slug']}" # slug is already file_name e.g. articulo_1.mdx
                    desc_for_link = art_detail['desc_snippet'] if art_detail['desc_snippet'] else f"Artículo {art_detail['num']}"
                    index_mdx_content += f"- [Artículo {art_detail['num']}: {desc_for_link}]({relative_path})\n"
                index_mdx_content += "\n"

            with open(index_mdx_path, 'w', encoding='utf-8') as f:
                f.write(index_mdx_content)
            print(f"  Created Libro index: {index_mdx_path}")
            
    print(f"Processing finished. MDX files generated in {base_output_dir}")

def extract_and_save_articles(text_block, current_titulo_dir_path, articulo_marker_regex, titulo_slug_for_index):
    """
    Extracts articles from a block of text, saves them with MDX frontmatter,
    and returns details for the Libro index.
    """
    article_matches = list(articulo_marker_regex.finditer(text_block))
    processed_article_details = []

    for i, match in enumerate(article_matches):
        art_num_raw = match.group(2) 
        art_num_slug = slugify(art_num_raw) 

        start_of_article_content = match.start()
        if i + 1 < len(article_matches):
            end_of_article_content = article_matches[i+1].start()
        else:
            end_of_article_content = len(text_block)
        
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
            if len(snippet) > 100: 
                snippet = snippet[:97] + "..."
        elif article_body_for_snippet: 
            snippet = article_body_for_snippet[:100].strip().replace('\n', ' ') + ("..." if len(article_body_for_snippet) > 100 else "")

        description_frontmatter = f"Artículo {art_num_raw} del Decreto 555 de 2021. {snippet}".strip()
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
            'titulo_slug': titulo_slug_for_index
        })

    if article_matches:
        print(f"      Processed {len(processed_article_details)} articles in {current_titulo_dir_path}")
    return processed_article_details


if __name__ == '__main__':
    docx_file_name = "Decreto_555_de_2021_Alcaldia.docx" 
    output_folder_name = "pot-bogota" # User specified this as the direct output folder
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_docx_path = os.path.join(script_dir, docx_file_name)
    # The base_output_dir is now directly 'pot-bogota' inside the script_dir
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

    parse_and_create_mdx(full_docx_path, full_output_dir_path)