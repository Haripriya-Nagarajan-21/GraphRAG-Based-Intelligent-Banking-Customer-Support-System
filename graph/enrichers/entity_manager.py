import re

from graph.enrichers.eligibility import EligibilityExtractor


class BankingEntityManager:
    """
    Central entity extraction manager.

    Responsible only for extracting structured entities
    from policy sections.

    It does NOT communicate with Neo4j.
    """

    def __init__(self):

        self.eligibility_extractor = EligibilityExtractor()

    # ==========================================================
    # PUBLIC METHOD
    # ==========================================================

    def extract(self, section_name, text):

        if not text:
            return []

        section = section_name.strip().lower()

        entities = []

        # ------------------------------------------------------
        # Eligibility
        # ------------------------------------------------------

        if "eligibility" in section:

            entities.extend(
                self._extract_eligibility(text)
            )

        # ------------------------------------------------------
        # Interest Rate
        # ------------------------------------------------------

        if "interest" in section:

            entities.extend(
                self._extract_interest_rate(text)
            )

        # ------------------------------------------------------
        # Loan Amount
        # ------------------------------------------------------

        if "loan amount" in section:

            entities.extend(
                self._extract_loan_amount(text)
            )

        # ------------------------------------------------------
        # Processing Fee
        # ------------------------------------------------------

        if "processing fee" in section:

            entities.extend(
                self._extract_percentage(
                    text,
                    "ProcessingFee"
                )
            )

        # ------------------------------------------------------
        # Loan Tenure
        # ------------------------------------------------------

        if "loan tenure" in section:

            entities.extend(
                self._extract_tenure(text)
            )

        # ------------------------------------------------------
        # Collateral
        # ------------------------------------------------------

        if "collateral" in section:

            entities.extend(
                self._extract_collateral(text)
            )

        # ------------------------------------------------------
        # KYC
        # ------------------------------------------------------

        if section == "kyc" or section.startswith("kyc"):

            entities.extend(
                self._extract_kyc(text)
            )

        # Remove duplicate entities
        return self._remove_duplicates(entities)

    # ==========================================================
    # ELIGIBILITY
    # ==========================================================

    def _extract_eligibility(self, text):

        data = self.eligibility_extractor.extract(text)

        entities = []

        # Minimum age
        if data["minimum_age"] is not None:

            entities.append({
                "type": "MinimumAge",
                "value": data["minimum_age"],
                "unit": "years"
            })

        # Maximum age
        for age in data["maximum_age"]:

            entities.append({
                "type": "MaximumAge",
                "value": age,
                "unit": "years"
            })

        # Employment types
        for employment in data["employment_types"]:

            entities.append({
                "type": "EmploymentType",
                "value": employment
            })

        # Residency
        for residency in data["residency"]:

            entities.append({
                "type": "Residency",
                "value": residency
            })

        # Credit score
        for score in data["credit_scores"]:

            entities.append({
                "type": "CreditScore",
                "value": score
            })

        # Income
        for income in data["income_requirements"]:

            entities.append({
                "type": "IncomeRequirement",
                "value": income
            })

        return entities

    # ==========================================================
    # INTEREST RATE
    # ==========================================================

    def _extract_interest_rate(self, text):

        entities = []

        # Rate ranges such as:
        # 8.50% - 9.25%
        # 9.10%–9.50%
        ranges = re.findall(
            r"(\d+(?:\.\d+)?)\s*%\s*[-–]\s*(\d+(?:\.\d+)?)\s*%",
            text
        )

        for minimum, maximum in ranges:

            entities.append({
                "type": "InterestRate",
                "min_rate": float(minimum),
                "max_rate": float(maximum)
            })

        # Individual percentages
        percentages = re.findall(
            r"(?<![\d.])(\d+(?:\.\d+)?)\s*%",
            text
        )

        for rate in percentages:

            value = float(rate)

            # Don't duplicate values already represented
            # by a range.
            already_exists = any(
                e.get("min_rate") == value
                or e.get("max_rate") == value
                for e in entities
            )

            if not already_exists:

                entities.append({
                    "type": "InterestRate",
                    "value": value
                })

        return entities

    # ==========================================================
    # LOAN AMOUNT
    # ==========================================================

    def _extract_loan_amount(self, text):

        entities = []

        amounts = re.findall(
            r"₹\s*[\d,]+(?:\.\d+)?\s*(?:Lakhs?|Crores?)?",
            text,
            re.IGNORECASE
        )

        for amount in amounts:

            entities.append({
                "type": "LoanAmount",
                "value": amount.strip()
            })

        return entities

    # ==========================================================
    # GENERIC PERCENTAGE
    # ==========================================================

    def _extract_percentage(self, text, entity_type):

        entities = []

        percentages = re.findall(
            r"(\d+(?:\.\d+)?)\s*%",
            text
        )

        for value in percentages:

            entities.append({
                "type": entity_type,
                "value": float(value)
            })

        return entities

    # ==========================================================
    # LOAN TENURE
    # ==========================================================

    def _extract_tenure(self, text):

        entities = []

        matches = re.findall(
            r"\b\d+\s*(?:years?|months?)\b",
            text,
            re.IGNORECASE
        )

        for tenure in matches:

            entities.append({
                "type": "LoanTenure",
                "value": tenure.strip()
            })

        return entities

    # ==========================================================
    # COLLATERAL
    # ==========================================================

    def _extract_collateral(self, text):

        entities = []

        if re.search(
            r"\bnot\s+required\b|\bno\s+collateral\b",
            text,
            re.IGNORECASE
        ):

            entities.append({
                "type": "Collateral",
                "status": "Not Required"
            })

        elif re.search(
            r"\brequired\b",
            text,
            re.IGNORECASE
        ):

            entities.append({
                "type": "Collateral",
                "status": "Required"
            })

        return entities

    # ==========================================================
    # KYC
    # ==========================================================

    def _extract_kyc(self, text):

        entities = []

        documents = [
            "Aadhaar",
            "PAN",
            "Passport",
            "Driving Licence",
            "Voter ID"
        ]

        lower_text = text.lower()

        for document in documents:

            if document.lower() in lower_text:

                entities.append({
                    "type": "KYCDocument",
                    "value": document
                })

        return entities

    # ==========================================================
    # DUPLICATE REMOVAL
    # ==========================================================

    def _remove_duplicates(self, entities):

        unique = []
        seen = set()

        for entity in entities:

            key = (
                entity.get("type"),
                tuple(
                    sorted(
                        entity.items()
                    )
                )
            )

            if key not in seen:

                seen.add(key)
                unique.append(entity)

        return unique