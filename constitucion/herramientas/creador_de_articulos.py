import json

pages = []

def create_mdx_files(directory_path, first_number, last_number, series_name):
    for i in range(first_number, last_number+1):
        filename = f"{series_name}_{i}.mdx"
        filepath = f"{directory_path}/{filename}"
        default_lines = [
            "---",
            "title: \"Artículo {}\"".format(i),
            "description: \"Artículo {} de la Constitución Política de Colombia \"".format(i),
            "---"]
        with open(filepath, "w") as f:
            pages.append(filepath[:-4])

            for line in default_lines:
                f.write(line + "\n")
                # add path to the file to an array called "pages"
    return pages

pages = create_mdx_files("titulo_xiii/capitulo_6", 371, 373, "articulo")
json_pages = json.dumps(pages)
print(json_pages)

