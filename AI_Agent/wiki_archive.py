"""Local snapshots only. No models, network requests, Git operations or agent imports."""
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import uuid

STYLE = """
body{font:16px/1.6 system-ui,sans-serif;margin:0;background:#f3f5f4;color:#172c28}
main{max-width:1200px;margin:auto;padding:32px}h1{line-height:1.2}
header,article,.notice{background:white;border:1px solid #d9e2dd;border-radius:12px;padding:24px;margin-bottom:20px}
a{color:#006650}small{color:#53645e}input{font:inherit;padding:12px;width:min(90%,600px)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.7 system-ui;margin:0}
.badge{font-size:12px;background:#eaf0cc;padding:4px 8px;border-radius:6px}
@media(max-width:750px){.grid{grid-template-columns:1fr}main{padding:16px}}
"""
SCRIPT = """
const input=document.getElementById('search');
if(input) input.addEventListener('input',()=>{
 const term=input.value.toLocaleLowerCase();
 document.querySelectorAll('article').forEach(card=>{
  card.hidden=!card.textContent.toLocaleLowerCase().includes(term);
 });
});
"""


def document(title, body, script=False):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            'style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
            f'<title>{html.escape(title)}</title><style>{STYLE}</style></head><body><main>'
            + body + '</main>' + (f'<script>{SCRIPT}</script>' if script else '') + '</body></html>')


def atomic_text(path, text):
    temp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('x', encoding='utf-8', newline='') as stream:
            stream.write(text)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def rebuild_index(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    cards = []
    for folder in sorted(root.iterdir(), reverse=True):
        if not folder.is_dir() or folder.name.startswith('.'):
            continue
        # Folder names are generated IDs, never source-controlled filenames.
        if not all(c.isalnum() or c in '-_' for c in folder.name):
            continue
        try:
            record = json.loads((folder / 'record.json').read_text(encoding='utf-8'))
            if not (folder / 'index.html').is_file():
                continue
            title = html.escape(str(record['title']))
            created = html.escape(str(record['created_utc']))
            model = html.escape(str(record['model']))
        except (OSError, ValueError, KeyError, TypeError):
            continue
        cards.append(f'<article><span class="badge">Automatic record · unreviewed</span>'
                     f'<h2><a href="{folder.name}/index.html">{title}</a></h2>'
                     f'<small>{created} · model {model}</small><p>'
                     f'<a href="{folder.name}/input-nl.txt">Dutch input</a> · '
                     f'<a href="{folder.name}/translation-en.txt">English translation</a> · '
                     f'<a href="{folder.name}/record.json">Metadata</a></p></article>')
    body = ('<header><p>AIBS × AEL / LLM wiki</p><h1>Translation archive</h1>'
            '<p>Each completed translation has its own record: input and output side by side.</p>'
            '<input id="search" type="search" placeholder="Search by title, date or model…" aria-label="Search records">'
            f'<p>Number of records: {len(cards)}</p></header>'
            '<div class="notice">Local archive, not approved research evidence. '
            'The original input may contain personal data. Records are created before the handbook '
            'test gate and do not confirm that it passed. A translation is not an independent source. '
            'Use public source material for public demonstrations.</div>'
            + (''.join(cards) if cards else '<article>No translations yet. Run the program as usual, then refresh this page.</article>'))
    atomic_text(root / 'index.html', document('Translation archive — LLM wiki', body, True))
    return root / 'index.html'


def archive_translation(dutch_text, english_text, *, model, wiki_root=None):
    if not isinstance(dutch_text, str) or not isinstance(english_text, str):
        raise ValueError('Archive expects two text strings')
    if not dutch_text.strip() or not english_text.strip():
        raise ValueError('Cannot archive an empty input or translation')
    wiki_root = Path(wiki_root) if wiki_root is not None else Path(__file__).resolve().parent.parent / 'LLM_Wiki'
    root = wiki_root.resolve() / 'pipeline_archive'
    root.mkdir(parents=True, exist_ok=True)
    created = dt.datetime.now(dt.timezone.utc)
    run_id = created.strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex
    pending = root / ('.pending-' + run_id)
    destination = root / run_id
    pending.mkdir()
    title = next(line.strip() for line in dutch_text.splitlines() if line.strip())[:160]
    record = {
        'schema_version': 1, 'run_id': run_id, 'title': title,
        'created_utc': created.isoformat(), 'model': str(model),
        'status': 'unreviewed-pipeline-output',
        'input_scope': 'Exact text supplied to the run method, before anonymization; not original file bytes',
        'original_filename': None,
        'source_author': None, 'source_url_verified': False,
        'translation_scope': 'Final reviewed English text returned by the existing translation pipeline',
        'handbook_test_gate': 'not evaluated at archive time',
        'files': {
            'input-nl.txt': hashlib.sha256(dutch_text.encode('utf-8')).hexdigest(),
            'translation-en.txt': hashlib.sha256(english_text.encode('utf-8')).hexdigest(),
        },
    }
    # Write once inside an invisible staging directory; publish only a complete pair.
    for name, content in [('input-nl.txt', dutch_text), ('translation-en.txt', english_text),
                          ('record.json', json.dumps(record, ensure_ascii=False, indent=2) + '\n')]:
        with (pending / name).open('x', encoding='utf-8', newline='') as stream:
            stream.write(content)
    body = (f'<header><a href="../index.html">← All translations</a><h1>{html.escape(title)}</h1>'
            f'<small>{html.escape(record["created_utc"])} · {html.escape(str(model))}</small>'
            '<p><span class="badge">Unreviewed archive record</span></p>'
            '<p>The Dutch text is the input before anonymisation. The English text is derived output from the agents. '
            'This record does not confirm a passed handbook test or factual accuracy.</p>'
            '<p><a href="record.json">Metadata and SHA-256</a></p></header>'
            '<div class="grid"><article><h2>Dutch input</h2><p><a href="input-nl.txt">Open TXT</a></p>'
            f'<pre>{html.escape(dutch_text)}</pre></article>'
            '<article><h2>English translation</h2><p><a href="translation-en.txt">Open TXT</a></p>'
            f'<pre>{html.escape(english_text)}</pre></article></div>')
    with (pending / 'index.html').open('x', encoding='utf-8', newline='') as stream:
        stream.write(document(title, body))
    pending.rename(destination)
    try:
        rebuild_index(root)
    except OSError as exc:
        # The complete record remains usable even if the overview cannot be replaced.
        print(f'[WikiArchive] Pair saved, overview update failed: {exc}')
    return destination / 'index.html'


if __name__ == '__main__':
    target = Path(__file__).resolve().parent.parent / 'LLM_Wiki' / 'pipeline_archive'
    print(rebuild_index(target))

