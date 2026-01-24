"""
Tests for the normalization module.

These tests verify the enum-based normalization system for property listing data.
"""

import pytest

from src.core.enums import (
    City,
    Currency,
    OfferType,
    PlovdivNeighborhood,
    PropertyType,
    SofiaNeighborhood,
)
from src.core.normalization import (
    CURRENCY_ALIASES,
    clear_unknown_values,
    get_unknown_values,
    normalize_agency,
    normalize_city,
    normalize_currency,
    normalize_neighborhood,
    normalize_offer_type,
    normalize_property_type,
)


# =============================================================================
# Tests for Issue #1: Missing "студио" alias
# =============================================================================


class TestPropertyTypeStudioAlias:
    """Tests for the 'студио' property type alias fix."""

    def test_normalize_property_type_studio_bulgarian(self):
        """Test that 'студио' is recognized as STUDIO."""
        result = normalize_property_type("Модерно студио под наем")
        assert result == PropertyType.STUDIO

    def test_normalize_property_type_studio_standalone(self):
        """Test that standalone 'студио' is recognized."""
        result = normalize_property_type("студио")
        assert result == PropertyType.STUDIO

    def test_normalize_property_type_studio_url(self):
        """Test that 'studio' in URL is recognized."""
        result = normalize_property_type("", "https://example.com/studio-apartment")
        assert result == PropertyType.STUDIO

    def test_normalize_property_type_ednostaen_still_works(self):
        """Test that 'едностаен' maps to ONE_ROOM."""
        result = normalize_property_type("Продава ЕДНОСТАЕН апартамент")
        assert result == PropertyType.ONE_ROOM

    def test_normalize_property_type_studio_case_insensitive(self):
        """Test that 'СТУДИО' (uppercase) is recognized."""
        result = normalize_property_type("СТУДИО В ЦЕНТЪРА")
        assert result == PropertyType.STUDIO


# =============================================================================
# Tests for Issue #2: Duplicate KNIAJEVO enum removed
# =============================================================================


class TestSofiaNeighborhoodUniqueValues:
    """Tests to ensure SofiaNeighborhood enum values are unique."""

    def test_sofia_neighborhood_values_are_unique(self):
        """Verify all SofiaNeighborhood enum values are unique."""
        values = [e.value for e in SofiaNeighborhood]
        assert len(values) == len(set(values)), "Duplicate values found in SofiaNeighborhood"

    def test_knyazhevo_exists(self):
        """Verify KNYAZHEVO enum exists."""
        assert hasattr(SofiaNeighborhood, "KNYAZHEVO")
        assert SofiaNeighborhood.KNYAZHEVO.value == "Княжево"

    def test_kniajevo_does_not_exist(self):
        """Verify duplicate KNIAJEVO was removed."""
        assert not hasattr(SofiaNeighborhood, "KNIAJEVO")


class TestPlovdivNeighborhoodUniqueValues:
    """Tests to ensure PlovdivNeighborhood enum values are unique."""

    def test_plovdiv_neighborhood_values_are_unique(self):
        """Verify all PlovdivNeighborhood enum values are unique."""
        values = [e.value for e in PlovdivNeighborhood]
        assert len(values) == len(set(values)), "Duplicate values found in PlovdivNeighborhood"


# =============================================================================
# Tests for Issue #3: NADEJDA -> NADEZHDA spelling consistency
# =============================================================================


class TestNadezhdaSpellingConsistency:
    """Tests for consistent NADEZHDA spelling in enums."""

    def test_nadezhda_base_exists(self):
        """Verify NADEZHDA base enum exists."""
        assert hasattr(SofiaNeighborhood, "NADEZHDA")
        assert SofiaNeighborhood.NADEZHDA.value == "Надежда"

    def test_nadezhda_1_exists_with_correct_spelling(self):
        """Verify NADEZHDA_1 exists (not NADEJDA_1)."""
        assert hasattr(SofiaNeighborhood, "NADEZHDA_1")
        assert SofiaNeighborhood.NADEZHDA_1.value == "Надежда 1"

    def test_nadezhda_2_exists_with_correct_spelling(self):
        """Verify NADEZHDA_2 exists (not NADEJDA_2)."""
        assert hasattr(SofiaNeighborhood, "NADEZHDA_2")
        assert SofiaNeighborhood.NADEZHDA_2.value == "Надежда 2"

    def test_nadezhda_3_exists_with_correct_spelling(self):
        """Verify NADEZHDA_3 exists (not NADEJDA_3)."""
        assert hasattr(SofiaNeighborhood, "NADEZHDA_3")
        assert SofiaNeighborhood.NADEZHDA_3.value == "Надежда 3"

    def test_nadezhda_4_exists_with_correct_spelling(self):
        """Verify NADEZHDA_4 exists (not NADEJDA_4)."""
        assert hasattr(SofiaNeighborhood, "NADEZHDA_4")
        assert SofiaNeighborhood.NADEZHDA_4.value == "Надежда 4"

    def test_old_nadejda_names_do_not_exist(self):
        """Verify old NADEJDA_* names were removed."""
        assert not hasattr(SofiaNeighborhood, "NADEJDA_1")
        assert not hasattr(SofiaNeighborhood, "NADEJDA_2")
        assert not hasattr(SofiaNeighborhood, "NADEJDA_3")
        assert not hasattr(SofiaNeighborhood, "NADEJDA_4")

    def test_normalize_nadezhda_1(self):
        """Test that 'надежда 1' normalizes to NADEZHDA_1."""
        result = normalize_neighborhood("надежда 1", City.SOFIA)
        assert result == SofiaNeighborhood.NADEZHDA_1

    def test_normalize_nadezhda_variants(self):
        """Test normalization of all Nadezhda variants."""
        assert normalize_neighborhood("надежда 2", City.SOFIA) == SofiaNeighborhood.NADEZHDA_2
        assert normalize_neighborhood("надежда 3", City.SOFIA) == SofiaNeighborhood.NADEZHDA_3
        assert normalize_neighborhood("надежда 4", City.SOFIA) == SofiaNeighborhood.NADEZHDA_4


# =============================================================================
# Tests for Issue #5: normalize_currency uses CURRENCY_ALIASES
# =============================================================================


class TestNormalizeCurrencyUsesAliases:
    """Tests to verify normalize_currency uses CURRENCY_ALIASES dict."""

    def test_all_eur_aliases_recognized(self):
        """Test that all EUR aliases from CURRENCY_ALIASES are recognized."""
        eur_aliases = [k for k, v in CURRENCY_ALIASES.items() if v == Currency.EUR]
        for alias in eur_aliases:
            result = normalize_currency(f"100 {alias}")
            assert result == Currency.EUR, f"EUR alias '{alias}' not recognized"

    def test_all_bgn_aliases_recognized(self):
        """Test that all BGN aliases from CURRENCY_ALIASES are recognized."""
        bgn_aliases = [k for k, v in CURRENCY_ALIASES.items() if v == Currency.BGN]
        for alias in bgn_aliases:
            # Only test BGN when no EUR is present
            result = normalize_currency(f"100 {alias}")
            assert result == Currency.BGN, f"BGN alias '{alias}' not recognized"

    def test_eur_prioritized_over_bgn(self):
        """Test that EUR is detected first when both currencies present."""
        result = normalize_currency("179 000 €350 093 лв.")
        assert result == Currency.EUR

    def test_currency_empty_input(self):
        """Test that empty input returns empty string."""
        assert normalize_currency("") == ""
        assert normalize_currency(None) == ""

    def test_currency_no_match(self):
        """Test that unknown currency returns empty string."""
        assert normalize_currency("100 USD") == ""


# =============================================================================
# Tests for Unknown Value Tracking
# =============================================================================


class TestUnknownValueTracking:
    """Tests for the unknown value tracking system."""

    def setup_method(self):
        """Clear unknown values before each test."""
        clear_unknown_values()

    def test_clear_unknown_values(self):
        """Test that clear_unknown_values() clears the tracker."""
        # Generate some unknown values
        normalize_offer_type("unknown offer type")
        normalize_city("Unknown City XYZ")

        # Verify they were tracked
        assert len(get_unknown_values()) > 0

        # Clear and verify
        clear_unknown_values()
        assert get_unknown_values() == {}

    def test_get_unknown_values_returns_dict(self):
        """Test that get_unknown_values() returns correct structure."""
        result = get_unknown_values()
        assert isinstance(result, dict)

    def test_unknown_offer_type_tracked(self):
        """Test that unrecognized offer types are tracked."""
        clear_unknown_values()
        normalize_offer_type("търси имот")  # "looking for property" - not a valid offer type

        unknown = get_unknown_values()
        assert "offer_type" in unknown
        assert "търси имот" in unknown["offer_type"]

    def test_unknown_city_tracked(self):
        """Test that unrecognized cities are tracked."""
        clear_unknown_values()
        normalize_city("Непознат град")  # "Unknown city"

        unknown = get_unknown_values()
        assert "city" in unknown

    def test_unknown_property_type_tracked(self):
        """Test that unrecognized property types are tracked."""
        clear_unknown_values()
        normalize_property_type("непознат тип имот")

        unknown = get_unknown_values()
        assert "property_type" in unknown

    def test_known_values_not_tracked(self):
        """Test that known/matched values are NOT tracked as unknown."""
        clear_unknown_values()
        normalize_offer_type("продава")
        normalize_city("София")
        normalize_property_type("двустаен")

        unknown = get_unknown_values()
        # Should be empty since all values were recognized
        assert unknown == {} or all(len(v) == 0 for v in unknown.values())


# =============================================================================
# Tests for City-Aware Neighborhood Normalization
# =============================================================================


class TestCityAwareNeighborhoodNormalization:
    """Tests for city-aware neighborhood normalization."""

    def test_center_in_sofia_returns_sofia_center(self):
        """Test that 'Център' in Sofia returns SofiaNeighborhood.CENTER."""
        result = normalize_neighborhood("Център", City.SOFIA)
        assert result == SofiaNeighborhood.CENTER

    def test_center_in_plovdiv_returns_plovdiv_center(self):
        """Test that 'Център' in Plovdiv returns PlovdivNeighborhood.CENTER."""
        result = normalize_neighborhood("Център", City.PLOVDIV)
        assert result == PlovdivNeighborhood.CENTER

    def test_lozenets_in_sofia(self):
        """Test Sofia-specific neighborhood 'Лозенец'."""
        result = normalize_neighborhood("Лозенец", City.SOFIA)
        assert result == SofiaNeighborhood.LOZENETS

    def test_trakia_in_plovdiv(self):
        """Test Plovdiv-specific neighborhood 'Тракия'."""
        result = normalize_neighborhood("Тракия", City.PLOVDIV)
        assert result == PlovdivNeighborhood.TRAKIA

    def test_neighborhood_without_city_tries_sofia_first(self):
        """Test that without city context, Sofia neighborhoods are tried first."""
        # Лозенец only exists in Sofia
        result = normalize_neighborhood("Лозенец")
        assert result == SofiaNeighborhood.LOZENETS

    def test_neighborhood_without_city_finds_plovdiv(self):
        """Test that Plovdiv-only neighborhoods are found without city context."""
        # Тракия only exists in Plovdiv
        result = normalize_neighborhood("Тракия")
        assert result == PlovdivNeighborhood.TRAKIA

    def test_neighborhood_with_kv_prefix(self):
        """Test that 'кв.' prefix is stripped."""
        result = normalize_neighborhood("кв. Лозенец", City.SOFIA)
        assert result == SofiaNeighborhood.LOZENETS

    def test_neighborhood_with_jk_prefix(self):
        """Test that 'ж.к.' prefix is stripped."""
        result = normalize_neighborhood("ж.к. Младост", City.SOFIA)
        assert result == SofiaNeighborhood.MLADOST

    def test_neighborhood_city_string_sofia(self):
        """Test city detection from string containing 'соф'."""
        result = normalize_neighborhood("Лозенец", "гр. София")
        assert result == SofiaNeighborhood.LOZENETS

    def test_neighborhood_city_string_plovdiv(self):
        """Test city detection from string containing 'плов'."""
        result = normalize_neighborhood("Тракия", "гр. Пловдив")
        assert result == PlovdivNeighborhood.TRAKIA


# =============================================================================
# Tests for Offer Type Normalization
# =============================================================================


class TestOfferTypeNormalization:
    """Tests for offer type normalization."""

    def test_normalize_offer_type_prodava(self):
        """Test 'продава' is recognized as SALE."""
        result = normalize_offer_type("Продава апартамент")
        assert result == OfferType.SALE

    def test_normalize_offer_type_naem(self):
        """Test 'наем' is recognized as RENT."""
        result = normalize_offer_type("Под наем")
        assert result == OfferType.RENT

    def test_normalize_offer_type_from_url(self):
        """Test offer type extraction from URL takes priority."""
        result = normalize_offer_type("", "https://example.com/prodava/apartment")
        assert result == OfferType.SALE

    def test_normalize_offer_type_url_rent(self):
        """Test rent detection from URL."""
        result = normalize_offer_type("", "https://example.com/naem/apartment")
        assert result == OfferType.RENT

    def test_normalize_offer_type_api_values(self):
        """Test API values like 'apartmentsell' are recognized."""
        result = normalize_offer_type("", "apartmentsell")
        assert result == OfferType.SALE

        result = normalize_offer_type("", "apartmentrent")
        assert result == OfferType.RENT


# =============================================================================
# Tests for City Normalization
# =============================================================================


class TestCityNormalization:
    """Tests for city normalization."""

    def test_normalize_city_sofia(self):
        """Test Sofia is recognized."""
        assert normalize_city("София") == City.SOFIA
        assert normalize_city("гр. София") == City.SOFIA
        assert normalize_city("град София") == City.SOFIA

    def test_normalize_city_plovdiv(self):
        """Test Plovdiv is recognized."""
        assert normalize_city("Пловдив") == City.PLOVDIV
        assert normalize_city("гр. Пловдив") == City.PLOVDIV

    def test_normalize_city_varna(self):
        """Test Varna is recognized."""
        assert normalize_city("Варна") == City.VARNA

    def test_normalize_city_burgas(self):
        """Test Burgas is recognized."""
        assert normalize_city("Бургас") == City.BURGAS

    def test_normalize_city_transliterated(self):
        """Test transliterated city names."""
        assert normalize_city("sofia") == City.SOFIA
        assert normalize_city("plovdiv") == City.PLOVDIV

    def test_normalize_city_empty(self):
        """Test empty input."""
        assert normalize_city("") == ""
        assert normalize_city(None) == ""


# =============================================================================
# Tests for Property Type Normalization (beyond studio)
# =============================================================================


class TestPropertyTypeNormalization:
    """Tests for property type normalization."""

    def test_normalize_property_type_dvustaen(self):
        """Test 'двустаен' (2-room)."""
        result = normalize_property_type("двустаен апартамент")
        assert result == PropertyType.TWO_ROOM

    def test_normalize_property_type_tristaen(self):
        """Test 'тристаен' (3-room)."""
        result = normalize_property_type("тристаен")
        assert result == PropertyType.THREE_ROOM

    def test_normalize_property_type_mezonet(self):
        """Test 'мезонет' (maisonette)."""
        result = normalize_property_type("мезонет")
        assert result == PropertyType.MAISONETTE

    def test_normalize_property_type_kashta(self):
        """Test 'къща' (house)."""
        result = normalize_property_type("къща")
        assert result == PropertyType.HOUSE

    def test_normalize_property_type_from_url(self):
        """Test property type from URL."""
        result = normalize_property_type("", "https://example.com/dvustaen-apartment")
        assert result == PropertyType.TWO_ROOM

    def test_normalize_property_type_empty(self):
        """Test empty input."""
        assert normalize_property_type("") == ""
        assert normalize_property_type(None) == ""


# =============================================================================
# Tests for normalize_agency function
# =============================================================================


class TestNormalizeAgency:
    """Tests for agency name normalization."""

    def test_normalize_agency_known_lowercase(self):
        """Test normalizing known agency in lowercase."""
        result = normalize_agency("bulgarian properties")
        assert result == "Bulgarian Properties"

    def test_normalize_agency_known_mixed_case(self):
        """Test normalizing known agency with mixed case."""
        result = normalize_agency("Bulgarian Properties")
        assert result == "Bulgarian Properties"

    def test_normalize_agency_known_variations(self):
        """Test normalizing known agency variations."""
        assert normalize_agency("suprimmo") == "Suprimmo"
        assert normalize_agency("luximmo") == "Luximmo"
        assert normalize_agency("явлена") == "Явлена"
        assert normalize_agency("yavlena") == "Явлена"

    def test_normalize_agency_century21(self):
        """Test Century 21 variations."""
        assert normalize_agency("century 21") == "Century 21"
        assert normalize_agency("century21") == "Century 21"

    def test_normalize_agency_remax(self):
        """Test RE/MAX variations."""
        assert normalize_agency("re/max") == "RE/MAX"
        assert normalize_agency("remax") == "RE/MAX"

    def test_normalize_agency_private(self):
        """Test private seller variations."""
        assert normalize_agency("частно лице") == "Частно лице"
        assert normalize_agency("частен") == "Частно лице"
        assert normalize_agency("private") == "Частно лице"

    def test_normalize_agency_unknown(self):
        """Test unknown agency is cleaned and returned."""
        result = normalize_agency("  Unknown Agency Name  ")
        assert result == "Unknown Agency Name"

    def test_normalize_agency_empty(self):
        """Test empty input returns empty string."""
        assert normalize_agency("") == ""

    def test_normalize_agency_none(self):
        """Test None input returns empty string."""
        assert normalize_agency(None) == ""

    def test_normalize_agency_whitespace(self):
        """Test whitespace is stripped."""
        result = normalize_agency("   Suprimmo   ")
        assert result == "Suprimmo"

    def test_normalize_agency_era(self):
        """Test ERA agency."""
        assert normalize_agency("era") == "ERA"

    def test_normalize_agency_arco(self):
        """Test Arco Real Estate variations."""
        assert normalize_agency("arco") == "Arco Real Estate"
        assert normalize_agency("arco real estate") == "Arco Real Estate"
