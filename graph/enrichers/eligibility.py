import re


class EligibilityExtractor:
    """
    Extracts structured eligibility information from an
    Eligibility Criteria section.

    The extractor does not write to Neo4j.
    It only converts policy text into structured data.
    """

    def extract(self, text):

        if hasattr(text, "content"):
            text = text.content

        if not text:
            return {
                "minimum_age": None,
                "maximum_age": [],
                "employment_types": [],
                "residency": [],
                "credit_scores": [],
                "income_requirements": []
            }

        result = {
            "minimum_age": None,
            "maximum_age": [],
            "employment_types": [],
            "residency": [],
            "credit_scores": [],
            "income_requirements": []
        }

        # =====================================================
        # AGE
        # =====================================================

        # Minimum age
        minimum_patterns = [
            r"minimum\s+age\s*(?:is|:)?\s*(\d+)\s*years?",
            r"at\s+least\s+(\d+)\s*years?",
            r"minimum.*?(\d+)\s*years?"
        ]

        for pattern in minimum_patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE | re.DOTALL
            )

            if match:
                result["minimum_age"] = int(match.group(1))
                break

        # Maximum age
        maximum_patterns = [
            r"maximum\s+age\s*(?:is|:)?\s*(\d+)\s*years?",
            r"maximum.*?(\d+)\s*years?"
        ]

        for pattern in maximum_patterns:

            matches = re.findall(
                pattern,
                text,
                re.IGNORECASE | re.DOTALL
            )

            for age in matches:

                age = int(age)

                if age not in result["maximum_age"]:
                    result["maximum_age"].append(age)

        # =====================================================
        # EMPLOYMENT TYPES
        # =====================================================

        employment_patterns = {
            "Salaried": r"\bsalaried\b",
            "Self-employed": r"\bself[- ]employed\b",
            "Non-Resident Indians": r"\bnon[- ]resident\s+indians\b",
            "NRI": r"\bnris?\b"
        }

        for name, pattern in employment_patterns.items():

            if re.search(
                pattern,
                text,
                re.IGNORECASE
            ):

                if name not in result["employment_types"]:
                    result["employment_types"].append(name)

        # =====================================================
        # RESIDENCY
        # =====================================================

        if re.search(
            r"\bindian\s+citizens?\b",
            text,
            re.IGNORECASE
        ):

            result["residency"].append(
                "Indian Citizen"
            )

        if re.search(
            r"\bnon[- ]resident\s+indians?\b|\bnris?\b",
            text,
            re.IGNORECASE
        ):

            result["residency"].append(
                "NRI"
            )

        # Remove duplicates
        result["residency"] = list(
            dict.fromkeys(result["residency"])
        )

        # =====================================================
        # CREDIT SCORE
        # =====================================================

        score_patterns = [
            r"credit\s+score.*?(\d{3})",
            r"cibil\s+score.*?(\d{3})",
            r"cibil.*?(\d{3})"
        ]

        for pattern in score_patterns:

            matches = re.findall(
                pattern,
                text,
                re.IGNORECASE | re.DOTALL
            )

            for score in matches:

                score = int(score)

                if score not in result["credit_scores"]:
                    result["credit_scores"].append(score)

        # =====================================================
        # INCOME REQUIREMENTS
        # =====================================================

        income_patterns = [
            r"₹\s*[\d,]+\s*(?:per\s+month|monthly)",
            r"₹\s*[\d,]+\s*(?:per\s+year|annually)",
            r"minimum\s+income.*?(?:₹\s*[\d,]+)"
        ]

        for pattern in income_patterns:

            matches = re.findall(
                pattern,
                text,
                re.IGNORECASE
            )

            for income in matches:

                income = income.strip()

                if income not in result["income_requirements"]:
                    result["income_requirements"].append(
                        income
                    )

        return result