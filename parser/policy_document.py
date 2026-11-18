from dataclasses import dataclass, field
from typing import List


@dataclass
class DocumentItem:
    """
    Actual documents like PAN Card, Aadhaar
    """
    name: str
    description: str = ""


@dataclass
class DocumentCategory:
    """
    Identity Proof, Address Proof etc.
    """
    name: str
    documents: List[DocumentItem] = field(default_factory=list)


@dataclass
class Section:
    """
    Main document sections
    """
    name: str
    content: str = ""
    categories: List[DocumentCategory] = field(default_factory=list)



class SectionList(list):
    """
    Custom list subclass that allows string-based indexing to find a section by its name.
    """
    def __getitem__(self, key):
        if isinstance(key, str):
            for s in self:
                if s.name == key:
                    return s
            raise KeyError(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


@dataclass
class PolicyDocument:

    document_name: str
    document_id: str
    version: str
    department: str
    category: str

    sections: List[Section] = field(default_factory=SectionList)