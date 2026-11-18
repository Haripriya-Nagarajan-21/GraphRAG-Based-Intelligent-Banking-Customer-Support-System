from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class Neo4jManager:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self):
        if self.driver:
            self.driver.close()

    def test_connection(self):
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 'Neo4j Connected Successfully!' AS message")
                return result.single()["message"]
        except Exception as e:
            return f"Connection Failed: {e}"


if __name__ == "__main__":
    db = Neo4jManager()

    print(db.test_connection())

    db.close()