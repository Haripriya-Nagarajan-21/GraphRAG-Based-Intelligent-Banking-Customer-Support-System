from neo4j import GraphDatabase

from config import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD
)


class GraphRetriever:

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(self):

        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(
                NEO4J_USER,
                NEO4J_PASSWORD
            )
        )

        self.driver.verify_connectivity()

        print("Graph Retriever Connected")


    # ==========================================================
    # CLOSE
    # ==========================================================

    def close(self):

        if self.driver:
            self.driver.close()


    # ==========================================================
    # MAIN RETRIEVAL
    # ==========================================================

    def retrieve(
        self,
        question: str
    ) -> list:

        question_lower = (
            question.lower().strip()
        )

        # ------------------------------------------------------
        # 1. Detect policy
        # ------------------------------------------------------

        policy_ids = self.detect_policies(
            question_lower
        )

        # ------------------------------------------------------
        # 2. Detect section / intent
        # ------------------------------------------------------

        sections = self.extract_keywords(
            question_lower
        )

        # ------------------------------------------------------
        # 3. If no section detected
        # ------------------------------------------------------

        if not sections:

            sections = self.default_sections(
                question_lower
            )

        # ------------------------------------------------------
        # 4. If no policy detected
        #
        # Search all policies.
        #
        # Example:
        # "What is the processing fee?"
        #
        # ------------------------------------------------------

        if not policy_ids:

            policy_ids = (
                self.get_all_policy_ids()
            )

        context = []

        try:

            with self.driver.session() as session:

                # ==================================================
                # SECTION RETRIEVAL
                # ==================================================

                for policy_id in policy_ids:

                    for section_name in sections:

                        records = session.run(
                            """
                            MATCH
                                (p:Policy {id:$policy_id})
                                -[:HAS_LOAN]->(l:Loan)
                                -[:HAS_SECTION]->(s:Section)

                            WHERE
                                toLower(trim(s.name))
                                =
                                toLower(trim($section_name))

                            RETURN
                                p.id AS policy_id,
                                p.name AS policy,
                                p.version AS policy_version,

                                l.name AS loan,

                                s.id AS section_id,
                                s.name AS section,
                                s.content AS content
                            """,

                            policy_id=policy_id,
                            section_name=section_name
                        )

                        for record in records:

                            data = record.data()

                            item = {

                                "policy_id":
                                    data.get(
                                        "policy_id"
                                    ),

                                "policy":
                                    data.get(
                                        "policy"
                                    ),

                                "policy_version":
                                    data.get(
                                        "policy_version"
                                    ),

                                "loan":
                                    data.get(
                                        "loan"
                                    ),

                                "section_id":
                                    data.get(
                                        "section_id"
                                    ),

                                "section":
                                    data.get(
                                        "section"
                                    ),

                                "category":
                                    None,

                                "content":
                                    data.get(
                                        "content"
                                    ) or "",

                                "entities":
                                    [],

                                "source_type":
                                    "graph_section",

                                "retrieval_reason":
                                    (
                                        f"Matched section "
                                        f"'{data.get('section')}' "
                                        f"for detected intent."
                                    )
                            }

                            context.append(
                                item
                            )


                # ==================================================
                # STRUCTURED ENTITIES
                # ==================================================

                context = (
                    self._attach_structured_entities(
                        session,
                        context
                    )
                )


                # ==================================================
                # REQUIRED DOCUMENTS
                # ==================================================

                if (
                    "Required Documents"
                    in sections
                ):

                    document_context = (
                        self._retrieve_documents(
                            session,
                            policy_ids
                        )
                    )

                    context.extend(
                        document_context
                    )


            # ======================================================
            # REMOVE DUPLICATES
            # ======================================================

            context = (
                self._remove_duplicates(
                    context
                )
            )


            # ======================================================
            # SORT CONTEXT
            # ======================================================

            context = (
                self._sort_context(
                    context
                )
            )


            # ======================================================
            # DEBUG OUTPUT
            # ======================================================

            self._debug_print(
                question,
                policy_ids,
                sections,
                context
            )


            return context


        except Exception as e:

            print(
                "Retriever Error:",
                e
            )

            return []


    # ==========================================================
    # POLICY DETECTION
    # ==========================================================

    def detect_policies(
        self,
        question
    ):

        policies = []


        # ------------------------------------------------------
        # EDUCATION LOAN
        # ------------------------------------------------------

        education_words = [

            "education loan",
            "education",
            "student",
            "students",
            "study",
            "college",
            "school",
            "course",
            "tuition",
            "university",
            "academic"
        ]


        if any(
            word in question
            for word in education_words
        ):

            policies.append(
                "ELP-002"
            )


        # ------------------------------------------------------
        # HOME LOAN
        # ------------------------------------------------------

        home_words = [

            "home loan",
            "home loan",
            "house loan",
            "home",
            "house",
            "housing",
            "property",
            "residential property",
            "residential"
        ]


        if any(
            word in question
            for word in home_words
        ):

            policies.append(
                "HLP-001"
            )


        # ------------------------------------------------------
        # GENERAL BANKING
        # ------------------------------------------------------

        general_words = [

            "saving account",
            "savings account",
            "bank account",
            "account",
            "atm",
            "upi",
            "cheque",
            "check",
            "nominee",
            "branch",
            "deposit",
            "withdraw",
            "withdrawal"
        ]


        if any(
            word in question
            for word in general_words
        ):

            policies.append(
                "GBP-003"
            )


        # ------------------------------------------------------
        # REMOVE DUPLICATES
        # ------------------------------------------------------

        return list(
            dict.fromkeys(
                policies
            )
        )


    # ==========================================================
    # SECTION / INTENT DETECTION
    # ==========================================================

    def extract_keywords(
        self,
        question
    ):

        mapping = [

            # ==================================================
            # REQUIRED DOCUMENTS
            # ==================================================

            (
                [
                    "required documents",
                    "documents required",
                    "documents needed",
                    "documents necessary",
                    "what documents",
                    "which documents",
                    "document required",
                    "document needed",
                    "proof required",
                    "proof needed",
                    "papers required",
                    "papers needed",
                    "aadhaar",
                    "aadhar",
                    "pan card",
                    "passport",
                    "driving licence",
                    "driving license"
                ],

                "Required Documents"
            ),


            # ==================================================
            # INTEREST RATE
            # ==================================================

            (
                [
                    "interest rate",
                    "interest rates",
                    "rate of interest",
                    "roi",
                    "what is the rate",
                    "what rate",
                    "interest"
                ],

                "Interest Rate"
            ),


            # ==================================================
            # PROCESSING FEE
            # ==================================================

            (
                [
                    "processing fee",
                    "processing fees",
                    "processing charge",
                    "processing charges"
                ],

                "Processing Fee"
            ),


            # ==================================================
            # LOAN AMOUNT
            # ==================================================

            (
                [
                    "loan amount",
                    "maximum loan",
                    "maximum amount",
                    "minimum loan",
                    "minimum amount",
                    "how much loan",
                    "how much can i borrow",
                    "how much can i get",
                    "maximum borrowing",
                    "loan limit"
                ],

                "Loan Amount"
            ),


            # ==================================================
            # ELIGIBILITY
            # ==================================================

            (
                [
                    "eligibility",
                    "eligible",
                    "qualify",
                    "qualification",
                    "who can apply",
                    "can i apply",
                    "can i get",
                    "age",
                    "minimum age",
                    "maximum age",
                    "salary",
                    "income",
                    "employment",
                    "employment type",
                    "credit score",
                    "credit history",
                    "cibil",
                    "residency",
                    "resident",
                    "citizen"
                ],

                "Eligibility Criteria"
            ),


            # ==================================================
            # LOAN TENURE
            # ==================================================

            (
                [
                    "loan tenure",
                    "tenure",
                    "loan duration",
                    "loan period",
                    "duration",
                    "repayment period"
                ],

                "Loan Tenure"
            ),


            # ==================================================
            # COLLATERAL
            # ==================================================

            (
                [
                    "collateral",
                    "security",
                    "security required",
                    "collateral required",
                    "guarantee",
                    "guarantor"
                ],

                "Collateral"
            ),


            # ==================================================
            # REPAYMENT
            # ==================================================

            (
                [
                    "repayment",
                    "repay",
                    "emi",
                    "installment",
                    "installments",
                    "installment amount",
                    "repayment schedule",
                    "pay back",
                    "payment schedule"
                ],

                "Repayment"
            ),


            # ==================================================
            # PURPOSE
            # ==================================================

            (
                [
                    "purpose",
                    "what is the loan for",
                    "what can the loan be used for",
                    "what can i use the loan for",
                    "loan used for",
                    "use of loan",
                    "why is the loan provided"
                ],

                "Purpose"
            )
        ]


        found = []


        for keywords, section in mapping:

            for keyword in keywords:

                if keyword in question:

                    found.append(
                        section
                    )

                    break


        return list(
            dict.fromkeys(
                found
            )
        )


    # ==========================================================
    # DEFAULT SECTION DETECTION
    # ==========================================================

    def default_sections(
        self,
        question
    ):

        # ------------------------------------------------------
        # Generic loan question
        #
        # IMPORTANT:
        # "Eligibility Criteria" is the actual section name
        # in the Neo4j database.
        # ------------------------------------------------------

        if any(
            word in question
            for word in [
                "loan",
                "borrow",
                "apply",
                "application"
            ]
        ):

            return [

                "Eligibility Criteria",

                "Loan Amount",

                "Required Documents"

            ]


        # ------------------------------------------------------
        # Generic banking question
        # ------------------------------------------------------

        if any(
            word in question
            for word in [
                "bank",
                "account",
                "banking",
                "service"
            ]
        ):

            return [

                "Purpose",

                "Required Documents"

            ]


        # ------------------------------------------------------
        # Safe fallback
        # ------------------------------------------------------

        return [

            "Purpose"

        ]


    # ==========================================================
    # GET ALL POLICIES
    # ==========================================================

    def get_all_policy_ids(
        self
    ):

        policy_ids = []


        try:

            with self.driver.session() as session:

                records = session.run(
                    """
                    MATCH (p:Policy)

                    RETURN
                        p.id AS policy_id

                    ORDER BY p.id
                    """
                )


                for record in records:

                    policy_id = (
                        record.get(
                            "policy_id"
                        )
                    )

                    if policy_id:

                        policy_ids.append(
                            policy_id
                        )


        except Exception as e:

            print(
                "Policy detection error:",
                e
            )


        return policy_ids


    # ==========================================================
    # ATTACH STRUCTURED ENTITIES
    # ==========================================================

    def _attach_structured_entities(
        self,
        session,
        context
    ):

        updated_context = []


        for item in context:

            section_id = (
                item.get(
                    "section_id"
                )
            )


            if not section_id:

                updated_context.append(
                    item
                )

                continue


            records = session.run(
                """
                MATCH
                    (s:Section {id:$section_id})
                    -[r]->(e)

                RETURN
                    type(r) AS relationship,
                    labels(e) AS labels,
                    properties(e) AS properties

                ORDER BY
                    labels(e)[0]
                """,

                section_id=section_id
            )


            entities = []


            for record in records:

                labels = (
                    record.get(
                        "labels"
                    ) or []
                )

                properties = (
                    record.get(
                        "properties"
                    ) or {}
                )


                # --------------------------------------------------
                # Ignore DocumentCategory
                #
                # Documents are retrieved separately.
                # --------------------------------------------------

                if (
                    "DocumentCategory"
                    in labels
                ):

                    continue


                # --------------------------------------------------
                # Ignore incomplete InterestRate nodes
                # --------------------------------------------------

                if (
                    "InterestRate"
                    in labels
                ):

                    if (
                        "category"
                        not in properties

                        or

                        "amount_range"
                        not in properties
                    ):

                        continue


                entities.append({

                    "labels":
                        labels,

                    "relationship":
                        record.get(
                            "relationship"
                        ),

                    "properties":
                        properties

                })


            item["entities"] = entities


            # --------------------------------------------------
            # Update provenance
            # --------------------------------------------------

            if entities:

                item["retrieval_reason"] += (

                    " Structured graph entities were "
                    "attached from the same section."

                )


            updated_context.append(
                item
            )


        return updated_context


    # ==========================================================
    # REQUIRED DOCUMENT RETRIEVAL
    # ==========================================================

    def _retrieve_documents(
        self,
        session,
        policy_ids
    ):

        context = []


        for policy_id in policy_ids:

            records = session.run(
                """
                MATCH
                    (p:Policy {id:$policy_id})
                    -[:HAS_LOAN]->(l:Loan)
                    -[:HAS_SECTION]->(s:Section)

                WHERE
                    toLower(trim(s.name))
                    =
                    "required documents"

                MATCH
                    (s)-[:HAS_SUBSECTION]->
                    (dc:DocumentCategory)

                OPTIONAL MATCH
                    (dc)-[:REQUIRES_DOCUMENT]->
                    (d:Document)

                RETURN
                    p.id AS policy_id,
                    p.name AS policy,
                    p.version AS policy_version,

                    l.name AS loan,

                    s.id AS section_id,
                    s.name AS section,

                    dc.id AS category_id,
                    dc.name AS category,

                    collect(
                        DISTINCT d.name
                    ) AS documents

                ORDER BY
                    category
                """,

                policy_id=policy_id
            )


            for record in records:

                documents = [

                    d

                    for d in (
                        record.get(
                            "documents"
                        ) or []
                    )

                    if d

                ]


                # --------------------------------------------------
                # Create clean content
                # --------------------------------------------------

                lines = []


                for document in documents:

                    lines.append(
                        f"• {document}"
                    )


                content = "\n".join(
                    lines
                )


                context.append({

                    "policy_id":
                        record.get(
                            "policy_id"
                        ),

                    "policy":
                        record.get(
                            "policy"
                        ),

                    "policy_version":
                        record.get(
                            "policy_version"
                        ),

                    "loan":
                        record.get(
                            "loan"
                        ),

                    "section_id":
                        record.get(
                            "section_id"
                        ),

                    "section":
                        record.get(
                            "section"
                        ),

                    "category":
                        record.get(
                            "category"
                        ),

                    "content":
                        content,

                    "entities":
                        [],

                    "source_type":
                        "graph_document_category",

                    "retrieval_reason":
                        (
                            "Matched Required Documents "
                            f"category "
                            f"'{record.get('category')}'."
                        ),

                    "category_id":
                        record.get(
                            "category_id"
                        )
                })


        return context


    # ==========================================================
    # DUPLICATE REMOVAL
    # ==========================================================

    def _remove_duplicates(
        self,
        context
    ):

        unique = []

        seen = set()


        for item in context:

            key = (

                item.get(
                    "policy_id"
                ),

                item.get(
                    "section_id"
                ),

                item.get(
                    "category"
                ),

                item.get(
                    "source_type"
                ),

                item.get(
                    "content"
                )

            )


            if key not in seen:

                seen.add(
                    key
                )

                unique.append(
                    item
                )


        return unique


    # ==========================================================
    # SORT CONTEXT
    # ==========================================================

    def _sort_context(
        self,
        context
    ):

        # ------------------------------------------------------
        # IMPORTANT:
        # These names match your actual Neo4j sections.
        # ------------------------------------------------------

        priority = {

            "Introduction":
                0,

            "Eligibility Criteria":
                1,

            "Interest Rate":
                2,

            "Loan Amount":
                3,

            "Loan Tenure":
                4,

            "Required Documents":
                5,

            "Processing Fee":
                6,

            "Collateral":
                7,

            "Purpose":
                8,

            "Repayment":
                9,

            "Frequently Asked Questions":
                10,

            "Moratorium Period":
                11
        }


        context.sort(

            key=lambda x: (

                x.get(
                    "policy",
                    ""
                ),

                priority.get(

                    x.get(
                        "section",
                        ""
                    ),

                    99
                ),

                x.get(
                    "category",
                    ""
                ) or ""

            )

        )


        return context


    # ==========================================================
    # DEBUG / PROVENANCE
    # ==========================================================

    def _debug_print(
        self,
        question,
        policy_ids,
        sections,
        context
    ):

        print("\n")

        print(
            "=" * 75
        )

        print(
            "GRAPH RETRIEVAL"
        )

        print(
            "=" * 75
        )


        print(
            "Question:",
            question
        )


        print(
            "Detected Policies:",
            policy_ids
        )


        print(
            "Detected Sections:",
            sections
        )


        print(
            "Retrieved Chunks:",
            len(context)
        )


        print(
            "-" * 75
        )


        for index, item in enumerate(
            context,
            start=1
        ):

            print(
                f"\nCHUNK {index}"
            )


            print(
                "Policy       :",
                item.get(
                    "policy"
                )
            )


            print(
                "Policy ID    :",
                item.get(
                    "policy_id"
                )
            )


            print(
                "Policy Version:",
                item.get(
                    "policy_version"
                )
            )


            print(
                "Loan         :",
                item.get(
                    "loan"
                )
            )


            print(
                "Section      :",
                item.get(
                    "section"
                )
            )


            print(
                "Section ID   :",
                item.get(
                    "section_id"
                )
            )


            print(
                "Category     :",
                item.get(
                    "category"
                )
            )


            print(
                "Source Type  :",
                item.get(
                    "source_type"
                )
            )


            print(
                "Reason       :",
                item.get(
                    "retrieval_reason"
                )
            )


            print(
                "Content      :"
            )


            print(

                item.get(
                    "content",
                    ""
                )[:1000]

            )


            print(
                "Entities     :",
                item.get(
                    "entities"
                )
            )


            print(
                "-" * 75
            )