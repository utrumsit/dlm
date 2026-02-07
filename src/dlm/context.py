"""
Context extraction for the reading assistant.
Handles scraping text from supported readers (Skim, Apple Books).
"""

import platform
import subprocess
import time


def get_current_context():
    """
    Attempt to get text from the active reader application.
    Returns:
        tuple: (source_app_name, context_text) or (None, error_message)
    """
    if platform.system() != "Darwin":
        return None, "Context extraction is only supported on macOS."

    # Check which app is frontmost or likely active
    # For now, we prioritize Skim if it's running and has docs open
    
    # Try Skim first (best support)
    skim_text = _get_skim_text()
    if skim_text:
        return "Skim", skim_text

    # Try Apple Books (requires clipboard workaround, so maybe only on explicit demand? 
    # For now, let's keep it safe and not clobber clipboard unless we are sure.)
    # In the proposal, we discussed this is invasive.
    # Let's stick to Skim for the automatic detection for now.
    
    return None, "No active Skim document found."


def _get_skim_text():
    """Get text from current page of frontmost Skim document via AppleScript."""
    script = '''
    tell application "System Events"
        set processExists to (name of processes) contains "Skim"
    end tell
    
    if processExists then
        tell application "Skim"
            if (count of documents) > 0 then
                set currentText to (get text of current page of document 1)
                return currentText
            end if
        end tell
    end if
    return ""
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None
