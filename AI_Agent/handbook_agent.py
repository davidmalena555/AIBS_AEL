import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional

import markdown

MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")


class HandbookAgent:
    """Agent generating an official academic research handbook in PDF matching HAN template."""

    def __init__(self, input_dir: str = "translated_articles", output_dir: str = "../handbooks", model: str = MODEL):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.model = model

    def _ask_ai(self, instructions: str, context: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": context}
            ],
            "stream": False,
            "options": {"temperature": 0.2, "num_ctx": 16384}
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
            raise RuntimeError("Cannot reach Ollama. Ensure 'ollama serve' is active.")

    def generate_handbook(self, combined_articles_text: str) -> str:
        instructions = """
You are an Applied AI Researcher at HAN University of Applied Sciences.
Synthesize the PROVIDED SOURCE TEXT into an official HAN AIBS x AEL Research Handbook.

CRITICAL REQUIREMENTS:
- Synthesize original, case-specific paragraphs derived strictly from the SOURCE TEXT below.
- Integrate the specific facts, metrics, company details, KPIs, or inventory observations directly into the chapters.
- Preserve all anonymized tokens intact ([Company_1], [CONFIDENTIAL_AMOUNT], [Person_1], [Person_2], etc.).
- Output ONLY valid Markdown.

HANDBOOK STRUCTURE:

# AI for SMEs — Handbook
A living handbook that helps regional manufacturing & wholesale SMEs put AI to work — written by HAN students, one practical question at a time.

This is the handbook's template. The structure is the shell every cohort fills. Content comes from the teams: researched in the AIBS module, and produced through the research platform the same teams build in AEL.

---

# Start here
Write a 3-4 sentence orientation tailored specifically to the problems discussed in the source text (e.g., inventory forecasting, supply chain bottlenecks, or financial ROI). Explain in plain language what this edition covers.

---

# The questions this handbook answers
Create a Markdown table with the relevant themes covered by the source document:
| # | Theme | The SME-facing question |
| 1 | Operational Gaps & Data Realities | [Formulate a specific question based on the text's challenges] |
| 2 | Practical Implementation & ROI | [Formulate a specific question based on the text's use cases] |

---

# Chapter template: Theme 1 — Operational Gaps & Data Realities
*One sentence summarizing what this chapter helps an owner do.*
Team: AIBS Cohort | SME Context: Regional SME Wholesale & Operations | Sources last appraised: October 2026

## 1. The question, for this kind of SME
Narrow down the question using the specific SME bottlenecks found in the source text.

## 2. The translation
Explain the real-world operational problem versus what the owner thinks they need, citing the specific evidence from the source text.

## 3. Illustrative use case (CRISP-DM)
Write a detailed, case-specific breakdown for ALL 6 CRISP-DM stages directly applying the facts from the source text:
- **Business understanding:** The concrete business target (referencing exact retention rates, stockout issues, or cost metrics from the text).
- **Data understanding:** The specific data mentioned or needed (transaction records, order logs, ERP tracking).
- **Data preparation:** Required data cleaning and anonymization before processing.
- **Modelling:** Practical model choice (e.g., time-series forecasting, regression, or automated categorization).
- **Evaluation:** Measuring success against the targets (e.g., reducing implementation days or fulfillment errors).
- **Deployment:** How staff or warehouse managers receive the automated recommendation.

## 4. Recommended tooling
Recommend 2-3 realistic tools (e.g., Power Query, Python script, or ERP connector) with estimated hours and cost.

## 5. Responsible AI & trust
Discuss data security, local anonymization, and GDPR compliance related to this specific case.

## 6. First five steps for an owner
Provide 5 sequential, realistic Monday-morning actions numbered 1 to 5 directly addressing the findings in the text.

## 7. Sources
State the sources evaluated (distinguish between the provided case interview/report and secondary industry benchmarks).

---

# Tooling index
Create a clean Markdown table summarizing tools, use case, estimated effort (hours), and cost.

---

# Regional ecosystem & support
List 2-3 regional Dutch support organizations (e.g., Oost NL, VNO-NCW, HAN Applied Research) and how they can help with this specific adoption challenge.

---

# About this handbook
- **Who writes it:** Students of HAN University of Applied Sciences, in teams, as the integrated task of AIBS and AEL.
- **The quality bar:** Clarity, accuracy against appraised sources, responsible-AI coverage, and usefulness.
- **Educational, not consultancy:** Educational inspiration, not formal business liability.
- **Confidentiality:** Real SME cases are anonymised or published only with consent.
"""
        return self._ask_ai(instructions, combined_articles_text)

    def markdown_to_html(self, md_content: str) -> str:
        body = markdown.markdown(md_content, extensions=["tables", "fenced_code"])
        css = """
        @page {
            size: A4;
            margin: 14mm 14mm 16mm 14mm;
        }
        body {
            font-family: Arial, Helvetica, sans-serif;
            color: #1a1a1a;
            line-height: 1.45;
            font-size: 10.5pt;
        }
        .header-bar {
            border-bottom: 3px solid #005F4B;
            padding-bottom: 6px;
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        .header-title {
            font-size: 8.5pt;
            font-weight: bold;
            color: #005F4B;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        h1 {
            color: #005F4B;
            font-size: 18pt;
            margin-top: 18px;
            margin-bottom: 8px;
            border-bottom: 1.5px solid #E0E0E0;
            padding-bottom: 4px;
        }
        h2 {
            color: #1a1a1a;
            font-size: 13pt;
            margin-top: 14px;
            margin-bottom: 6px;
        }
        h3 {
            font-size: 11pt;
            color: #333333;
            margin-top: 10px;
            margin-bottom: 4px;
        }
        p, li {
            font-size: 10pt;
            color: #2b2b2b;
        }
        ul, ol {
            margin-top: 4px;
            margin-bottom: 10px;
            padding-left: 20px;
        }
        li {
            margin-bottom: 3px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 14px 0;
            font-size: 9.5pt;
        }
        th, td {
            border: 1px solid #D1D5DB;
            padding: 7px 10px;
            text-align: left;
        }
        th {
            background-color: #F3F4F6;
            color: #005F4B;
            font-weight: bold;
        }
        tr:nth-child(even) {
            background-color: #FAFAFA;
        }
        hr {
            border: none;
            border-top: 1px solid #E5E7EB;
            margin: 18px 0;
        }
        """
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{css}</style>
</head>
<body>
<div class="header-bar">
    <span class="header-title">HAN AIBS &times; AEL COURSE SITE</span>
</div>
{body}
</body>
</html>"""

    def _get_unique_pdf_path(self, base_name: str) -> Path:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', base_name).strip('_')
        return self.output_dir / f"{sanitized}_handbook_{timestamp}.pdf"

    def run_test_gate_for_files(self, filenames: List[str]) -> bool:
        """Spustí tester_agent.py striktně pro zadané vybrané soubory."""
        print("\n" + "=" * 60)
        print(f"[Pipeline Gate] Running TesterAgent for {len(filenames)} selected file(s)...")
        print("=" * 60)

        tester_script = Path(__file__).parent / "tester_agent.py"
        cmd = [sys.executable, str(tester_script), "--files"] + filenames
        result = subprocess.run(cmd)

        return result.returncode == 0

    def run(self, source_filename: Optional[str] = None, source_filenames: Optional[List[str]] = None) -> Optional[Path]:
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
                    print("Invalid selection. Defaulting to latest.")
                    target_paths = [max(available_files, key=os.path.getmtime)]

        if not target_paths:
            target_paths = [max(available_files, key=os.path.getmtime)]

        # SPUŠTĚNÍ TESTOVACÍ BRÁNY PRO VYBRANÉ SOUBORY
        selected_file_names = [p.name for p in target_paths]
        gate_passed = self.run_test_gate_for_files(selected_file_names)

        if not gate_passed:
            print("\n" + "!" * 60)
            print("[HandbookAgent] CANCELLED: Selected files did not pass Test Gate.")
            print("!" * 60)
            return None

        print(f"\n[HandbookAgent] Aggregating {len(target_paths)} verified source report(s):")
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
            raise RuntimeError("wkhtmltopdf was not found.")
        finally:
            if os.path.exists(temp_html_path):
                os.remove(temp_html_path)

        return pdf_path