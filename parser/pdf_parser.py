import fitz
from pathlib import Path


class PDFParser:
    """
    Handles extraction of text from banking policy PDFs.
    """

    def __init__(self):
        pass

    def extract_text(self, pdf_path):
        """
        Extract text from a single PDF.

        Parameters
        ----------
        pdf_path : str or Path

        Returns
        -------
        str
            Complete extracted text.
        """

        document = fitz.open(pdf_path)

        full_text = ""

        for page in document:
            full_text += page.get_text()

        document.close()

        return full_text


if __name__ == "__main__":

    parser = PDFParser()

    pdf = Path("data/policies/Home_Loan_Policy.pdf")

    text = parser.extract_text(pdf)

    print(text[:3000])