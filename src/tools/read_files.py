import os




def read_file(file_path: str) -> str:
    """
    Reads the content of a file.

    Args:
        file_path: The path to the file.

    Returns:
        The content of the file as a string.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def read_directory_files(directory_path: str) -> dict[str, str]:
    """
    Reads the content of all files in a directory and its subdirectories.

    Args:
        directory_path: The path to the directory.

    Returns:
        A dictionary where keys are file paths and values are file contents.
    """
    if not os.path.isdir(directory_path):
        return {"error": f"Error: Directory not found at {directory_path}"}
    
    file_contents = {}
    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            # Skip .git directory files
            if '.git' in file_path.split(os.sep):
                continue
            file_contents[file_path] = read_file(file_path)
            
    return file_contents
