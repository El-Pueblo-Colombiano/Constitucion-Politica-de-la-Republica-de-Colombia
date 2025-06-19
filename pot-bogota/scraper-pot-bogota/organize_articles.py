import os
import shutil
import re
import unicodedata

def slugify(text):
    # Remove accents, lowercase, replace spaces and special chars with underscores
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    text = re.sub(r'_+', '_', text).strip('_')
    return text

def extract_folder_name(node_name):
    m = re.match(r'^(libro|titulo|capitulo|subcapitulo|seccion|subseccion)\s*([ivxlcdu0-9áéíóúñ]+)', node_name.lower())
    if m:
        keyword = m.group(1)
        ident = slugify(m.group(2))
        return f"{keyword}_{ident}"
    return slugify(node_name)

def organize_articles(taxonomy_path, articles_dir, target_root, expected_count=608):
    with open(taxonomy_path, 'r', encoding='utf-8') as f:
        lines = [line.rstrip() for line in f if line.strip()]
    stack = []  # (indent, folder_name)
    copied = set()
    for line in lines:
        indent = len(line) - len(line.lstrip(' '))
        name = line.strip()
        # Determine current path
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if name.startswith('ARTÍCULO '):
            # Copy the article file
            article_num = re.search(r'ARTÍCULO (\d+)', name).group(1)
            folder_path = os.path.join(target_root, *[extract_folder_name(n) for _, n in stack])
            os.makedirs(folder_path, exist_ok=True)
            src_file = os.path.join(articles_dir, f'articulo_{article_num}.mdx')
            dst_file = os.path.join(folder_path, f'articulo_{article_num}.mdx')
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
                print(f'Copied {src_file} -> {dst_file}')
                copied.add(int(article_num))
            else:
                print(f'WARNING: {src_file} does not exist!')
        else:
            # It's a hierarchy node, add to stack
            stack.append((indent, name))
    # Summary
    print(f'\nSummary: {len(copied)} articles copied.')
    missing = [str(i) for i in range(1, expected_count+1) if i not in copied]
    if missing:
        print(f'Missing articles: {", ".join(missing)}')
    else:
        print('All articles were found and copied!')

if __name__ == '__main__':
    base_dir = os.path.dirname(__file__)
    taxonomy_path = os.path.join(base_dir, 'raw-data', 'taxonomy_tree.txt')
    articles_dir = os.path.join(base_dir, 'pot_articles')
    # Use pot-bogota as the root for the folder structure
    target_root = os.path.abspath(os.path.join(base_dir, '..'))
    organize_articles(taxonomy_path, articles_dir, target_root) 