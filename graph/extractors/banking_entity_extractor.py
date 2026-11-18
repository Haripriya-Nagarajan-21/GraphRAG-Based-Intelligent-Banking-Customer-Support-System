import re

from graph.models.entity import Entity
from graph.models.relationship import Relationship


class BankingEntityExtractor:

    def extract(self, policy):

        entities = []
        relationships = []

        # -----------------------------------------
        # Policy Node
        # -----------------------------------------

        entities.append(
            Entity(
                entity_type="Policy",
                name=policy.document_name,
                value=policy.document_id
            )
        )

        # -----------------------------------------
        # Sections
        # -----------------------------------------

        for section_name, content in policy.sections.items():

            entities.append(
                Entity(
                    entity_type="Section",
                    name=section_name,
                    value=content
                )
            )

            relationships.append(
                Relationship(
                    source=policy.document_name,
                    relation="HAS_SECTION",
                    target=section_name
                )
            )

            self._extract_from_section(
                section_name,
                content,
                entities,
                relationships
            )

        return entities, relationships

    # -----------------------------------------------------

    def _extract_from_section(
            self,
            section,
            text,
            entities,
            relationships
    ):

        # ==============================================
        # Required Documents
        # ==============================================

        if "document" in section.lower():

            docs = [
                "Aadhaar",
                "PAN",
                "Passport",
                "Visa",
                "Salary Slip",
                "Bank Statement",
                "Admission Letter",
                "Academic Records",
                "Income Proof",
                "Address Proof",
                "Identity Proof",
                "Collateral Documents"
            ]

            for doc in docs:

                if doc.lower() in text.lower():

                    entities.append(
                        Entity(
                            "Document",
                            doc
                        )
                    )

                    relationships.append(
                        Relationship(
                            section,
                            "REQUIRES_DOCUMENT",
                            doc
                        )
                    )

        # ==============================================
        # Interest Rate
        # ==============================================

        if "interest" in section.lower():

            rates = re.findall(
                r"\d+\.\d+%",
                text
            )

            for rate in rates:

                entities.append(
                    Entity(
                        "InterestRate",
                        rate
                    )
                )

                relationships.append(
                    Relationship(
                        section,
                        "HAS_INTEREST_RATE",
                        rate
                    )
                )

        # ==============================================
        # Loan Amount
        # ==============================================

        if "loan amount" in section.lower():

            amounts = re.findall(
                r"₹[\d.,]+\s*(?:Lakhs?|Crores?)?",
                text
            )

            for amount in amounts:

                entities.append(
                    Entity(
                        "LoanAmount",
                        amount
                    )
                )

                relationships.append(
                    Relationship(
                        section,
                        "HAS_LOAN_AMOUNT",
                        amount
                    )
                )

        # ==============================================
        # Eligibility
        # ==============================================

        if "eligibility" in section.lower():

            ages = re.findall(
                r"\d+\s*years",
                text,
                re.I
            )

            for age in ages:

                entities.append(
                    Entity(
                        "Age",
                        age
                    )
                )

                relationships.append(
                    Relationship(
                        section,
                        "HAS_AGE",
                        age
                    )
                )

            if "NRI" in text:

                entities.append(
                    Entity(
                        "EmploymentType",
                        "NRI"
                    )
                )

                relationships.append(
                    Relationship(
                        section,
                        "HAS_EMPLOYMENT_TYPE",
                        "NRI"
                    )
                )

            if "Salaried" in text:

                entities.append(
                    Entity(
                        "EmploymentType",
                        "Salaried"
                    )
                )

                relationships.append(
                    Relationship(
                        section,
                        "HAS_EMPLOYMENT_TYPE",
                        "Salaried"
                    )
                )

            if "Self-employed" in text:

                entities.append(
                    Entity(
                        "EmploymentType",
                        "Self-employed"
                    )
                )

                relationships.append(
                    Relationship(
                        section,
                        "HAS_EMPLOYMENT_TYPE",
                        "Self-employed"
                    )
                )