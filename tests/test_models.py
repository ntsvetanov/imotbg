from datetime import datetime

from src.core.models import ListingData


class TestListingDataDefaults:
    def test_default_values(self):
        listing = ListingData()

        assert listing.raw_title == ""
        assert listing.raw_description == ""
        assert listing.price == 0.0
        assert listing.currency == ""
        assert listing.without_dds is False
        assert listing.offer_type == ""
        assert listing.property_type == ""
        assert listing.city == ""
        assert listing.neighborhood == ""
        assert listing.contact_info == ""
        assert listing.agency == ""
        assert listing.agency_url == ""
        assert listing.details_url == ""
        assert listing.num_photos == 0
        assert listing.date_time_added is None
        assert listing.search_url == ""
        assert listing.site == ""
        assert listing.total_offers == 0
        assert listing.ref_no == ""
        assert listing.time == ""
        assert listing.price_per_m2 == ""
        assert listing.area == ""
        assert listing.floor == ""


class TestListingDataWithValues:
    def test_with_all_values(self):
        now = datetime.now()
        listing = ListingData(
            raw_title="Двустаен апартамент",
            raw_description="Описание",
            price=150000.0,
            currency="EUR",
            without_dds=True,
            offer_type="продава",
            property_type="двустаен",
            city="София",
            neighborhood="Лозенец",
            contact_info="0888123456",
            agency="Агенция Имоти",
            agency_url="https://agency.bg",
            details_url="https://site.bg/listing/123",
            num_photos=10,
            date_time_added=now,
            search_url="https://site.bg/search",
            site="imotbg",
            total_offers=500,
            ref_no="ABC123",
            time="2024-01-15",
            price_per_m2="2500",
            area="65 кв.м",
            floor="5",
        )

        assert listing.raw_title == "Двустаен апартамент"
        assert listing.price == 150000.0
        assert listing.currency == "EUR"
        assert listing.without_dds is True
        assert listing.city == "София"
        assert listing.neighborhood == "Лозенец"
        assert listing.num_photos == 10
        assert listing.date_time_added == now


class TestListingDataValidation:
    def test_accepts_empty_string_defaults(self):
        listing = ListingData(raw_title="", price=0.0)

        assert listing.raw_title == ""
        assert listing.price == 0.0

    def test_date_time_added_accepts_none(self):
        listing = ListingData(date_time_added=None)
        assert listing.date_time_added is None

    def test_model_dump(self):
        listing = ListingData(raw_title="Test", price=100.0)
        data = listing.model_dump()

        assert isinstance(data, dict)
        assert data["raw_title"] == "Test"
        assert data["price"] == 100.0
