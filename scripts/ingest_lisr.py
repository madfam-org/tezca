import sys
import os
import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from apps.bluebell_lite import BluebellLite

def ingest_lisr():
    """
    Ingests the Ley del Impuesto Sobre la Renta (LISR).
    Focus on Title I (General) and Title IV (Physical Persons).
    """
    uri = "/mx/fed/ley/2013/12/11/lisr"
    pub_date = datetime.date(2013, 12, 11)
    
    print(f"Initializing Bluebell for {uri}...")
    bluebell = BluebellLite(frbr_uri=uri, title="Ley del Impuesto Sobre la Renta", date=pub_date)
    
    # Title I
    title_1 = bluebell.add_hierarchy("title", "titulo-primero", "TITULO I - DISPOSICIONES GENERALES")
    
    # Article 1: Subjects
    art_1_content = (
        "Las personas físicas y las morales están obligadas al pago del impuesto sobre la renta "
        "en los siguientes casos: "
        "I. Las residentes en México, respecto de todos sus ingresos, cualquiera que sea "
        "la ubicación de la fuente de riqueza de donde procedan."
    )
    bluebell.add_article("art-1", art_1_content, parent=title_1)

    # Title IV
    title_4 = bluebell.add_hierarchy("title", "titulo-cuarto", "TITULO IV - DE LAS PERSONAS FISICAS")
    
    # Article 90: General Dispositions for Physical Persons
    art_90_content = (
        "Están obligadas al pago del impuesto establecido en este Título, las personas físicas "
        "residentes en México que obtengan ingresos en efectivo, en bienes, devengado cuando, "
        "en los términos de este Título, señale, en crédito, en servicios en los casos que "
        "señale esta Ley, o de cualquier otro tipo."
    )
    bluebell.add_article("art-90", art_90_content, parent=title_4)

    output_path = "data/federal/mx-fed-lisr.xml"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Writing to {output_path}...")
    with open(output_path, "w") as f:
        f.write(bluebell.to_xml_string())
    
    print("Done.")

if __name__ == "__main__":
    ingest_lisr()
