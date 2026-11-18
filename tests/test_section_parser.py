from pathlib import Path

from parser.pdf_parser import PDFParser
from parser.text_cleaner import TextCleaner
from parser.section_parser import SectionParser


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

    print("=" * 70)
    print("POLICY INFORMATION")
    print("=" * 70)

    print("Document Name :", policy.document_name)
    print("Document ID   :", policy.document_id)
    print("Version       :", policy.version)
    print("Department    :", policy.department)
    print("Category      :", policy.category)

    print("\n")

    print("=" * 70)
    print("SECTIONS FOUND")
    print("=" * 70)

    for section in policy.sections:
        print(section)

    print("\n")

    print("=" * 70)
    print("ELIGIBILITY SECTION")
    print("=" * 70)

    print(policy.sections.get("Eligibility Criteria", "Not Found"))


if __name__ == "__main__":
    main()