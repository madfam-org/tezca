import sys
import os
import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from apps.parsers.bluebell import BluebellLite

def ingest_ccf():
    """
    Ingests the Código Civil Federal (CCF) - Book 1.
    """
    uri = "/mx/fed/ley/1928/08/31/ccf"
    pub_date = datetime.date(1928, 8, 31)
    
    print(f"Initializing Bluebell for {uri}...")
    bluebell = BluebellLite(frbr_uri=uri, title="Código Civil Federal", date=pub_date)
    
    # Structure: Book > Title > Article
    book_1 = bluebell.add_hierarchy("book", "libro-primero", "LIBRO PRIMERO - DE LAS PERSONAS")
    title_1 = bluebell.add_hierarchy("title", "titulo-primero", "DE LAS PERSONAS FISICAS")

    # In a real scenario, this data comes from the scraper/parser
    articles = [
        ("art-22", "La capacidad jurídica de las personas físicas se adquiere por el nacimiento y se pierde por la muerte; pero desde el momento en que un individuo es concebido, entra bajo la protección de la ley..."),
        ("art-23", "La minoría de edad, el estado de interdicción y demás incapacidades establecidas por la ley, son restricciones a la personalidad jurídica..."),
        ("art-24", "El mayor de edad tiene la facultad de disponer libremente de su persona y de sus bienes, salvo las limitaciones que establece la ley.")
    ]

    for art_id, content in articles:
        print(f"Adding {art_id}...")
        # Note: In this lite version, we aren't strict about nesting articles inside Titles in the XML tree 
        # because add_hierarchy creates siblings in body. 
        # A full version would manage the tree pointer.
        bluebell.add_article(art_id, content)

    output_path = "data/federal/mx-fed-ccf.xml"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Writing to {output_path}...")
    with open(output_path, "w") as f:
        f.write(bluebell.to_xml_string())
    
    print("Done.")

if __name__ == "__main__":
    ingest_ccf()
