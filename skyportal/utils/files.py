from pathlib import Path
import os
import re

RE_SLASHES = re.compile(r'^[\w_\-\+\/\\]*$')
RE_NO_SLASHES = re.compile(r'^[\w_\-\+]*$')

MAX_FILEPATH_LENGTH = 255


def check_path_string(string, allow_slashes=False):
    if allow_slashes:
        reg = RE_SLASHES
    else:
        reg = RE_NO_SLASHES

    if not reg.match(string):
        raise ValueError(f'Illegal characters in string "{string}". ')


def save_file_data(root_folder, path_string, filename, file_data):
    # the filename can have alphanumeric, underscores, + or -
    check_path_string(path_string)

    # make sure to replace windows style slashes
    subfolder = path_string.replace("\\", "/")

    path = os.path.join(root_folder, subfolder)
    if not os.path.exists(path):
        os.makedirs(path)

    full_path = os.path.join(path, filename)

    if len(full_path) > MAX_FILEPATH_LENGTH:
        raise ValueError(
            f'Full path to file {full_path} is longer than {MAX_FILEPATH_LENGTH} characters.'
        )

    with open(full_path, 'wb') as f:
        f.write(file_data)

    return full_path


def delete_file_data(attachment_path):
    if attachment_path:
        if os.path.exists(attachment_path):
            # remove the file and other files in the same directory
            os.remove(attachment_path)
        parent_dir = Path(attachment_path).parent
        try:
            if parent_dir.is_dir():
                for file_name in os.listdir(parent_dir):
                    file = str(parent_dir) + '/' + file_name
                    if os.path.isfile(file):
                        os.remove(file)
                parent_dir.rmdir()
        except OSError:
            pass
