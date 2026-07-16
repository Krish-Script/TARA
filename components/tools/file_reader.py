import glob
from pathlib import Path
from components.error_manager import ToolExpectedError

class FileReaderTool:
    def __init__(self, llm):
        self.llm = llm
        
        # Dynamically resolve the Windows user home directory (e.g., C:\Users\Krishna)
        self.home_dir = Path.home()
        
        # Whitelisted path aliases for secure reading
        self.aliases = {
            "desktop": self.home_dir / "Desktop",
            "documents": self.home_dir / "Documents",
            "downloads": self.home_dir / "Downloads",
            "notes": Path("data/notes").resolve()
        }

        if (self.home_dir / "OneDrive" / "Desktop").exists():
            self.aliases["desktop"] = self.home_dir / "OneDrive" / "Desktop"
        if (self.home_dir / "OneDrive" / "Documents").exists():
            self.aliases["documents"] = self.home_dir / "OneDrive" / "Documents"

    def _resolve_path(self, filename: str, alias: str = "") -> Path:
        """Securely finds the most recently modified text file in allowed directories."""
        if alias and alias.lower() in self.aliases:
            search_dirs = [self.aliases[alias.lower()]]
        else:
            search_dirs = self.aliases.values()
        
        for directory in search_dirs:
            if not directory.exists():
                continue
            
            # Case-insensitive wildcard search using glob
            search_pattern = str(directory / f"*{filename}*")
            matches = glob.glob(search_pattern)
            
            # Filter for readable text formats
            text_matches = [m for m in matches if m.endswith(('.txt', '.md', '.csv', '.json', '.log'))]
            
            if text_matches:
                # Return the most recently modified match
                latest_file = max(text_matches, key=lambda x: Path(x).stat().st_mtime)
                return Path(latest_file)
                
        raise ToolExpectedError(f"I couldn't find a readable file named {filename} in your standard folders.")

    def read_file(self, query: str) -> dict:
        """Extracts filename, resolves path, reads, and summarizes if needed."""
        # 1. Extract target filename using LLM
        prompt = (
            "Extract the specific filename or subject the user wants to read. "
            "Return ONLY the core filename or subject, nothing else.\n"
            "User: 'Read my report document'\nTarget: report\n"
            "User: 'Can you read the meeting notes from my desktop?'\nTarget: meeting notes\n"
            f"User: '{query}'\nTarget:"
        )
        target_file, _ = self.llm.generate(prompt)
        target_file = target_file.strip().lower()
        
        if not target_file:
            raise ToolExpectedError("I wasn't sure which file you wanted me to read.")

        # 2. Check for explicit path aliases in the spoken query
        alias = ""
        for key in self.aliases.keys():
            if key in query.lower():
                alias = key
                break

        # 3. Resolve path securely
        filepath = self._resolve_path(target_file, alias)
        
        # 4. Read the content
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except Exception:
            raise ToolExpectedError(f"I found {filepath.name}, but I don't have permission to read it.")
        
        if not content:
            raise ToolExpectedError(f"{filepath.name} is completely empty.")

        # Strip our custom NotesTool headers if reading a note file
        clean_content = content.split("---\n")[-1] if "---\n" in content else content

        # 5. Summarize if too long (threshold: ~100 words / 500 characters)
        if len(clean_content) > 500:
            summary_prompt = (
                "Summarize this document concisely in 1 to 2 sentences for spoken audio. "
                "Do not use markdown, bullet points, or special characters.\n\n"
                f"Document: {clean_content}\n\nSummary:"
            )
            spoken_text, _ = self.llm.generate(summary_prompt)
            action = "summarize"
        else:
            spoken_text = clean_content
            action = "read"

        return {
            "action": action, 
            "filename": filepath.name, 
            "content": spoken_text.strip()
        }