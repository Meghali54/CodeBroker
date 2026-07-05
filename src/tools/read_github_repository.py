import os
import re
import shutil
import tempfile
import asyncio
from tools.read_files import read_directory_files



async def read_github_repository(repo_url: str) -> dict:
    """
    Clones a public GitHub repository and reads the content of all its files.
    Returns the temporary directory path where the repository was cloned, along with file contents.

    Args:
        repo_url: The full URL of the GitHub repository to clone.

    Returns:
        A dictionary with keys 'file_contents' (dictionary of file paths and contents) and 'temp_dir' (path to the temporary directory),
        or an error message.
    """
    print(f"Debug: read_github_repository received URL: {repo_url}") # Debug print
    # Validate the GitHub URL - more flexible regex
    if not re.match(r"https://github\.com/([^/]+)/([^/]+)", repo_url):
        return {"error": "Invalid GitHub repository URL provided."}

    temp_dir = tempfile.mkdtemp()
    try:
        # Construct the git clone command
        command = f"git clone --depth 1 {repo_url} ."
        
        # Execute the command in the temporary directory
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=temp_dir
        )
        
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            # Clean up on clone failure
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return {"error": f"Failed to clone repository. Error: {stderr.decode()}"}

        # Read the files from the cloned repository
        file_contents = read_directory_files(temp_dir)
        return {"file_contents": file_contents, "temp_dir": temp_dir}

    except Exception as e:
        # Clean up on unexpected error
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return {"error": f"An unexpected error occurred: {e}"}
            

def cleanup_temp_directory(directory_path: str) -> dict:
    """
    Removes a temporary directory and its contents.

    Args:
        directory_path: The path to the temporary directory to remove.

    Returns:
        A dictionary indicating success or an error message.
    """
    if not os.path.isdir(directory_path):
        return {"error": f"Error: Directory not found at {directory_path}"}
    try:
        shutil.rmtree(directory_path)
        return {"success": f"Successfully removed directory: {directory_path}"}
    except Exception as e:
        return {"error": f"Error removing directory {directory_path}: {e}"}

