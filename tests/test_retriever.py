from graph.retriever import GraphRetriever


retriever = GraphRetriever()


questions = [

    "What is the interest rate for education loan?",

    "What documents are required for a home loan?",

    "What is the maximum loan amount for education loan?",

    "Is collateral required for education loan?"

]


for question in questions:

    print("\n")
    print("=" * 80)
    print("QUESTION:", question)
    print("=" * 80)

    context = retriever.retrieve(question)

    print("\nRESULT COUNT:", len(context))

    for item in context:

        print("\nPolicy :", item["policy"])
        print("Section:", item["section"])

        if item.get("category"):
            print("Category:", item["category"])

        print("Content:")
        print(item["content"])

        print("Entities:")

        for entity in item["entities"]:

            print(entity)


retriever.close()