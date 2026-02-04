from datetime import datetime

from src.core.models import ListingData


class TestListingDataDefaults:
    def test_default_values(self):
        listing = ListingData(site="testsite")

        assert listing.raw_title == ""
        assert listing.raw_description is None
        assert listing.price is None
        assert listing.original_currency == ""
        assert listing.offer_type == ""
        assert listing.property_type == ""
        assert listing.city == ""
        assert listing.neighborhood == ""
        assert listing.agency is None
        assert listing.agency_url is None
        assert listing.details_url == ""
        assert listing.num_photos is None
        assert listing.date_time_added is None
        assert listing.search_url is None
        assert listing.site == "testsite"
        assert listing.total_offers is None
        assert listing.ref_no == ""
        assert listing.price_per_m2 is None
        assert listing.area is None
        assert listing.floor is None
        assert listing.fingerprint_hash == ""


class TestListingDataWithValues:
    def test_with_all_values(self):
        now = datetime.now()
        listing = ListingData(
            site="imotbg",
            raw_title="Двустаен апартамент",
            raw_description="Описание",
            price=150000.0,
            original_currency="EUR",
            offer_type="продава",
            property_type="двустаен",
            city="София",
            neighborhood="Лозенец",
            agency="Агенция Имоти",
            agency_url="https://agency.bg",
            details_url="https://site.bg/listing/123",
            num_photos=10,
            date_time_added=now,
            search_url="https://site.bg/search",
            total_offers=500,
            ref_no="ABC123",
            price_per_m2=2500.0,
            area=65.0,
            floor="5",
        )

        assert listing.raw_title == "Двустаен апартамент"
        assert listing.price == 150000.0
        assert listing.original_currency == "EUR"
        assert listing.city == "София"
        assert listing.neighborhood == "Лозенец"
        assert listing.num_photos == 10
        assert listing.date_time_added == now


class TestListingDataValidation:
    def test_accepts_empty_string_defaults(self):
        listing = ListingData(site="testsite", raw_title="", price=0.0)

        assert listing.raw_title == ""
        assert listing.price == 0.0

    def test_date_time_added_accepts_none(self):
        listing = ListingData(site="testsite", date_time_added=None)
        assert listing.date_time_added is None

    def test_model_dump(self):
        listing = ListingData(site="testsite", raw_title="Test", price=100.0)
        data = listing.model_dump()

        assert isinstance(data, dict)
        assert data["raw_title"] == "Test"
        assert data["price"] == 100.0
        assert data["site"] == "testsite"


# =============================================================================
# Fingerprint Tests
# =============================================================================


class TestListingDataFingerprint:
    def test_fingerprint_basic(self):
        """Test basic fingerprint generation."""
        listing = ListingData(
            site="testsite",
            price=150000.0,
            area=65.0,
            property_type="двустаен",
            city="София",
        )
        fp = listing.fingerprint()

        # Price rounded to 100, area as int
        assert fp == "150000|65|двустаен|София"

    def test_fingerprint_price_rounding(self):
        """Test price is rounded to nearest 100."""
        listing1 = ListingData(site="testsite", price=150049.0, area=65.0, property_type="двустаен", city="София")
        listing2 = ListingData(site="testsite", price=150051.0, area=65.0, property_type="двустаен", city="София")

        # 150049 rounds to 150000, 150051 rounds to 150100
        assert listing1.fingerprint() == "150000|65|двустаен|София"
        assert listing2.fingerprint() == "150100|65|двустаен|София"

    def test_fingerprint_area_normalization(self):
        """Test area is normalized to integer."""
        listing = ListingData(site="testsite", price=100000.0, area=65.5, property_type="тристаен", city="Пловдив")
        fp = listing.fingerprint()

        assert fp == "100000|65|тристаен|Пловдив"

    def test_fingerprint_missing_price(self):
        """Test fingerprint with missing price."""
        listing = ListingData(site="testsite", area=65.0, property_type="двустаен", city="София")
        fp = listing.fingerprint()

        assert fp == "|65|двустаен|София"

    def test_fingerprint_missing_area(self):
        """Test fingerprint with missing area."""
        listing = ListingData(site="testsite", price=100000.0, property_type="двустаен", city="София")
        fp = listing.fingerprint()

        assert fp == "100000||двустаен|София"


class TestListingDataMatches:
    def test_matches_same_fingerprint(self):
        """Test matches returns True for same fingerprint."""
        listing1 = ListingData(site="testsite", price=150000.0, area=65.0, property_type="двустаен", city="София")
        listing2 = ListingData(site="testsite", price=150000.0, area=65.0, property_type="двустаен", city="София")

        assert listing1.matches(listing2) is True

    def test_matches_different_fingerprint(self):
        """Test matches returns False for different fingerprint."""
        listing1 = ListingData(site="testsite", price=150000.0, area=65.0, property_type="двустаен", city="София")
        listing2 = ListingData(site="testsite", price=200000.0, area=65.0, property_type="двустаен", city="София")

        assert listing1.matches(listing2) is False

    def test_matches_with_price_tolerance(self):
        """Test that similar prices match due to rounding."""
        listing1 = ListingData(site="testsite", price=150010.0, area=65.0, property_type="двустаен", city="София")
        listing2 = ListingData(site="testsite", price=150049.0, area=65.0, property_type="двустаен", city="София")

        # Both round to 150000
        assert listing1.matches(listing2) is True
