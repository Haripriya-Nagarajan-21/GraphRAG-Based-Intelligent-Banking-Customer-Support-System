from neo4j import GraphDatabase

from config import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD
)


def clear_graph():

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(
            NEO4J_USER,
            NEO4J_PASSWORD
        )
    )

    try:

        with driver.session() as session:

            session.run(
                """
                MATCH (n)
                DETACH DELETE n
                """
            )

        print("Neo4j graph cleared successfully.")

    finally:

        driver.close()


if __name__ == "__main__":
    clear_graph()