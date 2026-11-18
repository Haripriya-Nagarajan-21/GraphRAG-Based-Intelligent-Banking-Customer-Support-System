from pathlib import Path

from parser.pdf_parser import PDFParser
from parser.text_cleaner import TextCleaner
from parser.section_parser import SectionParser

from graph.graph_builder import GraphBuilder


def main():

    pdf = PDFParser()
    cleaner = TextCleaner()
    parser = SectionParser()

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

    builder = GraphBuilder()

    builder.build(policy)

    builder.close()


if __name__ == "__main__":
    main()