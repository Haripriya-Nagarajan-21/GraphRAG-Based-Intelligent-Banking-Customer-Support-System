from graph.enrichers.entity_manager import BankingEntityManager


manager = BankingEntityManager()


text = """
Applicants must be at least 21 years of age.

Maximum age for salaried applicants is 60 years.

Maximum age for self-employed applicants is 65 years.

Salaried and self-employed individuals are eligible.

Applicants must have a minimum CIBIL score of 750.

Indian citizens and NRIs can apply.
"""


entities = manager.extract(
    "Eligibility Criteria",
    text
)


print("\nExtracted Entities")
print("=" * 50)

for entity in entities:
    print(entity)