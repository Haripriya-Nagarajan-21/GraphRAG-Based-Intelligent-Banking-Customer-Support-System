from pathlib import Path

from parser.pdf_parser import PDFParser
from parser.text_cleaner import TextCleaner


def main():

    pdf_path = Path("data/policies/Home_Loan_Policy.pdf")

    parser = PDFParser()
    cleaner = TextCleaner()

    raw_text = parser.extract_text(pdf_path)

    cleaned_text = cleaner.clean(raw_text)

    print("=" * 60)
    print("RAW TEXT")
    print("=" * 60)
    print(raw_text[:500])

    print("\n")

    print("=" * 60)
    print("CLEANED TEXT")
    print("=" * 60)
    print(cleaned_text[:500])


if __name__ == "__main__":
    main()