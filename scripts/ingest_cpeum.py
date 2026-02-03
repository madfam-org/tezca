import sys
import os
import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from apps.bluebell_lite import BluebellLite

def ingest_cpeum():
    """
    Ingests the Constitution (CPEUM) with a sample Article 1.
    """
    uri = "/mx/fed/const/1917/02/05/cpeum"
    pub_date = datetime.date(1917, 2, 5)
    
    # Text of Article 1 (Shortened for example)
    art_1_text = (
        "En los Estados Unidos Mexicanos todas las personas gozarán de los derechos humanos "
        "reconocidos en esta Constitución y en los tratados internacionales de los que el "
        "Estado Mexicano sea parte, así como de las garantías para su protección, "
        "cuyo ejercicio no podrá restringirse ni suspenderse, salvo en los casos y bajo "
        "las condiciones que esta Constitución establece."
    )

    print(f"Initializing Bluebell for {uri}...")
    bluebell = BluebellLite(frbr_uri=uri, title="Constitución Política de los Estados Unidos Mexicanos", date=pub_date)
    
    print("Adding Article 1...")
    bluebell.add_article("art-1", art_1_text)

    output_path = "data/federal/mx-fed-const-cpeum.xml"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Writing to {output_path}...")
    with open(output_path, "w") as f:
        f.write(bluebell.to_xml_string())
    
    print("Done.")

if __name__ == "__main__":
    ingest_cpeum()
