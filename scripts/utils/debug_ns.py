import sys

from lxml import etree

xml_path = "data/federal/mx-fed-cff-v2.xml"
tree = etree.parse(xml_path)
root = tree.getroot()
ns = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}

print(f"Root tag: {root.tag}")
articles = root.findall(".//akn:article", ns)
print(f"Found {len(articles)} articles with namespace")

# Try without namespace (wildcard)
articles_wild = root.findall(".//*[local-name()='article']")
print(f"Found {len(articles_wild)} articles with local-name wildcard")

# Print first article tag if found
if articles_wild:
    print(f"First article tag: {articles_wild[0].tag}")
