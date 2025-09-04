from smolagents import tool
import os
import subprocess

@tool
def list_desktop() -> str:
    """
    List the contents of the current user's Desktop directory.

    Returns:
        str: A string containing the names of files and directories on the Desktop.
    """
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

    try:
        return subprocess.check_output(["ls", desktop_path], text=True)
    except Exception as e:
        return f"Error listing Desktop: {e}"

if __name__ == "__main__":
    print(list_desktop())
