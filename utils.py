import glob
import os


async def count_code_lines():
    """Count lines of Python code in the current folder

    Comments and empty lines are ignored."""
    count = 0
    path = os.path.dirname(__file__)+'/**/*.py'
    for filename in glob.iglob(path, recursive=True):
        if '/env/' in filename or not filename.endswith('.py'):
            continue
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file.read().split("\n"):
                cleaned_line = line.strip()
                if len(cleaned_line) > 2 and not cleaned_line.startswith('#') or cleaned_line.startswith('"'):
                    count += 1
    return count
