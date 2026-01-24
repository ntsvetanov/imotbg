from datetime import datetime
import hashlib

from src.core.enums import City, PropertyType
from src.core.models import ListingData


class TestListingDataDefaults:
    def test_default_values(self):
        listing = ListingData()

        assert listing.raw_title == ""
        assert listing.raw_description is None
        assert listing.price is None
        assert listing.currency == ""
        assert listing.without_dds is False
        assert listing.offer_type == ""
        assert listing.property_type == ""
        assert listing.city == ""
        assert listing.neighborhood == ""
        assert listing.contact_info is None
        assert listing.agency is None
        assert listing.agency_url is None
        assert listing.details_url == ""
        assert listing.num_photos is None
        assert listing.date_time_added is None
        assert listing.search_url is None
        assert listing.site == ""
        assert listing.total_offers is None
        assert listing.ref_no == ""
        assert listing.time == ""
        assert listing.price_per_m2 is None
        assert listing.area is None
        assert listing.floor is None


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


# =============================================================================
# Fingerprint Tests
# =============================================================================


class TestListingDataGetValue:
    def test_get_value_with_enum(self):
        """Test _get_value extracts value from enum."""
        listing = ListingData(city=City.SOFIA)
        result = listing._get_value(listing.city)
        assert result == "София"

    def test_get_value_with_string(self):
        """Test _get_value returns string as-is."""
        listing = ListingData(city="Варна")
        result = listing._get_value(listing.city)
        assert result == "Варна"

    def test_get_value_with_empty_string(self):
        """Test _get_value returns empty string for empty input."""
        listing = ListingData(city="")
        result = listing._get_value(listing.city)
        assert result == ""

    def test_get_value_with_none(self):
        """Test _get_value returns empty string for None."""
        listing = ListingData()
        result = listing._get_value(None)
        assert result == ""


class TestListingDataFingerprint:
    def test_fingerprint_basic(self):
        """Test basic fingerprint generation."""
        listing = ListingData(
            price=150000.0,
            area="65",
            property_type="двустаен",
            city="София",
        )
        fp = listing.fingerprint()

        # Price rounded to 100, area as int
        assert fp == "150000|65|двустаен|София"

    def test_fingerprint_with_enum_values(self):
        """Test fingerprint with enum values."""
        listing = ListingData(
            price=150000.0,
            area="65",
            property_type=PropertyType.TWO_ROOM,
            city=City.SOFIA,
        )
        fp = listing.fingerprint()

        assert fp == "150000|65|двустаен|София"

    def test_fingerprint_price_rounding(self):
        """Test price is rounded to nearest 100."""
        listing1 = ListingData(price=150049.0, area="65", property_type="двустаен", city="София")
        listing2 = ListingData(price=150051.0, area="65", property_type="двустаен", city="София")

        # 150049 rounds to 150000, 150051 rounds to 150100
        assert listing1.fingerprint() == "150000|65|двустаен|София"
        assert listing2.fingerprint() == "150100|65|двустаен|София"

    def test_fingerprint_area_normalization(self):
        """Test area is normalized to integer."""
        listing = ListingData(price=100000.0, area="65.5", property_type="тристаен", city="Пловдив")
        fp = listing.fingerprint()

        assert fp == "100000|65|тристаен|Пловдив"

    def test_fingerprint_area_with_text(self):
        """Test area with text falls back to string."""
        listing = ListingData(price=100000.0, area="65 кв.м.", property_type="тристаен", city="София")
        fp = listing.fingerprint()

        # Can't convert "65 кв.м." to float, keeps as string
        assert "65 кв.м." in fp

    def test_fingerprint_missing_price(self):
        """Test fingerprint with missing price."""
        listing = ListingData(area="65", property_type="двустаен", city="София")
        fp = listing.fingerprint()

        assert fp == "|65|двустаен|София"

    def test_fingerprint_missing_area(self):
        """Test fingerprint with missing area."""
        listing = ListingData(price=100000.0, property_type="двустаен", city="София")
        fp = listing.fingerprint()

        assert fp == "100000||двустаен|София"


class TestListingDataFingerprintStrict:
    def test_fingerprint_strict_includes_neighborhood(self):
        """Test strict fingerprint includes neighborhood."""
        listing = ListingData(
            price=150000.0,
            area="65",
            property_type="двустаен",
            city="София",
            neighborhood="Лозенец",
        )
        fp = listing.fingerprint_strict()

        assert fp == "150000|65|двустаен|София|Лозенец"

    def test_fingerprint_strict_empty_neighborhood(self):
        """Test strict fingerprint with empty neighborhood."""
        listing = ListingData(
            price=150000.0,
            area="65",
            property_type="двустаен",
            city="София",
        )
        fp = listing.fingerprint_strict()

        assert fp == "150000|65|двустаен|София|"


class TestListingDataFingerprintLoose:
    def test_fingerprint_loose_rounds_to_500(self):
        """Test loose fingerprint rounds price to 500."""
        listing = ListingData(
            price=150249.0,
            property_type="двустаен",
            city="София",
        )
        fp = listing.fingerprint_loose()

        # 150249 rounds to 150000
        assert fp == "150000|двустаен|София"

    def test_fingerprint_loose_rounds_up(self):
        """Test loose fingerprint rounds up when appropriate."""
        listing = ListingData(
            price=150251.0,
            property_type="двустаен",
            city="София",
        )
        fp = listing.fingerprint_loose()

        # 150251 rounds to 150500
        assert fp == "150500|двустаен|София"

    def test_fingerprint_loose_no_area(self):
        """Test loose fingerprint doesn't include area."""
        listing = ListingData(
            price=150000.0,
            area="65",
            property_type="двустаен",
            city="София",
        )
        fp = listing.fingerprint_loose()

        # Area is not in loose fingerprint
        assert "65" not in fp
        assert fp == "150000|двустаен|София"


class TestListingDataMatches:
    def test_matches_same_fingerprint(self):
        """Test matches returns True for same fingerprint."""
        listing1 = ListingData(price=150000.0, area="65", property_type="двустаен", city="София")
        listing2 = ListingData(price=150000.0, area="65", property_type="двустаен", city="София")

        assert listing1.matches(listing2) is True

    def test_matches_different_fingerprint(self):
        """Test matches returns False for different fingerprint."""
        listing1 = ListingData(price=150000.0, area="65", property_type="двустаен", city="София")
        listing2 = ListingData(price=200000.0, area="65", property_type="двустаен", city="София")

        assert listing1.matches(listing2) is False

    def test_matches_strict_same_neighborhood(self):
        """Test strict matches with same neighborhood."""
        listing1 = ListingData(
            price=150000.0, area="65", property_type="двустаен", city="София", neighborhood="Лозенец"
        )
        listing2 = ListingData(
            price=150000.0, area="65", property_type="двустаен", city="София", neighborhood="Лозенец"
        )

        assert listing1.matches(listing2, strict=True) is True

    def test_matches_strict_different_neighborhood(self):
        """Test strict matches with different neighborhood."""
        listing1 = ListingData(
            price=150000.0, area="65", property_type="двустаен", city="София", neighborhood="Лозенец"
        )
        listing2 = ListingData(price=150000.0, area="65", property_type="двустаен", city="София", neighborhood="Център")

        assert listing1.matches(listing2, strict=True) is False
        # Non-strict should still match
        assert listing1.matches(listing2, strict=False) is True

    def test_matches_with_price_tolerance(self):
        """Test that similar prices match due to rounding."""
        listing1 = ListingData(price=150010.0, area="65", property_type="двустаен", city="София")
        listing2 = ListingData(price=150049.0, area="65", property_type="двустаен", city="София")

        # Both round to 150000
        assert listing1.matches(listing2) is True


class TestListingDataFingerprintHash:
    """Tests for fingerprint_hash computed field."""

    def test_fingerprint_hash_is_md5(self):
        """Test fingerprint_hash is MD5 hash of fingerprint."""
        listing = ListingData(
            price=150000.0,
            area="65",
            property_type="двустаен",
            city="София",
        )
        expected_hash = hashlib.md5(listing.fingerprint().encode()).hexdigest()
        assert listing.fingerprint_hash == expected_hash

    def test_fingerprint_hash_length(self):
        """Test fingerprint_hash is 32 characters (MD5 hex digest)."""
        listing = ListingData(price=100000.0, area="50", property_type="студио", city="Пловдив")
        assert len(listing.fingerprint_hash) == 32

    def test_fingerprint_hash_consistency(self):
        """Test fingerprint_hash is consistent for same data."""
        listing1 = ListingData(price=150000.0, area="65", property_type="двустаен", city="София")
        listing2 = ListingData(price=150000.0, area="65", property_type="двустаен", city="София")
        assert listing1.fingerprint_hash == listing2.fingerprint_hash

    def test_fingerprint_hash_different_for_different_data(self):
        """Test fingerprint_hash differs for different fingerprints."""
        listing1 = ListingData(price=150000.0, area="65", property_type="двустаен", city="София")
        listing2 = ListingData(price=200000.0, area="65", property_type="двустаен", city="София")
        assert listing1.fingerprint_hash != listing2.fingerprint_hash

    def test_fingerprint_hash_included_in_model_dump(self):
        """Test fingerprint_hash is included in model_dump output."""
        listing = ListingData(price=100000.0, area="50", property_type="тристаен", city="Варна")
        dump = listing.model_dump()
        assert "fingerprint_hash" in dump
        assert dump["fingerprint_hash"] == listing.fingerprint_hash

    def test_fingerprint_hash_for_empty_listing(self):
        """Test fingerprint_hash works for listing with no values."""
        listing = ListingData()
        # Should not raise, should return valid hash
        assert len(listing.fingerprint_hash) == 32
        # Empty fingerprint: "|||"
        expected_hash = hashlib.md5("|||".encode()).hexdigest()
        assert listing.fingerprint_hash == expected_hash

    def test_fingerprint_hash_with_enums(self):
        """Test fingerprint_hash works with enum values."""
        listing = ListingData(
            price=150000.0,
            area="65",
            property_type=PropertyType.TWO_ROOM,
            city=City.SOFIA,
        )
        # Enum values are extracted for fingerprint
        expected_fp = "150000|65|двустаен|София"
        expected_hash = hashlib.md5(expected_fp.encode()).hexdigest()
        assert listing.fingerprint_hash == expected_hash
