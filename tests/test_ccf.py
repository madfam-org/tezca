import os
import xml.etree.ElementTree as ET

XML_PATH = "data/federal/mx-fed-ccf.xml"

def test_ccf_exists():
    assert os.path.exists(XML_PATH)

def test_ccf_structure():
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    ns = "{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}"
    
    # Check FRBR URI for CCF
    meta = root.find(f".//{ns}FRBRWork/{ns}FRBRuri")
    assert meta.get("value") == "/mx/fed/ley/1928/08/31/ccf"

    # Check for Article 22 (Personas Fisicas)
    art22 = root.find(f".//{ns}article[@id='art-22']")
    assert art22 is not None
    assert "capacidad jurídica" in art22.find(f".//{ns}p").text

    # Check for Book 1
    book1 = root.find(f".//{ns}book[@id='libro-primero']")
    assert book1 is not None
