from pathlib import Path

from parser.pdf_parser import PDFParser
from parser.text_cleaner import TextCleaner
from parser.section_parser import SectionParser

from graph.enrichers.eligibility import EligibilityExtractor


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

extractor = EligibilityExtractor()

result = extractor.extract(
    policy.sections["Eligibility Criteria"]
)

print(result)