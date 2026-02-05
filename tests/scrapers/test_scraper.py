import datetime
from apps.scraper.federal.dof_daily import DofScraper

def test_scraper_initialization():
    """Test that DofScraper initializes with current date by default."""
    scraper = DofScraper()
    assert scraper.date == datetime.date.today()

def test_scraper_custom_date():
    """Test that DofScraper accepts a custom date."""
    custom_date = datetime.date(2023, 1, 1)
    scraper = DofScraper(date=custom_date)
    assert scraper.date == custom_date

def test_fetch_method_exists():
    """Test that fetch_daily_edition method exists."""
    scraper = DofScraper()
    assert hasattr(scraper, 'fetch_daily_edition')
    # Since it's a skeleton, we just check callability for now
    assert isinstance(scraper.fetch_daily_edition(), list)
