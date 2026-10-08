import html
import json
import os
import re
import subprocess
import tempfile
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
    1. Loads a translated article from translated_articles/.
    2. Converts content into a structured 4-section executive Handbook.
    3. Exports and saves strictly the final PDF document into handbooks/.
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
Convert the provided business report into a standardized, executive 1-page Handbook.

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
- Detail 2-3 business KPIs or impact metrics mentioned in the text.

## 4. Quick-Start Action Sheet: Operational Guide
Target Audience: Operations Managers & Team Leads
- Day 1: Immediate audit / initial baseline
- Week 1: Core automation / safe deployment
- Week 2: Quality controls & thresholds
- Week 3: Scaling & fallback governance

IMPORTANT:
- Output only the markdown handbook.
- Do NOT include conversational filler like "Here is your handbook".
- Keep all anonymized tags (e.g. [Company_1], [CONFIDENTIAL_AMOUNT]) intact.
"""
        return self._ask_ai(instructions, article_text)

    def markdown_to_html(self, markdown_text: str) -> str:
        """Converts Markdown text into styled HTML for PDF rendering."""
        body_elements = []
        in_table = False
        table_rows = []

        lines = markdown_text.splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("|") and line.endswith("|"):
                if re.match(r"^\|[\s\-:|]+\|$", line):
                    continue
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if not in_table:
                    in_table = True
                    headers = "".join(f"<th>{html.escape(c)}</th>" for c in cells)
                    table_rows.append(f"<tr>{headers}</tr>")
                else:
                    cols = "".join(f"<td>{html.escape(c)}</td>" for c in cells)
                    table_rows.append(f"<tr>{cols}</tr>")
                continue
            else:
                if in_table:
                    body_elements.append(f"<table>{''.join(table_rows)}</table>")
                    table_rows = []
                    in_table = False

            if line.startswith("# "):
                body_elements.append(f"<h1>{html.escape(line[2:])}</h1>")
            elif line.startswith("## "):
                body_elements.append(f"<h2>{html.escape(line[3:])}</h2>")
            elif line.startswith("### "):
                body_elements.append(f"<h3>{html.escape(line[4:])}</h3>")
            elif line.startswith("- ") or line.startswith("* "):
                clean_bullet = re.sub(r"^[-*]\s+(\*\*)?", "", line).replace("**", "")
                body_elements.append(f"<li>{html.escape(clean_bullet)}</li>")
            else:
                clean_text = line.replace("**", "")
                body_elements.append(f"<p>{html.escape(clean_text)}</p>")

        if in_table:
            body_elements.append(f"<table>{''.join(table_rows)}</table>")

        body_html = "\n".join(body_elements)

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page {{ size: A4; margin: 18mm; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #1a202c;
        max-width: 820px;
        margin: 0 auto;
        padding: 20px;
        line-height: 1.5;
        font-size: 13px;
    }}
    h1 {{
        color: #1e3a8a;
        font-size: 20px;
        border-bottom: 2px solid #3b82f6;
        padding-bottom: 6px;
        margin-bottom: 16px;
    }}
    h2 {{
        color: #1d4ed8;
        font-size: 15px;
        margin-top: 18px;
        margin-bottom: 8px;
    }}
    h3 {{
        color: #4b5563;
        font-size: 13px;
        margin-top: 12px;
        margin-bottom: 4px;
    }}
    p, li {{
        margin-bottom: 4px;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 12px 0;
        font-size: 12px;
    }}
    th {{
        background-color: #eff6ff;
        color: #1e40af;
        border: 1px solid #bfdbfe;
        padding: 6px 8px;
        text-align: left;
    }}
    td {{
        border: 1px solid #e2e8f0;
        padding: 6px 8px;
        vertical-align: top;
    }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""

    def run(self, source_filename: str = None) -> Path:
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Directory '{self.input_dir}' does not exist.")

        if source_filename:
            file_path = self.input_dir / source_filename
        else:
            files = list(self.input_dir.glob("*.txt"))
            if not files:
                raise FileNotFoundError(f"No .txt files found in '{self.input_dir}'.")
            file_path = max(files, key=os.path.getmtime)

        print(f"\n[HandbookAgent] Loading article: {file_path.name}")
        with open(file_path, "r", encoding="utf-8") as f:
            article_content = f.read()

        print("[HandbookAgent] Generating structured Handbook via LLM...")
        handbook_md = self.generate_handbook(article_content)
        handbook_md = re.sub(r"^(Here's|Here is).*?:\s*", "", handbook_md, flags=re.IGNORECASE).strip()

        html_content = self.markdown_to_html(handbook_md)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = self.output_dir / f"{file_path.stem}_handbook.pdf"

        print("[HandbookAgent] Compiling directly to PDF...")
        with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as temp_html:
            temp_html.write(html_content)
            temp_html_path = temp_html.name

        try:
            subprocess.run(
                ["wkhtmltopdf", "--quiet", temp_html_path, str(pdf_path)],
                check=True
            )
            print(f"[HandbookAgent] PDF successfully created: {pdf_path}")
        except FileNotFoundError:
            raise RuntimeError(
                "wkhtmltopdf was not found. Install it by running: sudo apt update && sudo apt install -y wkhtmltopdf"
            )
        finally:
            if os.path.exists(temp_html_path):
                os.remove(temp_html_path)

        return pdf_path


if __name__ == "__main__":
    agent = HandbookAgent()
    try:
        agent.run()
    except Exception as e:
        print(f"Error: {e}")