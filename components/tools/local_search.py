import glob
from pathlib import Path
from components.error_manager import ToolExpectedError
from components.memory import MemoryStore
from config import MEMORY_CONFIG

class LocalSearchTool:
    def __init__(self, llm):
        self.llm = llm
        self.memory = MemoryStore(MEMORY_CONFIG["db_path"])
        self.notes_dir = Path("data/notes").resolve()

    def _search_notes(self, target: str) -> str: # type: ignore
        """Scans all local notes for the target keyword."""
        if not self.notes_dir.exists():
            return ""
            
        results = []
        target_lower = target.lower()
        target_stem = target_lower[:6]  # handles stemming variants
        
        for filepath in glob.glob(str(self.notes_dir / "*.txt")):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    clean_content = content.split("---\n")[-1] if "---\n" in content else content
                    content_lower = clean_content.lower()
                    
                    if target_lower in content_lower or target_stem in content_lower:
                        results.append(clean_content.strip())
            except Exception:
                continue
                
            return "\n\n".join(results)

    def search(self, query: str) -> dict:
        """Searches SQLite memory and text notes for the user's query."""
        # 1. Extract target keyword using LLM
        prompt = (
            "Extract the core subject the user is searching for as a single keyword.\n"
            "Return ONLY the keyword, nothing else.\n"
            "User: 'Do I have any notes about chess?'\nTarget: chess\n"
            "User: 'What do you know about my flight?'\nTarget: flight\n"
            f"User: '{query}'\nTarget:"
        )
        
        target, _ = self.llm.generate(prompt, memory_context="")
        target = target.strip().lower()
        
        if not target:
            raise ToolExpectedError("I wasn't sure what specific topic to search for.")

        # 2. Retrieve local data
        # Fetch the list of UserFact objects and ONLY keep facts matching the target
        facts_list = self.memory.get_facts()
        relevant_facts = [
            item.fact for item in facts_list 
            if target in item.fact.lower() or target[:6] in item.fact.lower()
        ]
        facts_context = "\n".join(relevant_facts) if relevant_facts else ""
        
        notes_context = self._search_notes(target)
        
        # If the target isn't found in either place, stop here
        if not notes_context and not facts_context:
            raise ToolExpectedError(f"I couldn't find any saved notes or facts about {target}.")

        # 3. Synthesize the answer using Recency Bias exploitation
        synth_prompt = (
            f"Database Facts:\n{facts_context if facts_context else 'None'}\n\n"
            f"Saved Notes:\n{notes_context if notes_context else 'None'}\n\n"
            "---\n"
            f"Task: Answer the user's query '{query}' strictly using the provided information above.\n"
            "Rules: Maximum of 2 sentences. Plain text only. Ignore unrelated details.\n"
            "Answer:"
        )
        
        answer, _ = self.llm.generate(synth_prompt, memory_context="")
        
        return {
            "target": target,
            "answer": answer.strip()
        }