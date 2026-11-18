from pathlib import Path

from parser.pdf_parser import PDFParser
from parser.text_cleaner import TextCleaner
from parser.section_parser import SectionParser

from graph.entity_extractor import EntityExtractor


def main():

    pdf = PDFParser()
    cleaner = TextCleaner()
    parser = SectionParser()
    extractor = EntityExtractor()

    text = pdf.extract_text(
        Path("data/policies/Home_Loan_Policy.pdf")
    )

    cleaned = cleaner.clean(text)

    policy = parser.parse(
        cleaned,
        document_name="Home Loan Policy",
        document_id="HLP-001",
        version="1.0",
        department="Retail Banking",
        category="Lending Policy"
    )

    entities = extractor.extract(policy)

    print("=" * 60)
    print("EXTRACTED ENTITIES")
    print("=" * 60)

    for entity in entities:
        print(entity)


if __name__ == "__main__":
    main()