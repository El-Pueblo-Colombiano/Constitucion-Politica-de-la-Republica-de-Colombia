## create a series of folders inside a folder

import os

def create_folders(directory_path, first_number, last_number, series_name):
    for i in range(first_number, last_number+1):
        folder_name = f"{series_name}_{i}"
        folder_path = f"{directory_path}/{folder_name}"
        os.mkdir(folder_path)
        # add path to the file to an array called "pages"

create_folders("titulo_xiii/", 1, 8, "capitulo")
