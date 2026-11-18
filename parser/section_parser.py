import re

from parser.policy_document import (
    PolicyDocument,
    Section,
    DocumentCategory,
    DocumentItem
)



class SectionParser:


    def _normalize(self,line):

        # Only strip section numbering if followed by a space and a letter (e.g. "1.3 Eligibility")
        # to avoid stripping decimal percentages like "9.25%"
        line = re.sub(
            r"^\d+\.(?:\d+(?:\.\d+)*)?\s+(?=[a-zA-Z])",
            "",
            line
        )

        return line.strip()



    def parse(
        self,
        text,
        document_name="Unknown Policy",
        document_id="UNKNOWN",
        version="1.0",
        department="Unknown",
        category="Unknown"
    ):


        policy = PolicyDocument(
            document_name,
            document_id,
            version,
            department,
            category
        )


        current_section=None
        current_category=None


        document_categories=[
            "Identity Proof",
            "Address Proof",
            "Income Proof",
            "Property Documents",
            "Passport Size Photographs"
        ]


        main_sections=[
            "Introduction",
            "Purpose",
            "Required Documents",
            "Eligibility Criteria",
            "Loan Amount",
            "Interest Rate",
            "Processing Fee",
            "Loan Tenure",
            "Collateral",
            "KYC",
            "Repayment",
            "Moratorium Period",
            "Frequently Asked Questions"
        ]



        for raw in text.split("\n"):


            line=self._normalize(raw)
            print(f"[{line}]")

            if not line:
                continue



            # MAIN SECTION
            matched = None

            for section in main_sections:
                if line.lower() == section.lower() or line.lower().startswith(section.lower()):
                    matched = section
                    break

            if matched:

                existing = None
                for s in policy.sections:
                    if s.name == matched:
                        existing = s
                        break
                
                if existing:
                    current_section = existing
                else:
                    current_section = Section(
                        name=matched
                    )
                    policy.sections.append(
                        current_section
                    )

                current_category=None


            # DOCUMENT CATEGORY
            elif (
                current_section
                and
                current_section.name=="Required Documents"
                and
                line in document_categories
            ):


                current_category=DocumentCategory(
                    name=line
                )


                current_section.categories.append(
                    current_category
                )



            # BULLET DOCUMENT
            elif line == "•":
                # Ignore bullet-only line.
                continue

            elif current_category:

                invalid_prefix = [
                    "mandatory",
                    "applicable",
                    "for ",
                    "the ",
                    "all ",
                    "identity and",
                    "address verification"
                ]

                if any(line.lower().startswith(x) for x in invalid_prefix):
                    continue

                current_category.documents.append(
                    DocumentItem(name=line)
                )


            else:


                if current_section:

                    current_section.content += (
                        line+"\n"
                    )



        return policy