import re

from neo4j import GraphDatabase

from config import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD
)

from graph.enrichers.entity_manager import BankingEntityManager


class GraphBuilder:

    def __init__(self):

        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(
                NEO4J_USER,
                NEO4J_PASSWORD
            )
        )

        self.driver.verify_connectivity()

        self.entity_manager = BankingEntityManager()

        print("Neo4j Connected")

    # ==========================================================
    # CLOSE
    # ==========================================================

    def close(self):

        self.driver.close()

    # ==========================================================
    # MAIN GRAPH BUILDER
    # ==========================================================

    def build(self, policy):

        with self.driver.session() as session:

            # --------------------------------------------------
            # 1. POLICY
            # --------------------------------------------------

            session.run(
                """
                MERGE (p:Policy {id:$id})

                SET
                    p.name=$name,
                    p.version=$version,
                    p.department=$department,
                    p.category=$category,
                    p.source="PDF",
                    p.status="Active",
                    p.last_updated=date(),
                    p.bank="Sample Bank"
                """,

                id=policy.document_id,
                name=policy.document_name,
                version=policy.version,
                department=policy.department,
                category=policy.category
            )

            # --------------------------------------------------
            # 2. LOAN
            # --------------------------------------------------

            loan_name = policy.document_name.replace(
                "Policy",
                ""
            ).strip()

            session.run(
                """
                MATCH (p:Policy {id:$policy_id})

                MERGE (l:Loan {name:$loan_name})

                MERGE (p)-[:HAS_LOAN]->(l)
                """,

                policy_id=policy.document_id,
                loan_name=loan_name
            )

            # --------------------------------------------------
            # 3. CATEGORY
            # --------------------------------------------------

            session.run(
                """
                MATCH (p:Policy {id:$policy_id})
                MATCH (p)-[:HAS_LOAN]->(l)

                MERGE (c:Category {
                    name:$category
                })

                MERGE (c)-[:HAS_LOAN]->(l)
                """,

                policy_id=policy.document_id,
                category=policy.category
            )

            # --------------------------------------------------
            # 4. SECTIONS
            # --------------------------------------------------

            for section in policy.sections:

                section_id = (
                    f"{policy.document_id}_"
                    f"{section.name}"
                )

                # ----------------------------------------------
                # Create Section
                # ----------------------------------------------

                session.run(
                    """
                    MATCH (p:Policy {id:$policy_id})
                    MATCH (p)-[:HAS_LOAN]->(l)

                    MERGE (s:Section {
                        id:$section_id
                    })

                    SET
                        s.name=$section_name,
                        s.content=$content,
                        s.policy_id=$policy_id

                    MERGE (l)-[:HAS_SECTION]->(s)
                    """,

                    policy_id=policy.document_id,
                    section_id=section_id,
                    section_name=section.name,
                    content=section.content
                )

                # ----------------------------------------------
                # Required Documents
                # ----------------------------------------------

                self._create_document_hierarchy(
                    session,
                    policy.document_id,
                    section
                )

                # ----------------------------------------------
                # Entity Extraction
                # ----------------------------------------------

                self._enrich_section(
                    session,
                    section_id,
                    section.name,
                    section.content
                )

        # ------------------------------------------------------
        # GRAPH STATISTICS
        # ------------------------------------------------------

        with self.driver.session() as session:

            nodes = session.run(
                """
                MATCH (n)
                RETURN count(n) AS total
                """
            ).single()["total"]

            relationships = session.run(
                """
                MATCH ()-[r]->()
                RETURN count(r) AS total
                """
            ).single()["total"]

        print("=" * 60)
        print("Knowledge Graph Built Successfully!")
        print(f"Total Nodes         : {nodes}")
        print(f"Total Relationships : {relationships}")
        print("=" * 60)

    # ==========================================================
    # DOCUMENT HIERARCHY
    # ==========================================================

    def _create_document_hierarchy(
        self,
        session,
        policy_id,
        section
    ):

        if section.name != "Required Documents":
            return

        section_id = (
            f"{policy_id}_"
            f"{section.name}"
        )

        for category in section.categories:

            category_id = (
                f"{policy_id}_"
                f"{category.name}"
            )

            # --------------------------------------------------
            # Document Category
            # --------------------------------------------------

            session.run(
                """
                MATCH (s:Section {
                    id:$section_id
                })

                MERGE (c:DocumentCategory {
                    id:$category_id
                })

                SET
                    c.name=$name,
                    c.policy_id=$policy_id

                MERGE
                    (s)-[:HAS_SUBSECTION]->(c)
                """,

                section_id=section_id,
                category_id=category_id,
                name=category.name,
                policy_id=policy_id
            )

            # --------------------------------------------------
            # Documents
            # --------------------------------------------------

            for doc in category.documents:

                doc_name = doc.name.strip()

                if not doc_name:
                    continue

                # Make document identity policy/category specific
                document_id = (
                    f"{policy_id}_"
                    f"{category.name}_"
                    f"{doc_name}"
                )

                session.run(
                    """
                    MATCH (s:Section {
                        id:$section_id
                    })

                    MATCH
                        (s)-[:HAS_SUBSECTION]->
                        (c:DocumentCategory {
                            id:$category_id
                        })

                    MATCH
                        (l:Loan)-[:HAS_SECTION]->
                        (s)

                    MERGE (d:Document {
                        id:$document_id
                    })

                    SET
                        d.name=$doc_name,
                        d.category=$category_name,
                        d.policy_id=$policy_id

                    MERGE
                        (c)-[:REQUIRES_DOCUMENT]->(d)

                    MERGE
                        (d)-[:USED_IN]->(l)
                    """,

                    section_id=section_id,
                    category_id=category_id,
                    document_id=document_id,
                    doc_name=doc_name,
                    category_name=category.name,
                    policy_id=policy_id
                )

        # ------------------------------------------------------
        # Debug
        # ------------------------------------------------------

        print("=" * 50)
        print("DOCUMENT HIERARCHY")
        print("=" * 50)

        for category in section.categories:

            print("CATEGORY:", category.name)

            for doc in category.documents:
                print("DOC:", repr(doc.name))

    # ==========================================================
    # ENTITY EXTRACTION
    # ==========================================================

    def _enrich_section(
        self,
        session,
        section_id,
        section_name,
        text
    ):

        """
        Extract general entities and create structured
        Neo4j relationships.

        Special structured sections such as:
        - Interest Rate
        - Loan Amount
        - Collateral

        are handled separately.
        """

        # ------------------------------------------------------
        # SPECIAL STRUCTURED SECTIONS
        # ------------------------------------------------------

        if section_name == "Interest Rate":

            self._build_interest_rates(
                session,
                section_id,
                text
            )

            return

        if section_name == "Loan Amount":

            self._build_loan_amounts(
                session,
                section_id,
                text
            )

            return

        if section_name == "Collateral":

            self._build_collateral_rules(
                session,
                section_id,
                text
            )

            return

        # ------------------------------------------------------
        # GENERAL ENTITY EXTRACTION
        # ------------------------------------------------------

        entities = self.entity_manager.extract(
            section_name,
            text
        )

        if not entities:
            return

        for entity in entities:

            entity_type = entity.get("type")

            # --------------------------------------------------
            # MINIMUM AGE
            # --------------------------------------------------

            if entity_type == "MinimumAge":

                session.run(
                    """
                    MATCH (s:Section {
                        id:$section_id
                    })

                    MERGE (a:MinimumAge {
                        section_id:$section_id,
                        value:$value
                    })

                    SET
                        a.unit=$unit

                    MERGE
                        (s)-[:HAS_MINIMUM_AGE]->(a)
                    """,

                    section_id=section_id,
                    value=entity["value"],
                    unit=entity.get("unit")
                )

            # --------------------------------------------------
            # MAXIMUM AGE
            # --------------------------------------------------

            elif entity_type == "MaximumAge":

                session.run(
                    """
                    MATCH (s:Section {
                        id:$section_id
                    })

                    MERGE (a:MaximumAge {
                        section_id:$section_id,
                        value:$value
                    })

                    SET
                        a.unit=$unit

                    MERGE
                        (s)-[:HAS_MAXIMUM_AGE]->(a)
                    """,

                    section_id=section_id,
                    value=entity["value"],
                    unit=entity.get("unit")
                )

            # --------------------------------------------------
            # EMPLOYMENT TYPE
            # --------------------------------------------------

            elif entity_type == "EmploymentType":

                session.run(
                    """
                    MATCH (s:Section {
                        id:$section_id
                    })

                    MERGE (e:EmploymentType {
                        section_id:$section_id,
                        name:$name
                    })

                    MERGE
                        (s)-[:HAS_EMPLOYMENT_TYPE]->(e)
                    """,

                    section_id=section_id,
                    name=entity["value"]
                )

            # --------------------------------------------------
            # RESIDENCY
            # --------------------------------------------------

            elif entity_type == "Residency":

                session.run(
                    """
                    MATCH (s:Section {
                        id:$section_id
                    })

                    MERGE (r:Residency {
                        section_id:$section_id,
                        name:$name
                    })

                    MERGE
                        (s)-[:HAS_RESIDENCY]->(r)
                    """,

                    section_id=section_id,
                    name=entity["value"]
                )

            # --------------------------------------------------
            # CREDIT SCORE
            # --------------------------------------------------

            elif entity_type == "CreditScore":

                session.run(
                    """
                    MATCH (s:Section {
                        id:$section_id
                    })

                    MERGE (c:CreditScore {
                        section_id:$section_id,
                        value:$value
                    })

                    MERGE
                        (s)-[:HAS_CREDIT_SCORE]->(c)
                    """,

                    section_id=section_id,
                    value=entity["value"]
                )

            # --------------------------------------------------
            # INCOME REQUIREMENT
            # --------------------------------------------------

            elif entity_type == "IncomeRequirement":

                session.run(
                    """
                    MATCH (s:Section {
                        id:$section_id
                    })

                    MERGE (i:IncomeRequirement {
                        section_id:$section_id,
                        value:$value
                    })

                    MERGE
                        (s)-[:HAS_INCOME_REQUIREMENT]->(i)
                    """,

                    section_id=section_id,
                    value=entity["value"]
                )

            # --------------------------------------------------
            # KYC DOCUMENT
            # --------------------------------------------------

            elif entity_type == "KYCDocument":

                session.run(
                    """
                    MATCH (s:Section {
                        id:$section_id
                    })

                    MERGE (d:KYCDocument {
                        section_id:$section_id,
                        name:$name
                    })

                    MERGE
                        (s)-[:REQUIRES_KYC]->(d)
                    """,

                    section_id=section_id,
                    name=entity["value"]
                )

            # --------------------------------------------------
            # UNKNOWN ENTITY
            # --------------------------------------------------

            else:

                print(
                    f"Skipping unsupported entity: "
                    f"{entity_type}"
                )

    # ==========================================================
    # INTEREST RATE
    # ==========================================================

    def _build_interest_rates(
        self,
        session,
        section_id,
        text
    ):

        """
        Creates one InterestRate node for each
        policy table row.

        Example:

        Secured Domestic Loan
        Up to ₹7.5 Lakhs
        9.50% – 10.25%
        0.50%

        becomes ONE node:

        InterestRate {
            category: "Secured Domestic Loan",
            amount_range: "Up to ₹7.5 Lakhs",
            min_rate: 9.50,
            max_rate: 10.25,
            female_concession: 0.50
        }
        """

        lines = [
            line.strip()
            for line in text.split("\n")
            if line.strip()
        ]

        loan_categories = {
            "Secured Domestic Loan",
            "Unsecured Domestic Loan",
            "International Study Loan"
        }

        current_category = None
        current_amount_range = None

        i = 0

        while i < len(lines):

            line = lines[i]

            # --------------------------------------------------
            # CATEGORY
            # --------------------------------------------------

            if line in loan_categories:

                current_category = line
                current_amount_range = None

                i += 1
                continue

            # --------------------------------------------------
            # AMOUNT RANGE
            # --------------------------------------------------

            amount_patterns = [
                r"Up to ₹[\d,]+(?:\s*Lakhs?)?",
                r"₹[\d,]+\s*Lakhs?\s*[–-]\s*₹[\d,]+\s*Lakhs?",
                r"Above ₹[\d,]+\s*Lakhs?",
                r"Up to ₹[\d,]+\s*Crores?",
                r"Above ₹[\d,]+\s*Crores?"
            ]

            amount_match = None

            for pattern in amount_patterns:

                amount_match = re.fullmatch(
                    pattern,
                    line,
                    re.IGNORECASE
                )

                if amount_match:
                    break

            if amount_match:

                current_amount_range = (
                    amount_match.group(0)
                )

                i += 1
                continue

            # --------------------------------------------------
            # INTEREST RATE
            # --------------------------------------------------

            rate_match = re.fullmatch(
                r"(\d+(?:\.\d+)?)%\s*[–-]\s*"
                r"(\d+(?:\.\d+)?)%",
                line
            )

            if (
                rate_match
                and current_category
                and current_amount_range
            ):

                min_rate = float(
                    rate_match.group(1)
                )

                max_rate = float(
                    rate_match.group(2)
                )

                # ----------------------------------------------
                # Female concession
                # ----------------------------------------------

                concession = None

                if i + 1 < len(lines):

                    concession_match = re.fullmatch(
                        r"(\d+(?:\.\d+)?)%",
                        lines[i + 1]
                    )

                    if concession_match:

                        concession = float(
                            concession_match.group(1)
                        )

                # ----------------------------------------------
                # CREATE NODE
                # ----------------------------------------------

                session.run(
                    """
                    MATCH (s:Section {
                        id:$section_id
                    })

                    MERGE (r:InterestRate {
                        section_id:$section_id,
                        category:$category,
                        amount_range:$amount_range
                    })

                    SET
                        r.min_rate=$min_rate,
                        r.max_rate=$max_rate,
                        r.female_concession=$female_concession

                    MERGE
                        (s)-[:HAS_INTEREST_RATE]->(r)
                    """,

                    section_id=section_id,
                    category=current_category,
                    amount_range=current_amount_range,
                    min_rate=min_rate,
                    max_rate=max_rate,
                    female_concession=concession
                )

                print(
                    "InterestRate:",
                    current_category,
                    "|",
                    current_amount_range,
                    "|",
                    min_rate,
                    "-",
                    max_rate,
                    "| Female:",
                    concession
                )

            i += 1

    # ==========================================================
    # LOAN AMOUNT
    # ==========================================================

    def _build_loan_amounts(
        self,
        session,
        section_id,
        text
    ):

        """
        Creates structured LoanAmount nodes.

        Example:

        Minimum Loan Amount: ₹50,000

        Maximum Loan Amount (Domestic Education):
        ₹50,00,000

        Maximum Loan Amount (International Education):
        ₹1,50,00,000
        """

        lines = [
            line.strip()
            for line in text.split("\n")
            if line.strip()
        ]

        for line in lines:

            # --------------------------------------------------
            # MINIMUM
            # --------------------------------------------------

            match = re.search(
                r"Minimum Loan Amount\s*:\s*"
                r"(₹[\d,]+)",
                line,
                re.IGNORECASE
            )

            if match:

                self._create_loan_amount(
                    session,
                    section_id,
                    match.group(1),
                    "Minimum",
                    "All Education Loans"
                )

                continue

            # --------------------------------------------------
            # MAXIMUM DOMESTIC
            # --------------------------------------------------

            match = re.search(
                r"Maximum Loan Amount\s*"
                r"\(Domestic Education\)\s*:\s*"
                r"(₹[\d,]+)",
                line,
                re.IGNORECASE
            )

            if match:

                self._create_loan_amount(
                    session,
                    section_id,
                    match.group(1),
                    "Maximum",
                    "Domestic Education"
                )

                continue

            # --------------------------------------------------
            # MAXIMUM INTERNATIONAL
            # --------------------------------------------------

            match = re.search(
                r"Maximum Loan Amount\s*"
                r"\(International Education\)\s*:\s*"
                r"(₹[\d,]+)",
                line,
                re.IGNORECASE
            )

            if match:

                self._create_loan_amount(
                    session,
                    section_id,
                    match.group(1),
                    "Maximum",
                    "International Education"
                )

    # ==========================================================
    # CREATE LOAN AMOUNT
    # ==========================================================

    def _create_loan_amount(
        self,
        session,
        section_id,
        value,
        amount_type,
        category
    ):

        session.run(
            """
            MATCH (s:Section {
                id:$section_id
            })

            MERGE (l:LoanAmount {
                section_id:$section_id,
                amount_type:$amount_type,
                category:$category
            })

            SET
                l.value=$value

            MERGE
                (s)-[:HAS_LOAN_AMOUNT]->(l)
            """,

            section_id=section_id,
            value=value,
            amount_type=amount_type,
            category=category
        )

        print(
            "LoanAmount:",
            amount_type,
            "|",
            category,
            "|",
            value
        )

    # ==========================================================
    # COLLATERAL
    # ==========================================================

    def _build_collateral_rules(
        self,
        session,
        section_id,
        text
    ):

        """
        Creates policy-specific collateral rules.

        Example:

        Below ₹7.5 Lakhs
        -> Not Required

        Above ₹7.5 Lakhs
        -> Required
        -> 100% coverage
        """

        lines = [
            line.strip()
            for line in text.split("\n")
            if line.strip()
        ]

        current_condition = None

        for line in lines:

            # --------------------------------------------------
            # BELOW THRESHOLD
            # --------------------------------------------------

            if re.search(
                r"Loans below ₹7\.5 Lakhs",
                line,
                re.IGNORECASE
            ):

                current_condition = (
                    "Below ₹7.5 Lakhs"
                )

                continue

            # --------------------------------------------------
            # ABOVE THRESHOLD
            # --------------------------------------------------

            if re.search(
                r"Loans above ₹7\.5 Lakhs",
                line,
                re.IGNORECASE
            ):

                current_condition = (
                    "Above ₹7.5 Lakhs"
                )

                continue

            # --------------------------------------------------
            # BELOW -> NOT REQUIRED
            # --------------------------------------------------

            if (
                current_condition ==
                "Below ₹7.5 Lakhs"
                and
                re.search(
                    r"No collateral security required",
                    line,
                    re.IGNORECASE
                )
            ):

                self._create_collateral_rule(
                    session,
                    section_id,
                    "Below ₹7.5 Lakhs",
                    "Not Required",
                    None
                )

                current_condition = (
                    "Below ₹7.5 Lakhs"
                )

                continue

            # --------------------------------------------------
            # ABOVE -> REQUIRED
            # --------------------------------------------------

            if (
                current_condition ==
                "Above ₹7.5 Lakhs"
                and
                re.search(
                    r"Tangible collateral security required",
                    line,
                    re.IGNORECASE
                )
            ):

                self._create_collateral_rule(
                    session,
                    section_id,
                    "Above ₹7.5 Lakhs",
                    "Required",
                    "100% of loan amount"
                )

                continue

    # ==========================================================
    # CREATE COLLATERAL RULE
    # ==========================================================

    def _create_collateral_rule(
        self,
        session,
        section_id,
        condition,
        status,
        coverage
    ):

        session.run(
            """
            MATCH (s:Section {
                id:$section_id
            })

            MERGE (c:CollateralRule {
                section_id:$section_id,
                condition:$condition
            })

            SET
                c.status=$status,
                c.coverage=$coverage

            MERGE
                (s)-[:HAS_COLLATERAL_RULE]->(c)
            """,

            section_id=section_id,
            condition=condition,
            status=status,
            coverage=coverage
        )

        print(
            "CollateralRule:",
            condition,
            "|",
            status,
            "|",
            coverage
        )