# AIBS × AEL — quality update

Run from AI_Agent exactly as before:
    python dutch_translation_agent.py
On WSL use your existing python3 command. Ollama, qwen2.5:3b (or OLLAMA_MODEL) and wkhtmltopdf are still required.
Python dependency: pip install -r requirements.txt

## Processing
Input → anonymisation → translation → B1/B2 simplification → review → fidelity check → automatic wiki archive → optional save → existing privacy/readability gate → evidence extraction + support audit → PDF → optional Git publication.

Long text is split into smaller chunks within the same translation/simplification/review stages.
Public names in the explicit allowlist, numeric values and selected sector terms are protected. This is not a general guarantee of de-identification.
The final translation is checked for numbers, placeholders and semantic differences. One repair is attempted; unresolved discrepancies stop processing. A failing or truncated model response is not accepted.

## Source information
Source metadata is extracted from the input's labelled header and kept outside model rewriting.
Translated TXT files include this metadata, followed by the English body.
A matching .source.json stores the safe Dutch comparison text, hashes and validation result.
Keep TXT and .source.json together. Filenames are unique so older results are not overwritten.

IMPORTANT: old translations do not have source sidecars and must be retranslated.
Do not select 0 (all files) if translated_articles still contains old outputs. Select only new validated files by their displayed numbers.
Do not fabricate sidecars or manually mark a failed result PASS.

## Handbook
The model extracts up to three findings per selected source with exact supporting passages.
Python checks the passages, numbers and source identifiers; a separate model audit checks meaning.
Headings, citations, bibliography and the educational proposal are rendered deterministically.
The proposal is explicitly not a researched SME case. Unsupported prices, ROI and regional-service claims are not generated.
Rejected paraphrases are replaced by exact source passages with paragraph context; malformed evidence still blocks output. A passing result produces PDF plus .md and .quality.json for review. A failed output check creates quality_reports/failed_*.json and no PDF.
Quotes in this document are from the English translation, not verbatim quotes from the publisher's original.
Checks reduce errors; model approval is not a guarantee of truth. Review before publishing.

## Wiki
The existing English archive and automatic paired capture remain unchanged.
Only translations that finish the new fidelity check reach the archive.
Its records do not imply a passed handbook gate.
Original input can still contain private data; archive publication is separate.

## Tests
    python test_source_quality.py
Tests use synthetic data under AI_Agent/test_runs and do not call Ollama, create real PDFs or publish.
Real-model regression results for this delivery are in the delivery validation report.

## Compatibility
No OpenAI key or openai/python-dotenv package is needed by these scripts.
Ollama API format=json is used for machine-readable evidence/audit results:
https://docs.ollama.com/api/chat
