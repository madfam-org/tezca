import pytest
from unittest.mock import MagicMock, patch
from apps.scraper.municipal.cdmx import CDMXScraper

class TestCDMXScraper:
    
    @pytest.fixture
    def scraper(self):
        return CDMXScraper()

    @patch('apps.scraper.municipal.cdmx.CDMXScraper.fetch_page')
    def test_scrape_finds_pdf(self, mock_fetch, scraper):
        # Mock HTML with a valid PDF link and row context
        mock_fetch.return_value = """
        <html>
            <table>
                <tr>
                    <td>
                        PUBLICADO EN LA GACETA... LEY DE EDUCACIÓN DE LA CIUDAD DE MÉXICO ULTIMA REFORMA...
                        <a href="/laws/educacion.pdf">Descargar</a>
                    </td>
                </tr>
            </table>
        </html>
        """
        # Note: The scraper logic relies on finding 'LEY' in uppercase. 
        # My mock above is simple. Let's make it match the scraper's heuristic regex:
        # (LEY\s+[A-ZÁÉÍÓÚÑ"“”,\s]{15,})
        
        mock_fetch.return_value = """
        <html>
            <table>
                <tr>
                    <td>
                        PUBLICADO EN LA GACETA...
                        LEY DE EDUCACIÓN DE LA CIUDAD DE MÉXICO
                        ULTIMA REFORMA...
                        <a href="/laws/educacion.pdf">Descargar</a>
                    </td>
                </tr>
            </table>
        </html>
        """
        
        results = scraper.scrape()
        assert len(results) == 1
        assert results[0]['title'].startswith("LEY DE EDUCACIÓN")
        assert results[0]['file_url'] == "https://data.consejeria.cdmx.gob.mx/laws/educacion.pdf"
        assert results[0]['municipality'] == "Ciudad de México"

    @patch('apps.scraper.municipal.cdmx.CDMXScraper.fetch_page')
    def test_scrape_filename_fallback(self, mock_fetch, scraper):
        # Case where row text is messy or missing "LEY" title
        mock_fetch.return_value = """
        <html>
            <table>
                <tr>
                    <td>
                        Some random text
                        <a href="/laws/LEY_DE_MOVILIDAD_CDMX.pdf">Descargar</a>
                    </td>
                </tr>
            </table>
        </html>
        """
        
        results = scraper.scrape()
        assert len(results) == 1
        assert results[0]['title'] == "LEY DE MOVILIDAD CDMX"

    @patch('apps.scraper.municipal.cdmx.CDMXScraper.fetch_page')
    def test_scrape_resolves_relative_urls(self, mock_fetch, scraper):
        mock_fetch.return_value = """
        <html>
            <a href="images/leyes/2025/LEY_TEST.pdf">Link</a>
        </html>
        """
        results = scraper.scrape()
        assert len(results) == 1
        assert results[0]['file_url'] == "https://data.consejeria.cdmx.gob.mx/images/leyes/2025/LEY_TEST.pdf"
