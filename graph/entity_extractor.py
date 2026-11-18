import re

from graph.models.entity import Entity


class EntityExtractor:
    """
    Extracts graph entities from a parsed PolicyDocument.
    """

    def extract(self, policy):

        entities = []

        # Policy Node
        entities.append(
            Entity(
                entity_type="Policy",
                name=policy.document_name,
                value=policy.document_id
            )
        )

        # Section Nodes
        for section in policy.sections:

            entities.append(
                Entity(
                    entity_type="Section",
                    name=section.name
                )
            )

        return entities