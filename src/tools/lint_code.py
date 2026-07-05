import os
import re
import asyncio


async def get_linting_score(file_path: str) -> dict:
    """
    Runs pylint on a given Python file and returns its linting score.

    Args:
        file_path: The path to the Python file to lint.

    Returns:
        A dictionary containing the linting score as a float and any errors,
        or an error message if the file is not found or pylint fails.
    """
    if not os.path.exists(file_path):
        return {"error": f"Error: File not found at {file_path}"}
    if not file_path.endswith('.py'):
        return {"error": "Error: Not a Python file."}

    try:
        # Run pylint as a subprocess with the absolute file path
        absolute_file_path = os.path.abspath(file_path)
        command = f"pylint {absolute_file_path}"
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        pylint_output = stdout.decode()
        pylint_error = stderr.decode()

        if process.returncode != 0 and "No such file or directory" in pylint_error:
             return {"error": "Pylint is not installed or not found. Please install it using 'pip install pylint'."}
        elif process.returncode != 0 and pylint_error:
             return {"error": f"Pylint encountered an error: {pylint_error}"}

        # Extract the score using a regular expression
        match = re.search(r"Your code has been rated at ([-+]?\d*\.\d+|\d+)/10", pylint_output)
        if match:
            score_out_of_10 = float(match.group(1))
            percentage_score = score_out_of_10 * 10  # Convert to percentage
            return {"linting_score": percentage_score}
        else:
            # If pylint runs but doesn't output a score (e.g., empty file, only errors, no code)
            return {"linting_score": 0.0, "message": "Pylint ran, but no score could be extracted. Check output for details.", "pylint_output": pylint_output}

    except Exception as e:
        return {"error": f"An unexpected error occurred during linting: {e}"}
    