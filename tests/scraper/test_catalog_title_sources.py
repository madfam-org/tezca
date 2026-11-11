"""The catalog spider and the registry loader hand out clean law names."""

import json

from apps.scraper.federal import catalog_spider
from apps.scraper.utils.law_registry import LawRegistry

TITLE = "LEY Federal de Protección de Datos Personales en Posesión de los Particulares"


def test_spider_keeps_date_and_marker_out_of_the_name(tmp_path):
    html = f"""
    <html><body><table>
      <tr>
        <td>{TITLE}
            <br>\t\t\t\t \t\t\t\tDOF 20/03/2025
            <br>\t\t\t\t \t\t\t\tNueva reforma</td>
        <td><a href="pdf/LFPDPPP.pdf">PDF</a></td>
      </tr>
    </table></body></html>
    """
    path = tmp_path / "index.htm"
    path.write_text(html, encoding="iso-8859-1")

    (law,) = catalog_spider.fetch_catalog(local_file=str(path))

    assert law["id"] == "lfpdppp"
    assert law["name"] == TITLE
    assert law["publication_date"] == "2025-03-20"
    assert law["catalog_notes"] == ["Nueva reforma"]


def test_registry_cleans_names_on_load(tmp_path):
    raw = f"{TITLE} \t\t\t\t \t\t\t\tDOF 20/03/2025 \t\t\t\t \t\t\t\tNueva reforma"
    registry_path = tmp_path / "law_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "federal_laws": [
                    {
                        "id": "lfpdppp",
                        "name": raw,
                        "short_name": raw[:50] + "...",
                        "publication_date": "2025-03-20",
                    },
                    {"id": "amparo", "name": "Ley de Amparo", "short_name": "Amparo"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    registry = LawRegistry(registry_path=registry_path)

    entry = registry.get_by_id("lfpdppp")
    assert entry["name"] == TITLE
    assert "\t" not in entry["short_name"]
    assert entry["short_name"] == TITLE[:50] + "..."
    assert registry.get_by_id("amparo")["short_name"] == "Amparo"
