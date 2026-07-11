import os
import glob
import re
from datetime import datetime
from components.error_manager import ToolExpectedError

class NotesTool:
    def __init__(self, llm):
        """
        The NotesTool requires an LLM instance because the 'create' and 'read' 
        operations use brief prompts to format the text cleanly.
        """
        self.llm = llm
        self.notes_dir = "data/notes"
        
        # Ensure the directory exists on startup (Tier 1 safety)
        try:
            os.makedirs(self.notes_dir, exist_ok=True)
        except Exception as e:
            raise ToolExpectedError(f"I couldn't access the storage drive to set up your notes. {e}")

    def create_note(self, query: str) -> dict:
        """Extracts note content from voice query and saves it to a timestamped file."""
        # 1. Sprint Plan Extraction Prompt
        prompt = (
            "Extract the note content the user wants to save. Return only the content as written, "
            "without preamble or explanation. Preserve the user's exact wording.\n\n"
            "Examples:\n"
            "User: \"Take a note, I need to call the dentist on Thursday.\"\n"
            "Note: I need to call the dentist on Thursday.\n"
            "User: \"Note that the project deadline is the 15th of August.\"\n"
            "Note: The project deadline is the 15th of August.\n\n"
            f"User: \"{query}\"\nNote:"
        )
        
        # Generate extraction (using cold inference as we are bypassing the chat context)
        extracted_note, _ = self.llm.generate(prompt)
        extracted_note = extracted_note.strip()
        
        if not extracted_note:
            raise ToolExpectedError("I didn't catch what you wanted me to write down.")

        # 2. Save to file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}.txt"
        filepath = os.path.join(self.notes_dir, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                # Sprint plan requirement: save raw transcription alongside extracted text
                f.write(f"Raw Transcription: {query}\n---\n{extracted_note}")
        except Exception:
            raise ToolExpectedError("I couldn't save that note — there may be a storage issue.")
            
        print(f"\n[NotesTool] Saved to {filepath}")
        return {"action": "create", "content": extracted_note}

    def read_last_note(self, query: str = "") -> dict:
        """Reads and summarizes the most recently modified note."""
        files = glob.glob(os.path.join(self.notes_dir, "*.txt"))
        if not files:
            raise ToolExpectedError("You don't have any saved notes yet.")
            
        # Get most recently modified file
        latest_file = max(files, key=os.path.getmtime)
        
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            raise ToolExpectedError("I found your last note, but I don't have permission to read it.")

        # Strip the raw transcription header for reading
        clean_content = content.split("---\n")[-1] if "---\n" in content else content
        
        return {"action": "read", "content": clean_content}

    def list_notes(self, query: str = "") -> dict:
        """Counts notes and identifies the most recent date."""
        files = glob.glob(os.path.join(self.notes_dir, "*.txt"))
        count = len(files)
        
        if count == 0:
            raise ToolExpectedError("You don't have any notes saved right now.")
            
        latest_file = max(files, key=os.path.getmtime)
        # Extract date from filename YYYY-MM-DD
        filename = os.path.basename(latest_file)
        date_str = filename.split("_")[0] 
        
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            friendly_date = date_obj.strftime("%B %d")
        except ValueError:
            friendly_date = "recently"
            
        return {"action": "list", "count": count, "latest_date": friendly_date}

    def search_notes(self, query: str) -> dict:
        """Searches all notes for a specific phrase."""
        # Extremely basic NLP to strip the command part
        search_term = re.sub(r"(find my note about|do i have a note about|search my notes for|look up)", "", query.lower()).strip()
        search_term = search_term.strip("?.!")
        
        if not search_term:
            raise ToolExpectedError("What would you like me to search for in your notes?")
            
        files = glob.glob(os.path.join(self.notes_dir, "*.txt"))
        if not files:
            raise ToolExpectedError("You don't have any notes to search through yet.")
            
        for file in sorted(files, key=os.path.getmtime, reverse=True):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                    clean_content = content.split("---\n")[-1] if "---\n" in content else content
                    if search_term in clean_content.lower():
                        return {"action": "search", "term": search_term, "match": clean_content}
            except Exception:
                continue # Skip unreadable files
                
        raise ToolExpectedError(f"I couldn't find any notes mentioning {search_term}.")