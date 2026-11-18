from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class GraphStatistics:
    """
    Retrieves metadata and count statistics from the Neo4j graph.
    """

    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def get_stats(self) -> dict:
        """
        Query Neo4j to count node labels and relationship types.

        Returns
        -------
        dict
            A dictionary containing counts of nodes and relationships.
        """
        stats = {
            "node_counts": {},
            "relationship_counts": {},
            "total_nodes": 0,
            "total_relationships": 0,
            "connected": False
        }
        try:
            with self.driver.session() as session:
                # Test connection and get node label counts
                node_result = session.run(
                    "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count"
                )
                for record in node_result:
                    label = record["label"] or "Unlabeled"
                    count = record["count"]
                    stats["node_counts"][label] = count
                    stats["total_nodes"] += count

                # Get relationship type counts
                rel_result = session.run(
                    "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(*) AS count"
                )
                for record in rel_result:
                    rel_type = record["rel_type"]
                    count = record["count"]
                    stats["relationship_counts"][rel_type] = count
                    stats["total_relationships"] += count

                stats["connected"] = True
        except Exception as e:
            print(f"Error fetching graph stats: {e}")
            stats["connected"] = False
        return stats
