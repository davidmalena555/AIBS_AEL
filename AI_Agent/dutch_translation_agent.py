import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from file_saver_agent import FileSaverAgent
from handbook_agent import HandbookAgent

# Free local model running through Ollama.
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/chat"
)


class DutchToEnglishAgent:
    """
    Local AI agent that:
    1. Anonymizes PII locally in Python (GDPR compliance),
    2. Translates the Dutch article into English,
    3. Simplifies the English to CEFR B1/B2,
    4. Reviews the final result against the Dutch original.
    """

    def __init__(self, model=MODEL):
        self.model = model

    def anonymize_text(self, text: str) -> str:

        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', text)

        currency_pattern = (
            r'(?:€|\$|£|CZK|EUR|USD)\s*\d+(?:[\.,\s]\d+)*(?:\s*(?:miljoen|miljard|million|billion|k))?'
            r'|\d+(?:[\.,\s]\d+)*\s*(?:€|\$|£|CZK|EUR|USD|euro|dollar|korun)'
            r'(?:\s*(?:per\s+(?:maand|jaar|kwartaal|uur)|bruto|netto))?'
        )
        text = re.sub(currency_pattern, '[CONFIDENTIAL_AMOUNT]', text, flags=re.IGNORECASE)

        phone_pattern = r'(?:\+\d{1,3}[\s-]?)?\(?0?\d{1,4}\)?[\s.-]?\d{3}[\s.-]?\d{3,4}\b'
        text = re.sub(phone_pattern, '[REDACTED_PHONE]', text)

        company_pattern = (
            r'\b(?:[A-Z][a-zA-Z0-9&]*\s+){1,3}'
            r'(?:B\.V\.|N\.V\.|BV|NV|Ltd\.?|LLC|Inc\.?|Corp\.?|GmbH|Group|Holdings|Solutions|Logistics|Bank\s+N\.V\.)\b'
        )
        companies_found = sorted(set(re.findall(company_pattern, text)), key=len, reverse=True)
        for idx, comp in enumerate(companies_found, start=1):
            text = text.replace(comp.strip(), f"[Company_{idx}]")

        job_titles_pattern = r'\b(?:Project\s+Manager|Projectmanager|General\s+Director|Directeur|Analist|Manager|Officer)\s+'
        text = re.sub(job_titles_pattern, '', text, flags=re.IGNORECASE)

        name_pattern = r'\b[A-Z][a-z]+(?:\s+(?:van|der|den|de|het|ten|ter|von)\b)?\s+[A-Z][a-z]+\b'
        names_found = set(re.findall(name_pattern, text))

        person_idx = 1
        for name in names_found:
            if not any(tag in name for tag in ["[Company_", "[CONFIDENTIAL_", "[REDACTED_"]):
                text = text.replace(name, f"[Person_{person_idx}]")
                person_idx += 1

        return text
    
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
Translate the Dutch article into accurate, clear English.
Keep all placeholders like [Person_1], [Company_1], [CONFIDENTIAL_AMOUNT], [REDACTED_EMAIL], [REDACTED_PHONE] exactly as they are.
Preserve facts, context, dates, and numbers.
Return ONLY the English translation.
"""
        return self.ask_ai(instructions, dutch_article)

    def simplify(self, english_translation):
        instructions = """
You are the Language Simplifier Agent.
Rewrite the English article so that it is suitable for a CEFR B1/B2 reader.
Rules:
- Keep all placeholders like [Person_1], [Company_1], [CONFIDENTIAL_AMOUNT] unchanged.
- Prefer common and clear vocabulary.
- Use reasonably short sentences.
- Avoid unnecessary idioms and complex syntax.
- Do not summarize or delete important facts.
- Return ONLY the rewritten English article.
"""
        return self.ask_ai(instructions, english_translation)

    def review(self, anonymized_dutch, simplified_english):
        instructions = """
You are the Reviewer Agent.
Compare the Dutch text with the proposed B1/B2 English version.
Create the final corrected English article.
Rules:
- Ensure all placeholders like [Person_1], [Company_1], [CONFIDENTIAL_AMOUNT] are strictly preserved.
- Verify that the meaning is preserved and facts are correct.
- Ensure the language is approximately CEFR B1/B2.
- Return ONLY the final corrected English article without explanations.
"""
        review_input = f"""
DUTCH ORIGINAL:
{anonymized_dutch}

PROPOSED B1/B2 ENGLISH VERSION:
{simplified_english}
"""
        response = self.ask_ai(instructions, review_input)

        cleaned_response = re.sub(r"^(Here's|Here is).*?:\s*", "", response, flags=re.IGNORECASE).strip()
        
        return cleaned_response

    def run(self, raw_dutch_article):
        if not raw_dutch_article.strip():
            raise ValueError("The article cannot be empty.")

        # Fáze 0: Deterministická GDPR anonymizace
        print("\n[0/3] Applying GDPR pre-processing...")
        safe_dutch = self.anonymize_text(raw_dutch_article)

        print("[1/3] Translating Dutch article...")
        draft = self.translate(safe_dutch)

        print("[2/3] Simplifying to B1/B2 English...")
        simplified = self.simplify(draft)

        print("[3/3] Reviewing the final translation...")
        final = self.review(safe_dutch, simplified)

        return {
            "draft_translation": draft,
            "simplified_translation": simplified,
            "final_translation": final,
        }


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
            raise ValueError("The 'articles' folder does not exist.")

        files = list(articles_folder.glob("*.txt"))
        if not files:
            raise ValueError("No .txt files were found in the articles folder.")

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
        final_text = result["final_translation"]

        print("\n" + "=" * 60)
        print("FINAL B1/B2 ENGLISH ARTICLE")
        print("=" * 60 + "\n")
        print(final_text)

        saved_file_name = None

        print("\n" + "-" * 60)
        save_choice = input("Do you want to save this translation to a file? (Y/N): ").strip().upper()

        if save_choice == "Y":
            saver = FileSaverAgent(output_dir="translated_articles")
            saved_path = saver.save(final_text)
            saved_file_name = saved_path.name
            print(f"[FileSaverAgent] Translation successfully saved to: {saved_path}")
        else:
            print("Action skipped. Translation was not saved.")

        print("\n" + "-" * 60)
        handbook_choice = input("Do you want HandbookAgent to create a Handbook from this? (Y/N): ").strip().upper()

        if handbook_choice == "Y":
            hb_agent = HandbookAgent(input_dir="translated_articles", output_dir="handbooks")
            hb_path = hb_agent.run(source_filename=saved_file_name)
            print(f"[HandbookAgent] Handbook successfully created: {hb_path}")
        else:
            print("Action skipped. Handbook was not created.")

    except Exception as error:
        print(f"\nError: {error}")


if __name__ == "__main__":
    main()