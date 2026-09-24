import json
import os
import urllib.error
import urllib.request
from pathlib import Path


# Free local model running through Ollama.

MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/chat"
)


class DutchToEnglishAgent:
    """
    Local AI agent that:
    1. translates a Dutch article into English,
    2. simplifies the English to CEFR B1/B2,
    3. reviews the final result against the Dutch original.

    It uses Ollama, so no paid API key is required.
    """

    def __init__(self, model=MODEL):
        self.model = model

    def ask_ai(self, instructions, text):
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": instructions
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        }

        request = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(request) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result["message"]["content"].strip()

        except urllib.error.URLError:
            raise RuntimeError(
                "\nCould not connect to Ollama.\n"
                "Make sure Ollama is installed and running.\n\n"
                "In another WSL terminal, run:\n"
                "    ollama serve\n\n"
                f"Then make sure the model exists:\n"
                f"    ollama pull {self.model}\n"
            )

        except KeyError:
            raise RuntimeError(
                "Ollama returned an unexpected response."
            )

    def translate(self, dutch_article):
        instructions = """
You are the Translator Agent.

Translate the Dutch article into accurate and natural English.

Rules:
- Preserve all important facts, names, dates and numbers.
- Preserve the original meaning.
- Do not summarize.
- Do not add information.
- Do not intentionally simplify the English yet.
- Return only the English translation.
"""
        return self.ask_ai(instructions, dutch_article)

    def simplify(self, english_translation):
        instructions = """
You are the Language Simplifier Agent.

Rewrite the English article so that it is suitable for a CEFR B1/B2 reader.

Rules:
- Keep exactly the same meaning and important information.
- Prefer common and clear vocabulary.
- Use reasonably short sentences.
- Avoid difficult academic vocabulary when a simpler word works.
- Avoid unnecessary idioms and very complex grammar.
- Keep names, dates, numbers and facts unchanged.
- Do not summarize.
- Do not add new information.
- Return only the rewritten English article.
"""
        return self.ask_ai(instructions, english_translation)

    def review(self, dutch_original, simplified_english):
        instructions = """
You are the Reviewer Agent.

Compare the Dutch original article with the proposed B1/B2 English version.

Create the final corrected English article.

Check internally that:
- the meaning of the Dutch original is preserved,
- no important information is missing,
- no information was invented,
- names, dates and numbers are correct,
- the English is natural and grammatically correct,
- the language is approximately CEFR B1/B2,
- difficult words are replaced with simpler alternatives when possible.

IMPORTANT OUTPUT RULES:
- Return ONLY the final corrected English article.
- Do NOT explain your corrections.
- Do NOT provide a checklist.
- Do NOT write headings such as "Final corrected article".
- Use normal English capitalization.
- Do NOT write the article in ALL CAPS.
- Capitalize only the beginning of sentences, proper names and normal acronyms.
"""

        review_input = f"""
DUTCH ORIGINAL:
{dutch_original}

PROPOSED B1/B2 ENGLISH VERSION:
{simplified_english}
"""
        return self.ask_ai(instructions, review_input)

    def run(self, dutch_article):
        if not dutch_article.strip():
            raise ValueError("The article cannot be empty.")

        print("\n[1/3] Translating Dutch article...")
        draft = self.translate(dutch_article)

        print("[2/3] Simplifying to B1/B2 English...")
        simplified = self.simplify(draft)

        print("[3/3] Reviewing the final translation...")
        final = self.review(dutch_article, simplified)

        return {
            "draft_translation": draft,
            "simplified_translation": simplified,
            "final_translation": final,
        }


from pathlib import Path


def read_article():
    print("How would you like to provide the article?")
    print("1 - Paste article")
    print("2 - Load article from articles folder")

    choice = input("\nChoose 1 or 2: ").strip()

    if choice == "1":
        print("\nPaste the Dutch article below.")
        print("When you are finished, type END on a new line.\n")

        lines = []

        while True:
            line = input()

            if line.strip() == "END":
                break

            lines.append(line)

        return "\n".join(lines).strip()

    elif choice == "2":
        articles_folder = Path("articles")

        if not articles_folder.exists():
            raise ValueError(
                "The 'articles' folder does not exist."
            )

        files = list(articles_folder.glob("*.txt"))

        if not files:
            raise ValueError(
                "No .txt files were found in the articles folder."
            )

        print("\nAvailable articles:")

        for i, file in enumerate(files, start=1):
            print(f"{i} - {file.name}")

        file_choice = input("\nChoose an article: ").strip()

        try:
            selected_file = files[int(file_choice) - 1]
        except (ValueError, IndexError):
            raise ValueError("Invalid article selection.")

        with open(selected_file, "r", encoding="utf-8") as file:
            article = file.read()

        if not article.strip():
            raise ValueError("The selected file is empty.")

        print(f"\nLoaded: {selected_file.name}")

        return article.strip()

    else:
        raise ValueError("Please choose 1 or 2.")


def main():
    try:
        article = read_article()

        agent = DutchToEnglishAgent()
        result = agent.run(article)

        print("\n" + "=" * 60)
        print("FINAL B1/B2 ENGLISH ARTICLE")
        print("=" * 60 + "\n")
        print(result["final_translation"])

    except Exception as error:
        print(f"\nError: {error}")


if __name__ == "__main__":
    main()
