from dataclasses import dataclass


@dataclass
class Entity:
    """
    Represents an entity extracted from a banking policy.
    """

    entity_type: str
    name: str
    value: str | None = None