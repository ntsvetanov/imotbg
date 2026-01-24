
from src.core.transforms import (
    extract_city,
    extract_currency,
    extract_neighborhood,
    extract_offer_type,
    extract_property_type,
    is_without_dds,
    parse_price,
    to_float_or_zero,
    to_float_safe,
    to_int_safe,
)


class TestParsePrice:
    def test_parse_price_eur(self):
        assert parse_price("179 000 €") == 179000.0

    def test_parse_price_bgn(self):
        assert parse_price("350 093 лв.") == 350093.0

    def test_parse_price_combined_eur_bgn(self):
        assert parse_price("179 000 €350 093.57 лв.") == 179000.0

    def test_parse_price_with_decimals(self):
        assert parse_price("1 234.56 лв.") == 123456.0

    def test_parse_price_empty(self):
        assert parse_price("") == 0.0

    def test_parse_price_none(self):
        assert parse_price(None) == 0.0

    def test_parse_price_no_numbers(self):
        assert parse_price("no price") == 0.0


class TestExtractCurrency:
    def test_extract_currency_eur_symbol(self):
        assert extract_currency("179 000 €") == "EUR"

    def test_extract_currency_eur_text(self):
        assert extract_currency("179 000 EUR") == "EUR"

    def test_extract_currency_bgn_lv(self):
        assert extract_currency("350 093 лв.") == "BGN"

    def test_extract_currency_bgn_text(self):
        assert extract_currency("100 BGN") == "BGN"

    def test_extract_currency_combined(self):
        assert extract_currency("179 000 €350 093.57 лв.") == "EUR"

    def test_extract_currency_empty(self):
        assert extract_currency("") == ""

    def test_extract_currency_none(self):
        assert extract_currency(None) == ""

    def test_extract_currency_unknown(self):
        assert extract_currency("100 USD") == ""


class TestIsWithoutDds:
    def test_is_without_dds_true(self):
        assert is_without_dds("100 000 лв. без ДДС") is True

    def test_is_without_dds_true_lowercase(self):
        assert is_without_dds("100 000 лв. без ддс") is True

    def test_is_without_dds_false(self):
        assert is_without_dds("100 000 лв.") is False

    def test_is_without_dds_empty(self):
        assert is_without_dds("") is False

    def test_is_without_dds_none(self):
        assert is_without_dds(None) is False


class TestExtractCity:
    def test_extract_city_with_grad(self):
        assert extract_city("град София, Лозенец") == "София"

    def test_extract_city_with_gr(self):
        assert extract_city("гр. Пловдив, Център") == "Пловдив"

    def test_extract_city_with_village(self):
        assert extract_city("с. Равда, Бургас") == "Равда"

    def test_extract_city_no_prefix(self):
        assert extract_city("Варна, Чайка") == "Варна"

    def test_extract_city_no_neighborhood(self):
        assert extract_city("град София") == "София"

    def test_extract_city_empty(self):
        assert extract_city("") == ""

    def test_extract_city_none(self):
        assert extract_city(None) == ""


class TestExtractNeighborhood:
    def test_extract_neighborhood(self):
        assert extract_neighborhood("град София, Лозенец") == "Лозенец"

    def test_extract_neighborhood_multiple_parts(self):
        assert extract_neighborhood("град София, Лозенец, ул. Тест") == "Лозенец"

    def test_extract_neighborhood_no_comma(self):
        assert extract_neighborhood("град София") == ""

    def test_extract_neighborhood_empty(self):
        assert extract_neighborhood("") == ""

    def test_extract_neighborhood_none(self):
        assert extract_neighborhood(None) == ""


class TestExtractPropertyType:
    def test_extract_property_type_dvustaen(self):
        assert extract_property_type("Продава 2-СТАЕН") == "двустаен"

    def test_extract_property_type_tristaen(self):
        assert extract_property_type("Продава ТРИСТАЕН") == "тристаен"

    def test_extract_property_type_mezonet(self):
        assert extract_property_type("Продава МЕЗОНЕТ") == "мезонет"

    def test_extract_property_type_zemedelska(self):
        assert extract_property_type("Продава ЗЕМЕДЕЛСКА земя") == "земя"

    def test_extract_property_type_empty(self):
        assert extract_property_type("") == ""

    def test_extract_property_type_none(self):
        assert extract_property_type(None) == ""

    def test_extract_property_type_unknown(self):
        assert extract_property_type("Продава ГАРАЖ") == ""


class TestExtractOfferType:
    def test_extract_offer_type_prodava(self):
        assert extract_offer_type("Продава 2-СТАЕН") == "продава"

    def test_extract_offer_type_naem(self):
        assert extract_offer_type("Под наем апартамент") == "наем"

    def test_extract_offer_type_empty(self):
        assert extract_offer_type("") == ""

    def test_extract_offer_type_none(self):
        assert extract_offer_type(None) == ""

    def test_extract_offer_type_unknown(self):
        assert extract_offer_type("Търси апартамент") == ""


class TestToIntSafe:
    def test_to_int_safe_number(self):
        assert to_int_safe("42") == 42

    def test_to_int_safe_with_text(self):
        assert to_int_safe("13 снимки") == 13

    def test_to_int_safe_empty(self):
        assert to_int_safe("") == 0

    def test_to_int_safe_none(self):
        assert to_int_safe(None) == 0

    def test_to_int_safe_no_digits(self):
        assert to_int_safe("no numbers") == 0


class TestToFloatSafe:
    def test_to_float_safe_integer(self):
        assert to_float_safe("42") == 42.0

    def test_to_float_safe_decimal(self):
        assert to_float_safe("3.14") == 3.14

    def test_to_float_safe_with_text(self):
        assert to_float_safe("price: 99.99 EUR") == 99.99

    def test_to_float_safe_empty(self):
        assert to_float_safe("") == 0.0

    def test_to_float_safe_none(self):
        assert to_float_safe(None) == 0.0


class TestToFloatOrZero:
    def test_float_value(self):
        assert to_float_or_zero(100.5) == 100.5

    def test_int_value(self):
        assert to_float_or_zero(100) == 100.0

    def test_string_value(self):
        assert to_float_or_zero("150000") == 150000.0

    def test_string_with_comma(self):
        assert to_float_or_zero("150,000") == 150000.0

    def test_string_with_spaces(self):
        assert to_float_or_zero("150 000") == 150000.0

    def test_empty_string(self):
        assert to_float_or_zero("") == 0.0

    def test_none_value(self):
        assert to_float_or_zero(None) == 0.0

    def test_invalid_string(self):
        assert to_float_or_zero("invalid") == 0.0

    def test_zero(self):
        assert to_float_or_zero(0) == 0.0
