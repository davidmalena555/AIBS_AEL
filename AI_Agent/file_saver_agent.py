import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")


class FileSaverAgent:
    """
    Operational AI Agent:
    1. Analyzes the translated article to generate an appropriate filename.
    2. Saves the translated content into the target folder (translated_articles/).
    """

    def __init__(self, model=MODEL, output_dir="translated_articles"):
        self.model = model
        self.output_dir = Path(output_dir)

    def _ask_ai(self, instructions: str, text: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": text}
            ],
            "stream": False,
            "options": {"temperature": 0.1}
        }

        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["message"]["content"].strip()

    def generate_filename(self, text_content: str) -> str:
        instructions = """
You are a File Organizer Agent.
Generate a short, descriptive file name in English for this article.
Rules:
- Format: snake_case (e.g., business_growth_report_2026.txt).
- Maximum 4-5 words.
- Always end with .txt.
- Return ONLY the filename. No markdown, no quotes, no extra text.
"""
        try:
            raw_name = self._ask_ai(instructions, text_content[:400])
            clean_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '', raw_name)
            if not clean_name.endswith(".txt"):
                clean_name += ".txt"
            return clean_name
        except Exception:
            return "translated_article.txt"

    def save(self, content: str) -> Path:
        print("\n[FileSaverAgent] Analyzing article to generate filename...")
        filename = self.generate_filename(content)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        target_path = self.output_dir / filename

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        return target_path