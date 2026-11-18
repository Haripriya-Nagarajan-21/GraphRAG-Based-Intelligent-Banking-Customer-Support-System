import time
import csv
import os
import re

from graph.graph_rag import GraphRAG


# ==========================================================
# EVALUATION DATASET
# ==========================================================

TEST_DATA = [

    # ======================================================
    # HOME LOAN
    # ======================================================

    {
        "id": 1,
        "question": "What is the interest rate for a home loan?",
        "expected_policy": "HLP-001",
        "expected_section": "Interest Rate",
        "expected_keywords": [
            "9.10%",
            "9.50%",
            "fixed rate"
        ]
    },

    {
        "id": 2,
        "question": "What documents are required for a home loan?",
        "expected_policy": "HLP-001",
        "expected_section": "Required Documents",
        "expected_keywords": [
            "aadhaar",
            "pan card",
            "bank statements",
            "salary slips"
        ]
    },

    {
        "id": 3,
        "question": "What is the eligibility criteria for a home loan?",
        "expected_policy": "HLP-001",
        "expected_section": "Eligibility Criteria",
        "expected_keywords": [
            "eligibility",
            "age",
            "income"
        ]
    },

    {
        "id": 4,
        "question": "What is the processing fee for a home loan?",
        "expected_policy": "HLP-001",
        "expected_section": "Processing Fee",
        "expected_keywords": [
            "processing",
            "fee"
        ]
    },

    {
        "id": 5,
        "question": "What is the repayment period for a home loan?",
        "expected_policy": "HLP-001",
        "expected_section": "Loan Tenure",
        "expected_keywords": [
            "tenure",
            "20 years"
        ]
    },

    {
        "id": 6,
        "question": "Is collateral required for a home loan?",
        "expected_policy": "HLP-001",
        "expected_section": "Collateral",
        "expected_keywords": [
            "collateral"
        ]
    },


    # ======================================================
    # EDUCATION LOAN
    # ======================================================

    {
        "id": 7,
        "question": "What is the interest rate for an education loan?",
        "expected_policy": "ELP-002",
        "expected_section": "Interest Rate",
        "expected_keywords": [
            "9.50%",
            "10.25%",
            "female concession"
        ]
    },

    {
        "id": 8,
        "question": "What documents are required for an education loan?",
        "expected_policy": "ELP-002",
        "expected_section": "Required Documents",
        "expected_keywords": [
            "aadhaar",
            "pan",
            "passport"
        ]
    },

    {
        "id": 9,
        "question": "Who is eligible for an education loan?",
        "expected_policy": "ELP-002",
        "expected_section": "Eligibility Criteria",
        "expected_keywords": [
            "student",
            "education"
        ]
    },

    {
        "id": 10,
        "question": "What is the maximum education loan amount?",
        "expected_policy": "ELP-002",
        "expected_section": "Loan Amount",
        "expected_keywords": [
            "loan amount"
        ]
    },


    # ======================================================
    # GENERAL BANKING
    # ======================================================

    {
        "id": 11,
        "question": "What documents are required for KYC?",
        "expected_policy": "GBP-003",
        "expected_section": "KYC",
        "expected_keywords": [
            "kyc",
            "identity"
        ]
    },

    {
        "id": 12,
        "question": "What is the process for adding a nominee to a bank account?",
        "expected_policy": "GBP-003",
        "expected_section": "Nominee",
        "expected_keywords": [
            "nominee",
            "account"
        ]
    }
]


# ==========================================================
# TEXT NORMALIZATION
# ==========================================================

def normalize_text(text):

    if not text:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ==========================================================
# POLICY RETRIEVAL ACCURACY
# ==========================================================

def calculate_policy_accuracy(
    context,
    expected_policy
):

    policies = set()

    for item in context:

        policy_id = item.get(
            "policy_id"
        )

        if policy_id:
            policies.add(
                policy_id
            )

    if expected_policy in policies:
        return 1

    return 0


# ==========================================================
# SECTION RETRIEVAL ACCURACY
# ==========================================================

def calculate_section_accuracy(
    context,
    expected_policy,
    expected_section
):

    for item in context:

        if (
            item.get("policy_id")
            == expected_policy
            and
            normalize_text(
                item.get("section")
            )
            ==
            normalize_text(
                expected_section
            )
        ):

            return 1

    return 0


# ==========================================================
# CONTEXT PRECISION
# ==========================================================

def calculate_context_precision(
    context,
    expected_policy,
    expected_section
):

    if not context:
        return 0.0

    relevant = 0

    for item in context:

        if (
            item.get("policy_id")
            == expected_policy
            and
            normalize_text(
                item.get("section")
            )
            ==
            normalize_text(
                expected_section
            )
        ):

            relevant += 1

    return relevant / len(context)


# ==========================================================
# CONTEXT RECALL
#
# For our evaluation dataset each question has one
# expected policy + section pair.
# ==========================================================

def calculate_context_recall(
    context,
    expected_policy,
    expected_section
):

    if not context:
        return 0.0

    for item in context:

        if (
            item.get("policy_id")
            == expected_policy
            and
            normalize_text(
                item.get("section")
            )
            ==
            normalize_text(
                expected_section
            )
        ):

            return 1.0

    return 0.0


# ==========================================================
# ANSWER FACT COVERAGE
# ==========================================================

def calculate_fact_coverage(
    answer,
    expected_keywords
):

    if not expected_keywords:
        return 0.0

    answer_normalized = normalize_text(
        answer
    )

    matched = 0

    for keyword in expected_keywords:

        keyword_normalized = normalize_text(
            keyword
        )

        if keyword_normalized in answer_normalized:

            matched += 1

    return matched / len(
        expected_keywords
    )


# ==========================================================
# ANSWER ACCURACY
#
# We consider an answer correct when:
#
# 1. Correct policy retrieved
# 2. Correct section retrieved
# 3. At least 70% expected facts appear
# ==========================================================

def calculate_answer_accuracy(
    policy_accuracy,
    section_accuracy,
    fact_coverage
):

    if (
        policy_accuracy == 1
        and
        section_accuracy == 1
        and
        fact_coverage >= 0.70
    ):

        return 1

    return 0


# ==========================================================
# EVALUATE ONE QUESTION
# ==========================================================

def evaluate_question(
    rag,
    test_case
):

    question = test_case[
        "question"
    ]

    expected_policy = test_case[
        "expected_policy"
    ]

    expected_section = test_case[
        "expected_section"
    ]

    expected_keywords = test_case[
        "expected_keywords"
    ]


    print("\n")
    print("=" * 80)

    print(
        f"QUESTION {test_case['id']}"
    )

    print(
        "Question:",
        question
    )

    print("=" * 80)


    # ======================================================
    # RUN GRAPHRAG
    # ======================================================

    start_time = time.perf_counter()


    try:

        result = rag.answer_question(
            question
        )

    except Exception as e:

        print(
            "ERROR:",
            e
        )

        return {

            "id":
                test_case["id"],

            "question":
                question,

            "policy_accuracy":
                0,

            "section_accuracy":
                0,

            "context_precision":
                0,

            "context_recall":
                0,

            "fact_coverage":
                0,

            "answer_accuracy":
                0,

            "response_time":
                0,

            "context_count":
                0,

            "error":
                str(e)
        }


    elapsed = (
        time.perf_counter()
        - start_time
    )


    # ======================================================
    # EXTRACT RESULT
    # ======================================================

    answer = result.get(
        "answer",
        ""
    )

    context = result.get(
        "context",
        []
    )


    # ======================================================
    # CALCULATE METRICS
    # ======================================================

    policy_accuracy = (
        calculate_policy_accuracy(
            context,
            expected_policy
        )
    )


    section_accuracy = (
        calculate_section_accuracy(
            context,
            expected_policy,
            expected_section
        )
    )


    context_precision = (
        calculate_context_precision(
            context,
            expected_policy,
            expected_section
        )
    )


    context_recall = (
        calculate_context_recall(
            context,
            expected_policy,
            expected_section
        )
    )


    fact_coverage = (
        calculate_fact_coverage(
            answer,
            expected_keywords
        )
    )


    answer_accuracy = (
        calculate_answer_accuracy(
            policy_accuracy,
            section_accuracy,
            fact_coverage
        )
    )


    # ======================================================
    # PRINT RESULT
    # ======================================================

    print("\nANSWER:")
    print(answer)


    print("\nEXPECTED POLICY:")
    print(expected_policy)


    print("\nEXPECTED SECTION:")
    print(expected_section)


    print("\nMETRICS:")

    print(
        "Policy Accuracy      :",
        policy_accuracy
    )

    print(
        "Section Accuracy     :",
        section_accuracy
    )

    print(
        "Context Precision    :",
        f"{context_precision:.2f}"
    )

    print(
        "Context Recall       :",
        f"{context_recall:.2f}"
    )

    print(
        "Fact Coverage        :",
        f"{fact_coverage:.2f}"
    )

    print(
        "Answer Accuracy      :",
        answer_accuracy
    )

    print(
        "Response Time        :",
        f"{elapsed:.2f} sec"
    )

    print(
        "Retrieved Chunks     :",
        len(context)
    )


    return {

        "id":
            test_case["id"],

        "question":
            question,

        "policy_accuracy":
            policy_accuracy,

        "section_accuracy":
            section_accuracy,

        "context_precision":
            round(
                context_precision,
                4
            ),

        "context_recall":
            round(
                context_recall,
                4
            ),

        "fact_coverage":
            round(
                fact_coverage,
                4
            ),

        "answer_accuracy":
            answer_accuracy,

        "response_time":
            round(
                elapsed,
                4
            ),

        "context_count":
            len(context),

        "error":
            ""
    }


# ==========================================================
# SAVE CSV
# ==========================================================

def save_results(
    results,
    filename
):

    os.makedirs(
        os.path.dirname(filename),
        exist_ok=True
    )


    fieldnames = [

        "id",

        "question",

        "policy_accuracy",

        "section_accuracy",

        "context_precision",

        "context_recall",

        "fact_coverage",

        "answer_accuracy",

        "response_time",

        "context_count",

        "error"
    ]


    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            results
        )


# ==========================================================
# SUMMARY
# ==========================================================

def print_summary(results):

    if not results:

        print(
            "No evaluation results."
        )

        return


    total = len(results)


    avg_policy = (
        sum(
            r["policy_accuracy"]
            for r in results
        )
        / total
    )


    avg_section = (
        sum(
            r["section_accuracy"]
            for r in results
        )
        / total
    )


    avg_precision = (
        sum(
            r["context_precision"]
            for r in results
        )
        / total
    )


    avg_recall = (
        sum(
            r["context_recall"]
            for r in results
        )
        / total
    )


    avg_fact = (
        sum(
            r["fact_coverage"]
            for r in results
        )
        / total
    )


    avg_answer = (
        sum(
            r["answer_accuracy"]
            for r in results
        )
        / total
    )


    avg_time = (
        sum(
            r["response_time"]
            for r in results
        )
        / total
    )


    print("\n\n")

    print("=" * 80)

    print(
        "GRAPHRAG EVALUATION SUMMARY"
    )

    print("=" * 80)


    print(
        f"Total Questions       : {total}"
    )

    print(
        f"Policy Accuracy       : {avg_policy * 100:.2f}%"
    )

    print(
        f"Section Accuracy      : {avg_section * 100:.2f}%"
    )

    print(
        f"Context Precision     : {avg_precision * 100:.2f}%"
    )

    print(
        f"Context Recall        : {avg_recall * 100:.2f}%"
    )

    print(
        f"Answer Fact Coverage  : {avg_fact * 100:.2f}%"
    )

    print(
        f"Answer Accuracy       : {avg_answer * 100:.2f}%"
    )

    print(
        f"Average Response Time : {avg_time:.2f} sec"
    )

    print("=" * 80)


# ==========================================================
# MAIN
# ==========================================================

def main():

    print("\n")

    print("=" * 80)

    print(
        "BANKING GRAPHRAG EVALUATION"
    )

    print("=" * 80)


    print(
        f"\nTotal test questions: "
        f"{len(TEST_DATA)}"
    )


    # ======================================================
    # INITIALIZE GRAPHRAG
    # ======================================================

    print(
        "\nConnecting to GraphRAG..."
    )


    rag = GraphRAG()


    print(
        "GraphRAG initialized successfully."
    )


    # ======================================================
    # RUN TESTS
    # ======================================================

    results = []


    for test_case in TEST_DATA:

        result = evaluate_question(
            rag,
            test_case
        )

        results.append(
            result
        )


    # ======================================================
    # SUMMARY
    # ======================================================

    print_summary(
        results
    )


    # ======================================================
    # SAVE RESULTS
    # ======================================================

    output_file = (
        "evaluation/"
        "evaluation_results.csv"
    )


    save_results(
        results,
        output_file
    )


    print(
        f"\nResults saved to:"
        f" {output_file}"
    )


    # ======================================================
    # CLOSE GRAPHRAG
    # ======================================================

    if hasattr(
        rag,
        "close"
    ):

        rag.close()


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":

    main()