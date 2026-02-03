import datetime
import xml.etree.ElementTree as ET
from typing import List, Dict

class BluebellLite:
    """
    A lightweight converter to Akoma Ntoso V3.
    """
    
    NS = {
        "akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance"
    }

    def __init__(self, frbr_uri: str, title: str, date: datetime.date):
        self.frbr_uri = frbr_uri
        self.title = title
        self.date = date
        self.root = ET.Element("akomaNtoso", {
            "xmlns": self.NS["akn"],
            "xmlns:xsi": self.NS["xsi"]
        })
        self.act = ET.SubElement(self.root, "act", {"name": "constitution"})
        self.meta = ET.SubElement(self.act, "meta")
        self.body = ET.SubElement(self.act, "body")
        
        self._build_meta()

    def _build_meta(self):
        """Constructs the FRBR metadata block."""
        identification = ET.SubElement(self.meta, "identification", {"source": "#antigravity"})
        
        # FRBRWork
        work = ET.SubElement(identification, "FRBRWork")
        ET.SubElement(work, "FRBRthis", {"value": f"{self.frbr_uri}/main"})
        ET.SubElement(work, "FRBRuri", {"value": self.frbr_uri})
        ET.SubElement(work, "FRBRdate", {"date": self.date.isoformat(), "name": "Generation"})
        ET.SubElement(work, "FRBRauthor", {"href": "#congress"})
        ET.SubElement(work, "FRBRcountry", {"value": "mx"})
        
        # FRBRExpression
        exp = ET.SubElement(identification, "FRBRExpression")
        ET.SubElement(exp, "FRBRthis", {"value": f"{self.frbr_uri}/spa@/main"})
        ET.SubElement(exp, "FRBRuri", {"value": f"{self.frbr_uri}/spa@"})
        ET.SubElement(exp, "FRBRdate", {"date": self.date.isoformat(), "name": "Generation"})
        ET.SubElement(exp, "FRBRauthor", {"href": "#antigravity"})
        ET.SubElement(exp, "FRBRlanguage", {"language": "spa"})

        # FRBRManifestation
        man = ET.SubElement(identification, "FRBRManifestation")
        ET.SubElement(man, "FRBRthis", {"value": f"{self.frbr_uri}/spa@/main.xml"})
        ET.SubElement(man, "FRBRuri", {"value": f"{self.frbr_uri}/spa@.akn"})
        ET.SubElement(man, "FRBRdate", {"date": datetime.date.today().isoformat(), "name": "Generation"})
        ET.SubElement(man, "FRBRauthor", {"href": "#antigravity"})

    def add_hierarchy(self, name: str, id: str, title: str):
        """Adds a hierarchical container (Book, Title, Chapter) to the body."""
        # For simplicity in this lite version, we append directly to body
        # In a real version, we'd track the current parent node
        container = ET.SubElement(self.body, name, {"id": id})
        ET.SubElement(container, "num", {"title": id}).text = title
        return container

    def add_article(self, id: str, content: str, parent=None):
        """Adds an article to the body or a specific parent."""
        target = parent if parent is not None else self.body
        article = ET.SubElement(target, "article", {"id": id})
        ET.SubElement(article, "num", {"title": id}).text = id.replace("-", " ").upper()
        
        paragraph = ET.SubElement(article, "paragraph", {"id": f"{id}-para-1"})
        content_tag = ET.SubElement(paragraph, "content")
        p = ET.SubElement(content_tag, "p")
        p.text = content
        return article

    def to_xml_string(self) -> str:
        """Returns the prettified XML string."""
        # Note: simplistic string generation for lack of lxml in default python
        raw = ET.tostring(self.root, encoding="utf-8").decode("utf-8")
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{raw}'
