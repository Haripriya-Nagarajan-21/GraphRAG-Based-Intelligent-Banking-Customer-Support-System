import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from parser.pdf_parser import PDFParser
from parser.text_cleaner import TextCleaner
from parser.section_parser import SectionParser
from graph.graph_builder import GraphBuilder


POLICY_METADATA = {
    "Home_Loan_Policy.pdf": {
        "name": "Home Loan Policy",
        "id": "HLP-001",
        "version": "1.0",
        "department": "Retail Lending",
        "category": "Lending Policy"
    },
    "Education_Loan_Policy.pdf": {
        "name": "Education Loan Policy",
        "id": "ELP-002",
        "version": "1.0",
        "department": "Retail Lending",
        "category": "Education Policy"
    },
    "General_Banking_Policy.pdf": {
        "name": "General Banking Policy",
        "id": "GBP-003",
        "version": "1.0",
        "department": "Branch Operations",
        "category": "Operational Policy"
    }
}


def ingest_all():
    print("=" * 70)
    print("STARTING BULK POLICY INGESTION")
    print("=" * 70)

    pdf_parser = PDFParser()
    cleaner = TextCleaner()
    section_parser = SectionParser()
    builder = GraphBuilder()

    policies_dir = Path("data/policies")

    for filename, meta in POLICY_METADATA.items():
        file_path = policies_dir / filename
        if not file_path.exists():
            print(f"⚠️ File not found: {file_path}")
            continue

        print(f"\nProcessing {filename}...")
        try:
            # 1. Extract text
            text = pdf_parser.extract_text(file_path)
            
            # 2. Clean text
            cleaned = cleaner.clean(text)
            
            # 3. Parse into document object
            policy = section_parser.parse(
                cleaned,
                document_name=meta["name"],
                document_id=meta["id"],
                version=meta["version"],
                department=meta["department"],
                category=meta["category"]
            )
            
            # 4. Build graph into Neo4j
            print(f"Building Knowledge Graph nodes for {meta['name']}...")
            builder.build(policy)
            print(f"Success: Ingested {meta['name']} ({meta['id']})")
        except Exception as e:
            print(f"Failed to ingest {filename}: {e}")

    builder.close()
    print("\n" + "=" * 70)
    print("BULK INGESTION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    ingest_all()
