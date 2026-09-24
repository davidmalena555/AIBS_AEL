# Dutch → B1/B2 English AI Agent

This Python project takes a Dutch article and produces an English version written at approximately CEFR B1/B2 level.

## How the agent works

The program uses three AI roles:

1. **Translator Agent**
   - Translates Dutch into English.
   - Preserves facts, names, dates and numbers.

2. **Language Simplifier Agent**
   - Rewrites the translation into clearer B1/B2 English.
   - Uses simpler vocabulary and sentence structures.

3. **Reviewer Agent**
   - Compares the English version with the Dutch original.
   - Corrects missing information, mistranslations and language that is too difficult.

Flow:

Dutch article
→ Translator
→ B1/B2 Simplifier
→ Reviewer
→ Final English article

## Installation

Open a terminal in this folder and run:

```bash
pip install -r requirements.txt
```

## API key

Create a file called `.env` in this folder.

Add:

```text
OPENAI_API_KEY=your_api_key_here
```

Do not share your API key publicly.

## Run the program

```bash
python dutch_translation_agent.py
```

Paste a Dutch article into the terminal.

When you are finished, type:

```text
END
```

on a new line.

The program will print the final B1/B2 English article.

## Main Python structure

`DutchToEnglishAgent.run()` coordinates the three AI steps:

```text
translate()
    ↓
simplify()
    ↓
review()
```

This makes the workflow easy to explain in a school presentation.
