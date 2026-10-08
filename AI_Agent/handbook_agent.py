import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/chat"
)


class HandbookAgent:
    """
    Synthetic AI Agent that:
    1. Loads a translated article from the translated_articles/ directory.
    2. Converts the content into a structured Handbook (Markdown format)
       following a standardized 4-section template.
    3. Saves the resulting file into the handbooks/ directory.
    """

    def __init__(self, model=MODEL, input_dir="translated_articles", output_dir="handbooks"):
        self.model = model
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

    def _ask_ai(self, instructions: str, text: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": text}
            ],
            "stream": False,
            "options": {"temperature": 0.3}
        }

        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["message"]["content"].strip()
        except urllib.error.URLError:
            raise RuntimeError("HandbookAgent: Cannot connect to Ollama. Please make sure it is running.")

    def generate_handbook(self, article_text: str) -> str:
        instructions = """
You are the Handbook Synthesis Agent.
Your task is to convert the provided business/technical report into a standardized, professional 1-page Handbook.

Format the output strictly according to this 4-section structure:

# Handbook Page: [Insert Catchy Subject Title based on the text]

## 1. Problem Analysis: Risk & Operational Challenges
- Explain 2-3 core operational risks or bottlenecks highlighted in the text.
- Include a specific "Data Boundary / Compliance Rule" summarizing privacy or boundary limits.

## 2. Framework: The 3 Maturity Tiers
Create a Markdown table with exact columns:
| Maturity Tier | Safety & Governance Mechanism | Operational Use Case |
- Tier 1: Initial setup / basic guardrails
- Tier 2: Workflow automation / human-in-the-loop
- Tier 3: Advanced operations / validation hooks

## 3. Business Impact & Operational KPIs
- Detail 2-3 business KPIs or impact metrics mentioned or derived from the text (e.g. cost reduction, order accuracy, cycle time).

## 4. Quick-Start Action Sheet: Operational Guide
Target Audience: Operations Managers & Team Leads
- Day 1: Immediate audit / initial baseline
- Week 1: Core automation / safe deployment
- Week 2: Quality controls & thresholds
- Week 3: Scaling & fallback governance

IMPORTANT:
- Output only the markdown handbook.
- Do NOT include conversational filler like "Here is your handbook".
- Maintain all anonymized tags (like [Company_1], [CONFIDENTIAL_AMOUNT]) intact.
"""
        return self._ask_ai(instructions, article_text)

    def run(self, source_filename: str = None) -> Path:
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Directory '{self.input_dir}' does not exist.")

        # Select file
        if source_filename:
            file_path = self.input_dir / source_filename
        else:
            files = list(self.input_dir.glob("*.txt"))
            if not files:
                raise FileNotFoundError(f"No .txt files found in '{self.input_dir}'.")
            # Select the most recently modified file
            file_path = max(files, key=os.path.getmtime)

        print(f"\n[HandbookAgent] Loading article: {file_path.name}")
        with open(file_path, "r", encoding="utf-8") as f:
            article_content = f.read()

        print("[HandbookAgent] Generating structured Handbook via LLM...")
        handbook_md = self.generate_handbook(article_content)

        # Clean conversational intro if present
        handbook_md = re.sub(r"^(Here's|Here is).*?:\s*", "", handbook_md, flags=re.IGNORECASE).strip()

        # Save to handbooks/ directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        handbook_filename = file_path.stem + "_handbook.md"
        output_path = self.output_dir / handbook_filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(handbook_md)

        print(f"[HandbookAgent] Handbook successfully saved to: {output_path}")
        return output_path


if __name__ == "__main__":
    agent = HandbookAgent()
    try:
        agent.run()
    except Exception as e:
        print(f"Error: {e}")