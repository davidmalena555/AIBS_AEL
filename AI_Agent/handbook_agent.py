import html
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Optional

MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/chat"
)


class HandbookAgent:
    """
    Synthetic AI Agent that:
    1. Loads translated articles from translated_articles/.
    2. Synthesizes a unified 2-chapter academic Handbook (Chapter 5 & 6) aligned with AIBS HAN methodology.
    3. Compiles directly into a styled, publication-ready PDF.
    """

    def __init__(self, model=MODEL, input_dir="translated_articles", output_dir="../handbooks"):
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
            "options": {"temperature": 0.25}
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
            raise RuntimeError("HandbookAgent: Cannot connect to Ollama. Please ensure it is running.")

    def generate_handbook(self, combined_articles_text: str) -> str:
        instructions = """
You are an expert Applied AI Researcher at HAN University of Applied Sciences.
Your task is to synthesize the provided company/sector reports into an official 2-Chapter Research Handbook for SME owners.
The document must strictly follow the academic handbook structure shown below, with factual, sober, and practical phrasing.

Format the markdown output strictly according to these two linked chapters:

# Chapter 5: SME Knowledge Gaps: What Regional SMEs Still Do Not Know About AI

## 1. The narrow question
- State in 2-3 sentences the core decision the owner faces: what they do not know yet, and what they need to know before committing budget to an AI tool.

## 2. The translation
- Frame the problem using the distinction between "known unknowns" (risks the firm already recognizes) and "unknown unknowns" (unidentified data/process blockers, such as dirty ERP records).
- State clearly: close the knowledge gaps here first, so the use cases in Chapter 6 become realistic investments rather than guesses.

## 3. Illustrative use case (CRISP-DM)
Walk through one specific, realistic business pain point across the 6 CRISP-DM stages:
- **Business understanding:** The specific operational goal (e.g. stockout reduction, automated invoicing).
- **Data understanding:** How known unknowns turn into unknown unknowns (missing fields, inconsistent historical data).
- **Data preparation:** The labor and timeline needed for data hygiene (e.g. 18-24 months of clean history).
- **Modelling:** Why generic off-the-shelf models fail if deployed on uncleaned data.
- **Evaluation:** Setting a strict confidence threshold (<85%) triggering manual human review.
- **Deployment:** The risk of deploying on guesswork before closing data gaps.

## 4. Recommended tooling
- Practical low-cost tools: staff AI usage survey, free readiness assessment checklists, and manual ERP data quality spot-checks.

## 5. Responsible AI and Trust
- Define the Data Boundary Rule: specify that no raw ERP exports, client identifiers, or proprietary pricing may be pasted into external public LLMs.

## 6. First five steps for an owner
1. Informally list which AI tools staff already use.
2. Select one specific operational bottleneck and define what must be true to trust an AI tool with it.
3. Conduct a spot check on historical records in the ERP for missing or invalid attributes.
4. Consult an independent trusted advisor on real ROI achieved by comparable firms.
5. Formulate a documented gap list as the direct input for choosing a use case in Chapter 6.

## 7. Sources
- Appraise sources: specify which findings originate from field data/interviews, and which from secondary reports (CBS, Eurostat, OECD, or trade press).

---

# Chapter 6: Practical AI Use Cases for Regional SMEs

## 1. Executive Summary & Context
- Summary of the SME context (100-200 employees, 1-2 internal IT staff, seasonal demand, operational bottlenecks).

## 2. Framework: The 3 AI Maturity Tiers for SMEs
- **Tier 1: Off-the-Shelf Generative & Visual Tools (Rapid Deployment)**
  - Description: Plug-and-play SaaS, automated email routing, lightweight marketing or visual assets.
  - Primary Goal: Eliminate administrative friction and lower time-to-market.
- **Tier 2: Workflow & Process Automation (Task-Level Optimization)**
  - Description: Embedded tools integrated with ERP/PIM systems for data cleaning, translation, and localized workflows.
  - Primary Goal: Save labor hours, eliminate manual spreadsheet entries, and reduce material waste.
- **Tier 3: Predictive Operations & Demand Balancing (Integrated Intelligence)**
  - Description: Fine-tuned predictive ML models for demand forecasting, automated reorders, and stock balancing.
  - Primary Goal: Prevent stockouts and balance seasonal spikes with human-in-the-loop oversight.

## 3. Comparative Benchmarks & Operational Performance
Create a clean Markdown table with exact columns:
| Maturity Tier | Implementation Focus | Operational Impact | Key SME ROI Anchor / KPI |

## 4. Regional Perspectives: Three AI Economies
- **United States:** Capital-intensive, platform-driven models focused on rapid market dominance and proprietary platforms.
- **China:** State-directed, vertically integrated industrial networks focusing on speed, manufacturing throughput, and shop-floor automation.
- **Europe:** SME Sovereignty & Sustainability Route prioritizing human-in-the-loop governance, worker autonomy, and strict compliance (GDPR, EU AI Act).

## 5. Quick-Start Action Sheet: SME AI Implementation Roadmap
- **Phase 1: Assessment & Data Audit (Weeks 1-2):** Audit ERP records, enforce local anonymization, and define anchor KPIs.
- **Phase 2: Tier 1 & Tier 2 Pilot Deployment (Weeks 3-4):** Deploy plug-and-play tools, automate high-friction workflows, and enforce citation verification.
- **Phase 3: Workflow Integration & Human Safeguards (Weeks 5-6):** Establish failure hooks, train internal IT staff, and ensure compliance with regional regulations.

IMPORTANT:
- Output only the markdown handbook.
- No conversational filler like "Here is the handbook".
- Preserve all anonymized tags intact ([Company_X], [CONFIDENTIAL_AMOUNT], [Person_X]).
"""
        return self._ask_ai(instructions, combined_articles_text)

    def markdown_to_html(self, markdown_text: str) -> str:
        """Converts Markdown text into academic-styled HTML formatted for wkhtmltopdf."""
        body_elements = []
        in_table = False
        table_rows = []

        lines = markdown_text.splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            # Page break divider
            if line == "---":
                if in_table:
                    body_elements.append(f"<table>{''.join(table_rows)}</table>")
                    table_rows = []
                    in_table = False
                body_elements.append('<div class="page-break"></div>')
                continue

            # Markdown Table parsing
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

            # Headings & List formatting
            if line.startswith("# "):
                body_elements.append(f"<h1>{html.escape(line[2:])}</h1>")
            elif line.startswith("## "):
                body_elements.append(f"<h2>{html.escape(line[3:])}</h2>")
            elif line.startswith("### "):
                body_elements.append(f"<h3>{html.escape(line[4:])}</h3>")
            elif line.startswith("- ") or line.startswith("* "):
                clean_bullet = re.sub(r"^[-*]\s+(\*\*)?", "", line).replace("**", "")
                body_elements.append(f"<li>{html.escape(clean_bullet)}</li>")
            elif re.match(r"^\d+\.\s+", line):
                clean_num = re.sub(r"^\d+\.\s+(\*\*)?", "", line).replace("**", "")
                body_elements.append(f"<li class='numbered'>{html.escape(clean_num)}</li>")
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
    @page {{
        size: A4;
        margin: 20mm 15mm 20mm 15mm;
        @bottom-right {{
            content: "HAN University of Applied Sciences Minor Data Driven Decision Making in Business";
            font-family: Arial, sans-serif;
            font-size: 8pt;
            color: #888888;
        }}
    }}
    body {{
        font-family: Arial, Helvetica, sans-serif;
        color: #222222;
        margin: 0;
        padding: 0;
        line-height: 1.45;
        font-size: 11pt;
    }}
    .page-break {{
        page-break-after: always;
        height: 0;
    }}
    .header-tag {{
        font-size: 9pt;
        color: #666666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
        border-bottom: 1px solid #d0d7de;
        padding-bottom: 4px;
    }}
    h1 {{
        color: #0f172a;
        font-size: 17pt;
        line-height: 1.25;
        margin-top: 6px;
        margin-bottom: 14px;
    }}
    h2 {{
        color: #1e3a8a;
        font-size: 12.5pt;
        margin-top: 14px;
        margin-bottom: 6px;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 3px;
    }}
    h3 {{
        color: #334155;
        font-size: 11pt;
        margin-top: 10px;
        margin-bottom: 4px;
    }}
    p {{
        margin: 0 0 7px 0;
        text-align: justify;
    }}
    ul, ol {{
        margin-top: 4px;
        margin-bottom: 8px;
        padding-left: 22px;
    }}
    li {{
        margin-bottom: 3px;
        text-align: justify;
    }}
    li.numbered {{
        margin-bottom: 4px;
        list-style-type: decimal;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0 12px 0;
        font-size: 9.5pt;
    }}
    th {{
        background-color: #f1f5f9;
        color: #0f172a;
        font-weight: bold;
        border: 1px solid #cbd5e1;
        padding: 6px 8px;
        text-align: left;
    }}
    td {{
        border: 1px solid #cbd5e1;
        padding: 5px 8px;
        vertical-align: top;
    }}
</style>
</head>
<body>
<div class="header-tag">AIBS & AEL Applied Research Handbook | AI Adoption for Regional SMEs</div>
{body_html}
</body>
</html>"""

    def _get_unique_pdf_path(self, base_name: str) -> Path:
        """Generates an incremented or timestamped PDF path to prevent overwriting."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        candidate = self.output_dir / f"{base_name}_handbook_{timestamp}.pdf"

        counter = 1
        while candidate.exists():
            candidate = self.output_dir / f"{base_name}_handbook_{timestamp}_{counter}.pdf"
            counter += 1

        return candidate

    def run(self, source_filename: Optional[str] = None, source_filenames: Optional[List[str]] = None) -> Path:
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Directory '{self.input_dir}' does not exist.")

        available_files = sorted(list(self.input_dir.glob("*.txt")))
        if not available_files:
            raise FileNotFoundError(f"No .txt files found in '{self.input_dir}'.")

        target_paths: List[Path] = []

        if source_filename:
            p = self.input_dir / source_filename
            if p.exists():
                target_paths.append(p)
        elif source_filenames:
            for fname in source_filenames:
                p = self.input_dir / fname
                if p.exists():
                    target_paths.append(p)
        else:
            print("\nAvailable translated articles for Academic Handbook synthesis:")
            print("0 - Process ALL available articles into one comprehensive Handbook")
            for idx, file in enumerate(available_files, start=1):
                print(f"{idx} - {file.name}")

            choice = input("\nSelect files to synthesize (e.g. '0' for all, or '1, 3'): ").strip()

            if choice == "0":
                target_paths = available_files
            else:
                try:
                    selected_indices = [int(i.strip()) - 1 for i in choice.split(",") if i.strip()]
                    target_paths = [available_files[i] for i in selected_indices if 0 <= i < len(available_files)]
                except ValueError:
                    print("Invalid selection. Defaulting to the latest article.")
                    target_paths = [max(available_files, key=os.path.getmtime)]

        if not target_paths:
            target_paths = [max(available_files, key=os.path.getmtime)]

        print(f"\n[HandbookAgent] Aggregating {len(target_paths)} source report(s):")
        combined_text_blocks = []
        for path in target_paths:
            print(f" -> Including: {path.name}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                combined_text_blocks.append(f"--- SOURCE DOCUMENT: {path.stem} ---\n{content}\n")

        aggregated_text = "\n\n".join(combined_text_blocks)

        print("[HandbookAgent] Synthesizing academic 2-chapter Handbook via LLM...")
        handbook_md = self.generate_handbook(aggregated_text)
        handbook_md = re.sub(r"^(Here's|Here is).*?:\s*", "", handbook_md, flags=re.IGNORECASE).strip()

        html_content = self.markdown_to_html(handbook_md)

        self.output_dir.mkdir(parents=True, exist_ok=True)

        if len(target_paths) > 1:
            base_filename = "AIBS_research_handbook"
        else:
            base_filename = target_paths[0].stem

        pdf_path = self._get_unique_pdf_path(base_filename)

        print(f"[HandbookAgent] Compiling official PDF: {pdf_path.name}...")
        with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as temp_html:
            temp_html.write(html_content)
            temp_html_path = temp_html.name

        try:
            footer_text = "HAN University of Applied Sciences Minor Data Driven Decision Making in Business"
            subprocess.run(
                [
                    "wkhtmltopdf",
                    "--quiet",
                    "--margin-top", "18mm",
                    "--margin-bottom", "18mm",
                    "--margin-left", "16mm",
                    "--margin-right", "16mm",
                    "--footer-font-size", "8",
                    "--footer-font-name", "Arial",
                    "--footer-left", footer_text,
                    "--footer-right", "Page [page] of [topage]",
                    temp_html_path,
                    str(pdf_path)
                ],
                check=True
            )
            print(f"[HandbookAgent] Official Research Handbook created: {pdf_path}")
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