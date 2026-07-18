import glob
from pathlib import Path
from components.error_manager import ToolExpectedError

class FileReaderTool:
    def __init__(self, llm):
        self.llm = llm
        
        # Dynamically resolve the Windows user home directory
        self.home_dir = Path.home()
        
        # Whitelisted path aliases for secure reading
        self.aliases = {
            "desktop": self.home_dir / "Desktop",
            "documents": self.home_dir / "Documents",
            "downloads": self.home_dir / "Downloads",
            "notes": Path("data/notes").resolve(),
            "tara": Path(".").resolve()  # Added to allow searching the project root!
        }
        
        # Windows OneDrive Fallback
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
        
        # FIX 3: Empty context for zero-shot text processing
        target_file, _ = self.llm.generate(prompt, memory_context="")
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
        
        # 4. Read the content with file size and binary guards
        try:
            # FIX 2: File size guard
            file_size = filepath.stat().st_size
            if file_size > 50_000:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read(3000).strip()
                content = content + "\n[File truncated — showing first 3000 characters only]"
            else:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    
        # FIX 1: Explicit error handling
        except UnicodeDecodeError:
            raise ToolExpectedError(f"{filepath.name} doesn't look like a text file I can read.")
        except PermissionError:
            raise ToolExpectedError(f"I found {filepath.name}, but I don't have permission to read it.")
        except Exception:
            raise ToolExpectedError(f"I had trouble reading {filepath.name}.")
        
        if not content:
            raise ToolExpectedError(f"{filepath.name} is completely empty.")

        # Strip our custom NotesTool headers ONLY if reading a note file
        if "notes" in filepath.parts and "---\n" in content:
            clean_content = content.split("---\n")[-1]
        else:
            clean_content = content

        # 5. Summarize if too long (threshold: ~100 words / 500 characters)
        if len(clean_content) > 500:
            # Starve the format bleed: give it only the first 1000 characters to summarize
            preview = clean_content[:1000]
            
            # Exploit recency bias: put the strict rules AT THE BOTTOM
            summary_prompt = (
                f"Document Preview:\n{preview}\n\n"
                "---\n"
                "Task: Write a 1-sentence spoken summary of the document above.\n"
                "Rules: Use plain text only. Do NOT use markdown, headings, or lists.\n"
                "Spoken Summary:"
            )
            # Empty context for zero-shot text processing
            spoken_text, _ = self.llm.generate(summary_prompt, memory_context="")
            action = "summarize"
        else:
            spoken_text = clean_content
            action = "read"

        return {
            "action": action, 
            "filename": filepath.name, 
            "content": spoken_text.strip()
        }