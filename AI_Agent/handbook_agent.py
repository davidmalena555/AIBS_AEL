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
    2. Synthesizes an official HAN AIBS x AEL Course Handbook with compact continuous layout.
    3. Compiles directly into a styled, publication-ready PDF via wkhtmltopdf.
    """

    def __init__(self, model: str = MODEL, input_dir: str = "translated_articles", output_dir: str = "../handbooks"):
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
Synthesize the provided SME research into the official HAN AIBS x AEL Course Handbook format.

CRITICAL INSTRUCTIONS:
- Strictly follow the official course template structure. Do NOT invent new arbitrary headings.
- Use concise, sober, practical language suitable for busy SME business owners. Keep explanations compact and punchy.
- Preserve all anonymized tokens intact ([Company_X], [CONFIDENTIAL_AMOUNT], [Person_X]).
- Output strictly clean Markdown only (no conversational filler).

REQUIRED SECTIONS TO GENERATE:

# AI for SMEs — Handbook
A living handbook that helps regional manufacturing & wholesale SMEs put AI to work — written by HAN students, one practical question at a time.

This is the handbook's template. The structure is the shell every cohort fills. Content comes from the teams: researched in the AIBS module, and produced through the research platform the same teams build in AEL.

---

# Start here
Orientation for an SME owner who is new to AI: what this handbook is, who it is for, how to use it, and what it deliberately does not do. Written for a busy non-technical reader — plain language, no jargon, and short enough to read in one sitting.

---

# The questions this handbook answers
The handbook is organised by themes, and every theme is posed as a question an owner would actually ask — not as a topic. The themes are the stable structure; the chapters beneath them compound from cohort to cohort.

| # | Theme | The SME-facing question |
|---|---|---|
| 1 | SME Knowledge Gaps | What do we not know yet about AI, and what would we need to know to decide well? |
| 2 | AI Use Cases at SMEs | What do firms like mine use AI for, and what actually pays off? |

---

# Chapter template: Theme 1 — What do we not know yet about AI, and what would we need to know to decide well?
*One sentence on what this chapter helps an owner do.*
Team: AIBS Cohort | SME Context: Dutch Wholesale & Distribution (e.g. sports teamwear) | Sources last appraised: October 2026

## 1. The question, for this kind of SME
Narrow down the question to regional SMEs (10-100 employees, limited IT staff, seasonal stock spikes).

## 2. The translation
Turn academic theory into plain guidance an owner can act on. Clearly separate what the firm says it needs from what empirical evidence shows it actually lacks.

## 3. Illustrative use case (CRISP-DM)
Examine the gap through all six CRISP-DM phases:
- **Business understanding:** Operational objective (reducing pre-season stockouts).
- **Data understanding:** Recognizing unorganized historical sales in ERP and broken size runs.
- **Data preparation:** Time and local cleaning needed before modeling.
- **Modelling:** Baseline rule-based logic vs. predictive ML.
- **Evaluation:** Setting strict accuracy thresholds and human-in-the-loop review.
- **Deployment:** Practical spreadsheet or ERP export integration.

## 4. Recommended tooling
Concrete, accessible options (no-code first, Excel Power Query, simple Python scripts) with effort and cost estimates.

## 5. Responsible AI & trust
Data ownership, local data boundaries (no private ERP records in public models), and GDPR compliance.

## 6. First five steps for an owner
Concrete Monday-morning actions (audit staff AI tools, spot-check ERP data, define a single bottleneck, consult peer SMEs).

## 7. Sources
Trace claims to field interviews and secondary reports (CBS, Eurostat, trade literature).

---

# Chapter template: Theme 2 — What do firms like mine use AI for, and what pays off?
*One sentence on what this chapter helps an owner do.*
Team: AIBS Cohort | SME Context: Regional SME Operations & Wholesale | Sources last appraised: October 2026

## 1. The question, for this kind of SME
Narrow down to practical, high-ROI AI adoption for inventory, customer communications, or forecasting.

## 2. The translation
How regional SMEs can implement AI pragmatically through 3 maturity tiers:
- Tier 1: Off-the-shelf generative & administrative tools (low effort, quick wins).
- Tier 2: Workflow & task automation (ERP connectors, semi-automated categorization).
- Tier 3: Predictive operations (demand balancing and replenishment alerts).

## 3. Illustrative use case (CRISP-DM)
Walk through a concrete implementation across the 6 CRISP-DM stages:
- **Business understanding:** Target ROI and service level improvement.
- **Data understanding:** Transaction logs and seasonal demand cycles.
- **Data preparation:** Merging sales history with supplier lead times.
- **Modelling:** Time-series / decision trees vs baseline moving average.
- **Evaluation:** Forecast error reduction and stockout reduction metrics.
- **Deployment:** Automated weekly reorder alert generated for the warehouse manager.

## 4. Recommended tooling
Accessible tooling index, estimated setup effort in hours, and subscription costs.

## 5. Responsible AI & trust
Safeguards, bias detection, and human validation for all automated purchase suggestions.

## 6. First five steps for an owner
Five concrete steps to trial a pilot project within 30 days.

## 7. Sources
Appraised field research sources, vendor reality check, and industry benchmarks.

---

# Tooling index
The accessible, mostly no-code tools referenced across the chapters, in one place: what each is for, what it costs in money and effort, and which chapter shows it in use.

---

# Regional ecosystem & support
Where an owner in the region can go next: innovation centres, hubs, training, funding, and regional networks (e.g. Oost NL, VNO-NCW, HAN Applied Research).

---

# About this handbook
- **Who writes it:** Students of HAN University of Applied Sciences, in teams, as the integrated task of the AIBS module and the AEL module.
- **The quality bar:** Clarity, accuracy against appraised sources, responsible-AI coverage, and usefulness.
- **Educational, not consultancy:** Inspirational guidance, not commercial liability.
- **Confidentiality:** Real SME cases are anonymised.
"""
        return self._ask_ai(instructions, combined_articles_text)

    def markdown_to_html(self, markdown_text: str) -> str:
        """Converts Markdown text into official HAN AIBS x AEL styled HTML without forced page breaks."""
        body_elements = []
        in_table = False
        table_rows = []

        lines = markdown_text.splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            # Nahrazení tvrdého zlomu stránky jemnou dělicí čarou
            if line == "---":
                if in_table:
                    body_elements.append(f"<table>{''.join(table_rows)}</table>")
                    table_rows = []
                    in_table = False
                body_elements.append('<div class="section-divider"></div>')
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

            # Nadpisy a odstavce s kompaktními mezerami
            if line.startswith("# "):
                title_text = line[2:]
                body_elements.append(f'<div class="accent-bar"></div><h1>{html.escape(title_text)}</h1>')
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
                if clean_text.startswith("Orientation for an SME owner") or clean_text.startswith("The accessible, mostly no-code") or clean_text.startswith("Where an owner in the region"):
                    body_elements.append(f"<div class='callout-box-dashed'>{html.escape(clean_text)}</div>")
                elif clean_text.startswith("This is the handbook's template") or clean_text.startswith("A living handbook"):
                    body_elements.append(f"<div class='callout-box-yellow'>{html.escape(clean_text)}</div>")
                else:
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
        margin: 12mm 14mm 12mm 14mm;
        @bottom-right {{
            content: "HAN University of Applied Sciences · AIBS × AEL";
            font-family: Arial, sans-serif;
            font-size: 7.5pt;
            color: #888888;
        }}
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #111827;
        margin: 0;
        padding: 0;
        line-height: 1.35;
        font-size: 9.5pt;
    }}
    .super-title {{
        font-size: 8pt;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #4b5563;
        font-weight: 700;
        margin-bottom: 2px;
    }}
    .accent-bar {{
        width: 32px;
        height: 3.5px;
        background-color: #c9d200;
        margin: 10px 0 4px 0;
    }}
    .section-divider {{
        border-top: 1px solid #e2e8f0;
        margin: 10px 0;
    }}
    h1 {{
        font-size: 16pt;
        font-weight: 800;
        color: #0f172a;
        margin-top: 0;
        margin-bottom: 6px;
        letter-spacing: -0.01em;
    }}
    h2 {{
        font-size: 11pt;
        font-weight: 700;
        color: #0f172a;
        margin-top: 8px;
        margin-bottom: 4px;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 2px;
    }}
    h3 {{
        font-size: 9.5pt;
        font-weight: 700;
        color: #1e293b;
        margin-top: 6px;
        margin-bottom: 2px;
    }}
    p {{
        margin: 0 0 5px 0;
        text-align: justify;
    }}
    .callout-box-yellow {{
        background-color: #fbfbf2;
        border: 1px solid #ececd5;
        border-left: 3px solid #c9d200;
        border-radius: 3px;
        padding: 6px 10px;
        margin-bottom: 8px;
        font-size: 9pt;
    }}
    .callout-box-dashed {{
        background-color: #ffffff;
        border: 1px dashed #cbd5e1;
        border-radius: 3px;
        padding: 6px 10px;
        margin-bottom: 8px;
        font-style: italic;
        color: #475569;
        font-size: 9pt;
    }}
    ul, ol {{
        margin-top: 2px;
        margin-bottom: 5px;
        padding-left: 18px;
    }}
    li {{
        margin-bottom: 2px;
        text-align: justify;
    }}
    li.numbered {{
        margin-bottom: 2px;
        list-style-type: decimal;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 6px 0 8px 0;
        font-size: 8.5pt;
    }}
    th {{
        background-color: #f8fafc;
        color: #0f172a;
        font-weight: 700;
        border: 1px solid #cbd5e1;
        padding: 4px 6px;
        text-align: left;
    }}
    td {{
        border: 1px solid #cbd5e1;
        padding: 4px 6px;
        vertical-align: top;
    }}
</style>
</head>
<body>
<div class="super-title">HAN · AIBS × AEL — COURSE SITE</div>
{body_html}
</body>
</html>"""

    def _get_unique_pdf_path(self, base_name: str) -> Path:
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

        print("[HandbookAgent] Synthesizing continuous handbook via Ollama...")
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
                    "--enable-local-file-access",
                    "--margin-top", "12mm",
                    "--margin-bottom", "12mm",
                    "--margin-left", "14mm",
                    "--margin-right", "14mm",
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