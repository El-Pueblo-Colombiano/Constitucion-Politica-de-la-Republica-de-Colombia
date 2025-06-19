import os
import re

HEADER_TEMPLATE = '''---
title: "Artículo {n}"
description: "Artículo {n} Plan de Ordenamiento Territorial de Bogotá POT"
---\n\n'''

def has_yaml_header(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        return first_line.strip() == '---'

def add_header_to_file(filepath, n):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    header = HEADER_TEMPLATE.format(n=n)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(header + content)

def main():
    for filename in os.listdir('.'):
        if filename.startswith('articulo_') and filename.endswith('.mdx'):
            match = re.match(r'articulo_(\d+)\.mdx', filename)
            if match:
                n = match.group(1)
                if not has_yaml_header(filename):
                    print(f'Adding header to {filename}')
                    add_header_to_file(filename, n)
                else:
                    print(f'Skipping {filename} (already has header)')

if __name__ == '__main__':
    main() 