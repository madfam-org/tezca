import os
import xml.etree.ElementTree as ET
import pytest

XML_PATH = "data/federal/mx-fed-const-cpeum.xml"

def test_xml_exists():
    assert os.path.exists(XML_PATH), f"File {XML_PATH} was not created."

def test_xml_structure():
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    
    # Check namespace
    ns = "{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}"
    assert root.tag == f"{ns}akomaNtoso"
    
    # Check for Act
    act = root.find(f"{ns}act")
    assert act is not None
    assert act.get("name") == "constitution"
    
    # Check Metadata
    meta = act.find(f"{ns}meta")
    assert meta is not None
    frbr_uri = meta.find(f".//{ns}FRBRWork/{ns}FRBRuri")
    assert frbr_uri.get("value") == "/mx/fed/const/1917/02/05/cpeum"

def test_article_1_content():
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    ns = "{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}"
    
    # Check Article 1
    art1 = root.find(f".//{ns}article[@id='art-1']")
    assert art1 is not None
    
    # Check text content contains "derechos humanos"
    content = art1.find(f".//{ns}p").text
    assert "derechos humanos" in content
