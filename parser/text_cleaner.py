import re


class TextCleaner:
    """
    Cleans extracted PDF text before section parsing.
    """

    def clean(self, text: str) -> str:

        if not text:
            return ""

        # Normalize line endings
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Replace tabs with spaces
        text = text.replace("\t", " ")

        # Remove page numbers like:
        # Page 1 of 8
        # Page 10 of 25
        text = re.sub(r"Page\s+\d+\s+of\s+\d+", "", text, flags=re.IGNORECASE)

        # Remove repeated spaces
        text = re.sub(r"[ ]{2,}", " ", text)

        # Remove multiple blank lines
        text = re.sub(r"\n{2,}", "\n\n", text)

        # Strip each line
        lines = [line.strip() for line in text.split("\n")]

        # Remove empty lines
        lines = [line for line in lines if line]

        return "\n".join(lines)