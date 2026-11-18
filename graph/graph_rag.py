from graph.retriever import GraphRetriever
from graph.context_formatter import ContextFormatter
from llm.ollama_client import OllamaClient

from prompts.answer_prompt import (
    QA_SYSTEM_PROMPT,
    QA_USER_TEMPLATE
)

import time


class GraphRAG:
    """
    Orchestrates the GraphRAG pipeline:

    1. Validate banking question
    2. Retrieve relevant sections and graph entities
       from Neo4j
    3. Format retrieved context
    4. Generate answer using Ollama / Gemma
    5. Provide fallback answer if required
    """

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(self):

        self.retriever = GraphRetriever()

        self.formatter = ContextFormatter()

        self.ollama = OllamaClient()

    # ==========================================================
    # CLOSE
    # ==========================================================

    def close(self):

        self.retriever.close()

    # ==========================================================
    # BANKING DOMAIN CHECK
    # ==========================================================

    def is_banking_related(
        self,
        question
    ):

        banking_keywords = [

            "loan",
            "home",
            "education",
            "personal",
            "credit",
            "card",
            "interest",
            "rate",
            "emi",
            "repayment",
            "document",
            "documents",
            "eligibility",
            "eligible",
            "qualify",
            "qualification",
            "kyc",
            "account",
            "saving",
            "savings",
            "transaction",
            "bank",
            "deposit",
            "withdraw",
            "customer",
            "nominee",
            "upi",
            "cheque",
            "atm",
            "branch",
            "mortgage",
            "collateral",
            "fee",
            "fees",
            "charges",
            "tenure",
            "salary",
            "income",
            "cibil",
            "credit score"
        ]

        question = question.lower()

        for word in banking_keywords:

            if word in question:

                return True

        return False

    # ==========================================================
    # FALLBACK ANSWER
    # ==========================================================

    def create_fallback_answer(
        self,
        policies_seen
    ):

        response = []

        for policy, sections in policies_seen.items():

            response.append(
                f"## 🏦 {policy}"
            )

            if not sections:

                response.append(
                    "No detailed information retrieved."
                )

                continue

            for section, contents in sections.items():

                response.append(
                    f"\n### {section}"
                )

                if contents:

                    for content in contents:

                        response.append(
                            content[:1000]
                        )

                else:

                    response.append(
                        "No section content available."
                    )

        return "\n".join(
            response
        )

    # ==========================================================
    # MAIN GRAPH RAG PIPELINE
    # ==========================================================

    def answer_question(
        self,
        question: str
    ) -> dict:

        start_time = time.time()

        # ======================================================
        # STEP 1
        # DOMAIN VALIDATION
        # ======================================================

        if not self.is_banking_related(
            question
        ):

            return {

                "answer":
                    "I can only answer questions related "
                    "to National Trust Bank services such as "
                    "loans, accounts, KYC, interest rates, "
                    "documents, repayment, and banking policies.",

                "context": [],

                "formatted_context": "",

                "keywords": [],

                "stats": {

                    "policies": [],

                    "section_count": 0,

                    "relationship_count": 0,

                    "response_time":
                        round(
                            time.time()
                            - start_time,
                            2
                        )
                }
            }

        # ======================================================
        # STEP 2
        # RETRIEVE FROM NEO4J
        # ======================================================

        raw_context = self.retriever.retrieve(
            question
        )

        keywords = self.retriever.extract_keywords(
            question
        )

        # ======================================================
        # STEP 3
        # NO RETRIEVAL RESULT
        # ======================================================

        if not raw_context:

            fallback_answer = (

                "I couldn't find any relevant information "
                "in the Banking Knowledge Graph for your "
                "question. Please try asking about eligibility, "
                "required documents, interest rates, loan amount, "
                "processing fee, collateral, KYC, or repayment."
            )

            return {

                "answer":
                    fallback_answer,

                "context": [],

                "formatted_context": "",

                "keywords":
                    keywords,

                "stats": {

                    "policies": [],

                    "section_count": 0,

                    "relationship_count": 0,

                    "response_time":
                        round(
                            time.time()
                            - start_time,
                            2
                        )
                }
            }

        # ======================================================
        # STEP 4
        # FORMAT CONTEXT
        # ======================================================

        context_str = (
            self.formatter.format_context(
                raw_context
            )
        )

        # ======================================================
        # STEP 5
        # EXTRACT STATISTICS
        # ======================================================

        formatter_stats = (
            self.formatter.extract_statistics(
                raw_context
            )
        )

        # ======================================================
        # STEP 6
        # GROUP DATA FOR FALLBACK
        # ======================================================

        policies_seen = (
            self.formatter.group_by_policy(
                raw_context
            )
        )

        # ======================================================
        # DEBUG
        # ======================================================

        print(
            "\n" + "=" * 70
        )

        print(
            "Retrieved Context Sent to Ollama"
        )

        print(
            "=" * 70
        )

        print(
            context_str
        )

        print(
            "=" * 70 + "\n"
        )

        # ======================================================
        # STEP 7
        # CREATE USER PROMPT
        # ======================================================

        try:

            user_prompt = QA_USER_TEMPLATE.format(

                context_str=context_str,

                question=question

            )

        except Exception as e:

            print(
                "Prompt Formatting Error:",
                e
            )

            user_prompt = (
                f"Context:\n"
                f"{context_str}\n\n"
                f"Question:\n"
                f"{question}"
            )

        # ======================================================
        # STEP 8
        # GENERATE ANSWER
        # ======================================================

        try:

            if self.should_use_structured_answer(
                raw_context
            ):

                answer = self.build_structured_answer(
                    raw_context
                )

            else:

                answer = self.ollama.generate(

                    prompt=user_prompt,

                    system=QA_SYSTEM_PROMPT,

                    temperature=0.0

                )

        except Exception as e:

            print(
                "Answer Generation Error:",
                e
            )

            answer = (
                "Error: "
                + str(e)
            )
        # ======================================================
        # DEBUG GEMMA OUTPUT
        # ======================================================

        print(
            "\n========== GEMMA RAW OUTPUT =========="
        )

        print(
            answer
        )

        print(
            "======================================"
        )

        # ======================================================
        # STEP 9
        # WEAK RESPONSE FALLBACK
        # ======================================================

        if not answer:

            answer = ""

        if (

            not self.should_use_structured_answer(
                raw_context
            )

            and (

                len(answer.strip()) < 80

                or (

                    "policy" in answer.lower()

                    and len(answer.split()) < 10

                )

            )

        ):

            answer = self.create_fallback_answer(
                policies_seen
            )
        # ======================================================
        # STEP 10
        # OLLAMA OFFLINE FALLBACK
        # ======================================================

        if (

            "Error:" in answer

            or "Failed to connect" in answer

            or "Connection refused" in answer

            or "timed out" in answer.lower()

            or "timeout" in answer.lower()

        ):

            fallback_parts = [

                "⚠️ **Ollama Offline Fallback**",

                "I was unable to connect to the local "
                "Ollama service to generate a natural "
                "language response. However, I have "
                "successfully extracted the following "
                "facts directly from the Neo4j Knowledge Graph:\n"

            ]

            for (
                policy_name,
                sections
            ) in policies_seen.items():

                fallback_parts.append(
                    f"### Policy: {policy_name}"
                )

                for (
                    section_name,
                    contents
                ) in sections.items():

                    fallback_parts.append(
                        f"#### Section: {section_name}"
                    )

                    # ------------------------------------------
                    # CONTENT
                    # ------------------------------------------

                    for content in contents:

                        lines = [

                            line.strip()

                            for line
                            in content.split("\n")

                            if line.strip()

                        ]

                        fallback_parts.append(

                            "\n".join(
                                lines[:15]
                            )

                        )

                        if len(lines) > 15:

                            fallback_parts.append(
                                "*(Content truncated for space)*"
                            )

                fallback_parts.append(
                    "-" * 30
                )

            answer = "\n\n".join(
                fallback_parts
            )

        # ======================================================
        # STEP 11
        # RESPONSE TIME
        # ======================================================

        response_time = round(

            time.time()
            - start_time,

            2

        )

        # ======================================================
        # STEP 12
        # FINAL STATISTICS
        # ======================================================

        stats = {

            "policies":
                formatter_stats[
                    "policies"
                ],

            "section_count":
                formatter_stats[
                    "section_count"
                ],

            "relationship_count":
                formatter_stats[
                    "relationship_count"
                ],

            "response_time":
                response_time

        }

        # ======================================================
        # STEP 13
        # FINAL RESPONSE
        # ======================================================

        return {

            "answer":
                answer,

            "context":
                raw_context,

            "formatted_context":
                context_str,

            "keywords":
                keywords,

            "stats":
                stats

        }
    # ==========================================================
    # STRUCTURED ANSWER BUILDER
    # ==========================================================

    

    def build_structured_answer(
        self,
        raw_context
    ):

        if not raw_context:

            return (
                "The available banking policy "
                "information does not specify this."
            )

        first = raw_context[0]

        policy = first.get(
            "policy",
            "Unknown Policy"
        )

        section = first.get(
            "section",
            "Unknown Section"
        )

        lines = [

            "🏦 Banking Policy Answer",

            "",

            f"Policy: {policy}",

            f"Section: {section}",

            "",

            "Answer:",

            ""
        ]

        seen = set()

        for item in raw_context:

            content = (
                item.get(
                    "content",
                    ""
                ).strip()
            )

            if not content:
                continue

            if content in seen:
                continue

            seen.add(content)

            content_lines = [

                x.strip()

                for x in content.splitlines()

                if x.strip()
            ]

            for line in content_lines:

                if line not in seen:

                    lines.append(line)

                    seen.add(line)

        lines.extend(

            [

                "",

                "Basis:",

                f"{policy} → {section}"
            ]

        )

        return "\n".join(lines)

    # ==========================================================
    # CHECK STRUCTURED SECTION
    # ==========================================================

    def should_use_structured_answer(
        self,
        raw_context
    ):

        structured_sections = {

            "Required Documents",

            "Eligibility Criteria",

            "Interest Rate",

            "Loan Amount",

            "Processing Fee",

            "Loan Tenure",

            "Collateral",

            "KYC"
        }

        for item in raw_context:

            section = item.get(
                "section",
                ""
            )

            if section in structured_sections:

                return True

        return False