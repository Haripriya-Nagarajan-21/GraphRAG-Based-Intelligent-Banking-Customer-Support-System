from dataclasses import dataclass


@dataclass
class Relationship:
    """
    Represents a relationship between two graph entities.
    """

    source: str
    relation: str
    target: str