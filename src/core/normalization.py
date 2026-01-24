"""
Normalization module for property listing data.

Provides alias mappings and normalization functions to convert
various input formats (from different sites, URLs, transliterations)
to standardized enum values.

Features:
- Soft validation: returns original value if no match found
- Unknown value tracking: collects unmatched values for review
- URL + text parsing: tries URL patterns first, then text content
"""

import re
from collections import defaultdict
from enum import Enum
from typing import TypeVar

from src.core.enums import (
    City,
    Currency,
    OfferType,
    PlovdivNeighborhood,
    PropertyType,
    SofiaNeighborhood,
)
from src.logger_setup import get_logger

logger = get_logger(__name__)

# Track unknown values during session
_unknown_values: dict[str, set[str]] = defaultdict(set)

T = TypeVar("T", bound=Enum)

# =============================================================================
# OFFER TYPE ALIASES
# =============================================================================

OFFER_TYPE_ALIASES: dict[str, OfferType] = {
    # Bulgarian text
    "продава": OfferType.SALE,
    "продажба": OfferType.SALE,
    "продаван": OfferType.SALE,
    "за продажба": OfferType.SALE,
    "продажби": OfferType.SALE,
    "наем": OfferType.RENT,
    "под наем": OfferType.RENT,
    "дава под наем": OfferType.RENT,
    "наеми": OfferType.RENT,
    # URL patterns (transliterated)
    "prodava": OfferType.SALE,
    "prodajba": OfferType.SALE,
    "prodazhba": OfferType.SALE,
    "prodazhbi": OfferType.SALE,
    "prodajbi": OfferType.SALE,
    "naem": OfferType.RENT,
    "pod-naem": OfferType.RENT,
    "dava-pod-naem": OfferType.RENT,
    "naemi": OfferType.RENT,
    # API values (e.g., HomesBg)
    "sell": OfferType.SALE,
    "apartmentsell": OfferType.SALE,
    "housesell": OfferType.SALE,
    "landsell": OfferType.SALE,
    "landagro": OfferType.SALE,
    "rent": OfferType.RENT,
    "apartmentrent": OfferType.RENT,
    "houserent": OfferType.RENT,
}

# =============================================================================
# PROPERTY TYPE ALIASES
# =============================================================================

PROPERTY_TYPE_ALIASES: dict[str, PropertyType] = {
    # Bulgarian text
    "студио": PropertyType.STUDIO,
    "едностаен": PropertyType.ONE_ROOM,
    "1-стаен": PropertyType.ONE_ROOM,
    "1 стаен": PropertyType.ONE_ROOM,
    "двустаен": PropertyType.TWO_ROOM,
    "2-стаен": PropertyType.TWO_ROOM,
    "2 стаен": PropertyType.TWO_ROOM,
    "тристаен": PropertyType.THREE_ROOM,
    "3-стаен": PropertyType.THREE_ROOM,
    "3 стаен": PropertyType.THREE_ROOM,
    "четиристаен": PropertyType.FOUR_ROOM,
    "4-стаен": PropertyType.FOUR_ROOM,
    "4 стаен": PropertyType.FOUR_ROOM,
    "многостаен": PropertyType.MULTI_ROOM,
    "5-стаен": PropertyType.MULTI_ROOM,
    "5 стаен": PropertyType.MULTI_ROOM,
    "мезонет": PropertyType.MAISONETTE,
    "мезонети": PropertyType.MAISONETTE,
    "земя": PropertyType.LAND,
    "земеделска": PropertyType.LAND,
    "земеделска земя": PropertyType.LAND,
    "парцел": PropertyType.LAND,
    "къща": PropertyType.HOUSE,
    "вила": PropertyType.HOUSE,
    "офис": PropertyType.OFFICE,
    "ателие": PropertyType.STUDIO_APARTMENT,
    "гараж": PropertyType.GARAGE,
    "паркомясто": PropertyType.PARKING,
    # URL patterns (transliterated)
    "studio": PropertyType.STUDIO,
    "ednostaen": PropertyType.ONE_ROOM,
    "ednostayn": PropertyType.ONE_ROOM,
    "ednostayni": PropertyType.ONE_ROOM,
    "dvustaen": PropertyType.TWO_ROOM,
    "dvustayn": PropertyType.TWO_ROOM,
    "dvustayni": PropertyType.TWO_ROOM,
    "dvustaini": PropertyType.TWO_ROOM,
    "tristaen": PropertyType.THREE_ROOM,
    "tristayn": PropertyType.THREE_ROOM,
    "tristayni": PropertyType.THREE_ROOM,
    "tristaini": PropertyType.THREE_ROOM,
    "chetiristaen": PropertyType.FOUR_ROOM,
    "chetiristayn": PropertyType.FOUR_ROOM,
    "chetiristayni": PropertyType.FOUR_ROOM,
    "chetiristaini": PropertyType.FOUR_ROOM,
    "mnogostaen": PropertyType.MULTI_ROOM,
    "mnogostayn": PropertyType.MULTI_ROOM,
    "mnogostayni": PropertyType.MULTI_ROOM,
    "mezonet": PropertyType.MAISONETTE,
    "mezoneti": PropertyType.MAISONETTE,
    "zemedelska": PropertyType.LAND,
    "zemedelski-zemi": PropertyType.LAND,
    "zemya": PropertyType.LAND,
    "kashta": PropertyType.HOUSE,
    "kashti": PropertyType.HOUSE,
    "ofis": PropertyType.OFFICE,
    "atelie": PropertyType.STUDIO_APARTMENT,
    "garazh": PropertyType.GARAGE,
    "parkomyasto": PropertyType.PARKING,
}

# =============================================================================
# CITY ALIASES
# =============================================================================

CITY_ALIASES: dict[str, City] = {
    # Bulgarian - lowercase for matching
    "софия": City.SOFIA,
    "гр. софия": City.SOFIA,
    "град софия": City.SOFIA,
    "гр.софия": City.SOFIA,
    "пловдив": City.PLOVDIV,
    "гр. пловдив": City.PLOVDIV,
    "град пловдив": City.PLOVDIV,
    "гр.пловдив": City.PLOVDIV,
    "варна": City.VARNA,
    "гр. варна": City.VARNA,
    "град варна": City.VARNA,
    "бургас": City.BURGAS,
    "гр. бургас": City.BURGAS,
    "град бургас": City.BURGAS,
    # Transliterated
    "sofia": City.SOFIA,
    "sofiya": City.SOFIA,
    "grad-sofiya": City.SOFIA,
    "grad-sofia": City.SOFIA,
    "plovdiv": City.PLOVDIV,
    "grad-plovdiv": City.PLOVDIV,
    "varna": City.VARNA,
    "grad-varna": City.VARNA,
    "burgas": City.BURGAS,
    "grad-burgas": City.BURGAS,
}

# =============================================================================
# CURRENCY ALIASES
# =============================================================================

CURRENCY_ALIASES: dict[str, Currency] = {
    "€": Currency.EUR,
    "eur": Currency.EUR,
    "евро": Currency.EUR,
    "euro": Currency.EUR,
    "лв": Currency.BGN,
    "лв.": Currency.BGN,
    "bgn": Currency.BGN,
    "лева": Currency.BGN,
}

# =============================================================================
# SOFIA NEIGHBORHOOD ALIASES
# =============================================================================

SOFIA_NEIGHBORHOOD_ALIASES: dict[str, SofiaNeighborhood] = {
    # Normalized lowercase Bulgarian -> enum
    "лозенец": SofiaNeighborhood.LOZENETS,
    "кв. лозенец": SofiaNeighborhood.LOZENETS,
    "кв.лозенец": SofiaNeighborhood.LOZENETS,
    "център": SofiaNeighborhood.CENTER,
    "центъра": SofiaNeighborhood.CENTER,
    "иван вазов": SofiaNeighborhood.IVAN_VAZOV,
    "ив. вазов": SofiaNeighborhood.IVAN_VAZOV,
    "ив.вазов": SofiaNeighborhood.IVAN_VAZOV,
    "оборище": SofiaNeighborhood.OBORISHTE,
    "дианабад": SofiaNeighborhood.DIANABAD,
    "изток": SofiaNeighborhood.IZTOK,
    "изгрев": SofiaNeighborhood.IZGREV,
    "яворов": SofiaNeighborhood.YAVOROV,
    "борово": SofiaNeighborhood.BOROVO,
    "гоце делчев": SofiaNeighborhood.GOTSE_DELCHEV,
    "г. делчев": SofiaNeighborhood.GOTSE_DELCHEV,
    "г.делчев": SofiaNeighborhood.GOTSE_DELCHEV,
    "стрелбище": SofiaNeighborhood.STRELBISHTE,
    "хиподрума": SofiaNeighborhood.HIPODRUMA,
    "хладилника": SofiaNeighborhood.HLADILNIKA,
    "пз хладилника": SofiaNeighborhood.HLADILNIKA,
    "белите брези": SofiaNeighborhood.BELITE_BREZI,
    "бели брези": SofiaNeighborhood.BELI_BREZI,
    "витоша": SofiaNeighborhood.VITOSHA,
    "манастирски ливади": SofiaNeighborhood.MANASTIRSKI_LIVADI,
    "студентски град": SofiaNeighborhood.STUDENTSKI_GRAD,
    "студентски": SofiaNeighborhood.STUDENTSKI_GRAD,
    "младост": SofiaNeighborhood.MLADOST,
    "младост 1": SofiaNeighborhood.MLADOST_1,
    "младост 2": SofiaNeighborhood.MLADOST_2,
    "младост 3": SofiaNeighborhood.MLADOST_3,
    "младост 4": SofiaNeighborhood.MLADOST_4,
    "дружба": SofiaNeighborhood.DRUZHBA,
    "дружба 1": SofiaNeighborhood.DRUZHBA_1,
    "дружба 2": SofiaNeighborhood.DRUZHBA_2,
    "люлин": SofiaNeighborhood.LYULIN,
    "надежда": SofiaNeighborhood.NADEZHDA,
    "надежда 1": SofiaNeighborhood.NADEZHDA_1,
    "надежда 2": SofiaNeighborhood.NADEZHDA_2,
    "надежда 3": SofiaNeighborhood.NADEZHDA_3,
    "надежда 4": SofiaNeighborhood.NADEZHDA_4,
    "слатина": SofiaNeighborhood.SLATINA,
    "гео милев": SofiaNeighborhood.GEO_MILEV,
    "редута": SofiaNeighborhood.REDUTA,
    "подуяне": SofiaNeighborhood.PODUYANE,
    "подуене": SofiaNeighborhood.PODUYANE,
    "кръстова вада": SofiaNeighborhood.KRASTOVA_VADA,
    "малинова долина": SofiaNeighborhood.MALINOVA_DOLINA,
    "драгалевци": SofiaNeighborhood.DRAGALEVTSI,
    "бояна": SofiaNeighborhood.BOYANA,
    "симеоново": SofiaNeighborhood.SIMEONOVO,
    "княжево": SofiaNeighborhood.KNYAZHEVO,
    "овча купел": SofiaNeighborhood.OVCHA_KUPEL,
    "красно село": SofiaNeighborhood.KRASNO_SELO,
    "лагера": SofiaNeighborhood.LAGERA,
    "бъкстон": SofiaNeighborhood.BUKSTON,
    "павлово": SofiaNeighborhood.PAVLOVO,
    "хаджи димитър": SofiaNeighborhood.HADJI_DIMITAR,
    "х. димитър": SofiaNeighborhood.HADJI_DIMITAR,
    "левски": SofiaNeighborhood.LEVSKI,
    "левски г": SofiaNeighborhood.LEVSKI_G,
    "левски в": SofiaNeighborhood.LEVSKI_V,
    "сухата река": SofiaNeighborhood.SUHA_REKA,
    "суха река": SofiaNeighborhood.SUHA_REKA,
    "банишора": SofiaNeighborhood.BANISHORA,
    "докторски паметник": SofiaNeighborhood.DOKTORSKI_PAMETNIK,
    "докторски": SofiaNeighborhood.DOKTORSKI_PAMETNIK,
    "дървеница": SofiaNeighborhood.DARVENITSA,
    "мусагеница": SofiaNeighborhood.MUSAGENITSA,
    "медицинска академия": SofiaNeighborhood.MEDITSINSKA_AKADEMIYA,
    "борисова градина": SofiaNeighborhood.BORISOVA_GRADINA,
    "крива река": SofiaNeighborhood.KRIVA_REKA,
    "модерно предградие": SofiaNeighborhood.MODERNO_PREDGRADIE,
    "зона б-5": SofiaNeighborhood.ZONA_B5,
    "зона б5": SofiaNeighborhood.ZONA_B5,
    "зона б-18": SofiaNeighborhood.ZONA_B18,
    "зона б-19": SofiaNeighborhood.ZONA_B19,
    "света троица": SofiaNeighborhood.SVETA_TROITSA,
    "св. троица": SofiaNeighborhood.SVETA_TROITSA,
    "сердика": SofiaNeighborhood.SERDIKA,
    "триъгълника": SofiaNeighborhood.TRIAGALNIKA,
    "полигона": SofiaNeighborhood.POLIGONA,
    "мотописта": SofiaNeighborhood.MOTOPISTA,
    "свобода": SofiaNeighborhood.SVOBODA,
    "толстой": SofiaNeighborhood.TOLSTOY,
    "фондови жилища": SofiaNeighborhood.FONDOVI_ZHILISHTA,
    "западен парк": SofiaNeighborhood.ZAPADEN_PARK,
    "разсадника": SofiaNeighborhood.RAZSADNIKA,
    "карпузица": SofiaNeighborhood.KARPUZITSA,
    "илинден": SofiaNeighborhood.ILINDEN,
    "бенковски": SofiaNeighborhood.BENKOVSKI,
    "орландовци": SofiaNeighborhood.ORLANDOVTSI,
    "малашевци": SofiaNeighborhood.MALASHEVTSI,
    "христо смирненски": SofiaNeighborhood.HRISTO_SMIRNENSKI,
    "хр. смирненски": SofiaNeighborhood.HRISTO_SMIRNENSKI,
    "горна баня": SofiaNeighborhood.GORNA_BANYA,
    "банкя": SofiaNeighborhood.BANKYA,
    "илиянци": SofiaNeighborhood.ILIENTSI,
    "враждебна": SofiaNeighborhood.VRAZHDEBNA,
    "ботунец": SofiaNeighborhood.BOTUNETS,
    "панчарево": SofiaNeighborhood.PANCHAREVO,
    "бистрица": SofiaNeighborhood.BISTRITSA,
    "германа": SofiaNeighborhood.GERMANA,
    # Transliterated versions
    "lozenets": SofiaNeighborhood.LOZENETS,
    "tsentar": SofiaNeighborhood.CENTER,
    "centar": SofiaNeighborhood.CENTER,
    "ivan-vazov": SofiaNeighborhood.IVAN_VAZOV,
    "oborishte": SofiaNeighborhood.OBORISHTE,
    "dianabad": SofiaNeighborhood.DIANABAD,
    "iztok": SofiaNeighborhood.IZTOK,
    "izgrev": SofiaNeighborhood.IZGREV,
    "yavorov": SofiaNeighborhood.YAVOROV,
    "borovo": SofiaNeighborhood.BOROVO,
    "gotse-delchev": SofiaNeighborhood.GOTSE_DELCHEV,
    "strelbishte": SofiaNeighborhood.STRELBISHTE,
    "hipodruma": SofiaNeighborhood.HIPODRUMA,
    "hladilnika": SofiaNeighborhood.HLADILNIKA,
    "vitosha": SofiaNeighborhood.VITOSHA,
    "manastirski-livadi": SofiaNeighborhood.MANASTIRSKI_LIVADI,
    "studentski-grad": SofiaNeighborhood.STUDENTSKI_GRAD,
    "mladost": SofiaNeighborhood.MLADOST,
    "druzhba": SofiaNeighborhood.DRUZHBA,
    "lyulin": SofiaNeighborhood.LYULIN,
    "nadezhda": SofiaNeighborhood.NADEZHDA,
    "slatina": SofiaNeighborhood.SLATINA,
    "geo-milev": SofiaNeighborhood.GEO_MILEV,
    "reduta": SofiaNeighborhood.REDUTA,
    "poduyane": SofiaNeighborhood.PODUYANE,
    "krastova-vada": SofiaNeighborhood.KRASTOVA_VADA,
    "malinova-dolina": SofiaNeighborhood.MALINOVA_DOLINA,
    "dragalevtsi": SofiaNeighborhood.DRAGALEVTSI,
    "boyana": SofiaNeighborhood.BOYANA,
    "simeonovo": SofiaNeighborhood.SIMEONOVO,
    "knyazhevo": SofiaNeighborhood.KNYAZHEVO,
    "ovcha-kupel": SofiaNeighborhood.OVCHA_KUPEL,
    "krasno-selo": SofiaNeighborhood.KRASNO_SELO,
    "lagera": SofiaNeighborhood.LAGERA,
    "bukston": SofiaNeighborhood.BUKSTON,
    "pavlovo": SofiaNeighborhood.PAVLOVO,
    "hadji-dimitar": SofiaNeighborhood.HADJI_DIMITAR,
    "levski": SofiaNeighborhood.LEVSKI,
    "suha-reka": SofiaNeighborhood.SUHA_REKA,
    "banishora": SofiaNeighborhood.BANISHORA,
}

# =============================================================================
# PLOVDIV NEIGHBORHOOD ALIASES
# =============================================================================

PLOVDIV_NEIGHBORHOOD_ALIASES: dict[str, PlovdivNeighborhood] = {
    # Bulgarian - lowercase
    "център": PlovdivNeighborhood.CENTER,
    "центъра": PlovdivNeighborhood.CENTER,
    "каменица 1": PlovdivNeighborhood.KAMENITSA_1,
    "каменица 2": PlovdivNeighborhood.KAMENITSA_2,
    "каменица": PlovdivNeighborhood.KAMENITSA_1,
    "мараша": PlovdivNeighborhood.MARASHA,
    "младежки хълм": PlovdivNeighborhood.MLADEJKI_HALM,
    "кършияка": PlovdivNeighborhood.KARSHIYAKA,
    "тракия": PlovdivNeighborhood.TRAKIA,
    "смирненски": PlovdivNeighborhood.SMIRNENSKI,
    "христо смирненски": PlovdivNeighborhood.HRISTO_SMIRNENSKI,
    "хр. смирненски": PlovdivNeighborhood.SMIRNENSKI,
    "гребна база": PlovdivNeighborhood.GREBNA_BAZA,
    "въстанически": PlovdivNeighborhood.VASTANICHESKI,
    "христо ботев": PlovdivNeighborhood.HRISTO_BOTEV,
    "хр. ботев": PlovdivNeighborhood.HRISTO_BOTEV,
    "южен": PlovdivNeighborhood.YUZHEN,
    "кючук париж": PlovdivNeighborhood.KYUCHUK_PARIJ,
    "гагарин": PlovdivNeighborhood.GAGARIN,
    "изгрев": PlovdivNeighborhood.IZGREV,
    "захарна фабрика": PlovdivNeighborhood.ZAHARNA_FABRIKA,
    "централна гара": PlovdivNeighborhood.TSENTRALNA_GARA,
    "беломорски": PlovdivNeighborhood.BELOMORSKI,
    "вми": PlovdivNeighborhood.VMI,
    "пещерско шосе": PlovdivNeighborhood.PESHTERSKO_SHOSE,
    "отдих и култура": PlovdivNeighborhood.OTDIH_I_KULTURA,
    "рогошко шосе": PlovdivNeighborhood.ROGOSHKO_SHOSE,
    "бунарджика": PlovdivNeighborhood.BUNARDZHIKA,
    "карловско шосе": PlovdivNeighborhood.KARLOVSKO_SHOSE,
    "тодор каблешков": PlovdivNeighborhood.TODOR_KABLESHKOV,
    "цар симеон": PlovdivNeighborhood.TSAR_SIMEON,
    "индустриална зона": PlovdivNeighborhood.INDUSTRIALNA_ZONA,
    "батак": PlovdivNeighborhood.BATAK,
    "пловдивски университет": PlovdivNeighborhood.PLOVDIVSKI_UNIVERSITET,
    "съдийски": PlovdivNeighborhood.SADIYSKI,
    "капана": PlovdivNeighborhood.KAPANA,
    "филипово": PlovdivNeighborhood.FILIPOVO,
    "прослав": PlovdivNeighborhood.PROSLAV,
    "коматево": PlovdivNeighborhood.KOMATEVO,
    "остромила": PlovdivNeighborhood.OSTROMILA,
    "столипиново": PlovdivNeighborhood.STOLIPINOVO,
    # Transliterated
    "tsentar": PlovdivNeighborhood.CENTER,
    "centar": PlovdivNeighborhood.CENTER,
    "kamenitsa": PlovdivNeighborhood.KAMENITSA_1,
    "marasha": PlovdivNeighborhood.MARASHA,
    "mladejki-halm": PlovdivNeighborhood.MLADEJKI_HALM,
    "karshiyaka": PlovdivNeighborhood.KARSHIYAKA,
    "trakia": PlovdivNeighborhood.TRAKIA,
    "smirnenski": PlovdivNeighborhood.SMIRNENSKI,
    "grebna-baza": PlovdivNeighborhood.GREBNA_BAZA,
    "yuzhen": PlovdivNeighborhood.YUZHEN,
    "gagarin": PlovdivNeighborhood.GAGARIN,
    "izgrev": PlovdivNeighborhood.IZGREV,
    "kapana": PlovdivNeighborhood.KAPANA,
}

# =============================================================================
# KNOWN AGENCIES (for normalization)
# =============================================================================

KNOWN_AGENCIES: dict[str, str] = {
    # lowercase -> canonical name
    "bulgarian properties": "Bulgarian Properties",
    "bulgarianproperties": "Bulgarian Properties",
    "suprimmo": "Suprimmo",
    "luximmo": "Luximmo",
    "arco real estate": "Arco Real Estate",
    "arco": "Arco Real Estate",
    "address": "Address",
    "явлена": "Явлена",
    "yavlena": "Явлена",
    "мирела": "Мирела",
    "mirela": "Мирела",
    "имоти бг": "Имоти БГ",
    "era": "ERA",
    "century 21": "Century 21",
    "century21": "Century 21",
    "re/max": "RE/MAX",
    "remax": "RE/MAX",
    "home tour": "Home Tour",
    "imoti.net": "Imoti.net",
    "homes.bg": "Homes.bg",
    "imot.bg": "Imot.bg",
    "частно лице": "Частно лице",
    "частен": "Частно лице",
    "private": "Частно лице",
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _find_in_text(text: str, aliases: dict[str, T]) -> T | None:
    """Search for any alias within the text (not just exact match)."""
    if not text:
        return None
    text_lower = text.lower()
    # Sort by length descending to match longer patterns first
    for alias in sorted(aliases.keys(), key=len, reverse=True):
        if alias in text_lower:
            return aliases[alias]
    return None


def _find_exact(text: str, aliases: dict[str, T]) -> T | None:
    """Exact match lookup."""
    if not text:
        return None
    return aliases.get(text.lower().strip())


# =============================================================================
# NORMALIZATION FUNCTIONS
# =============================================================================


def normalize_offer_type(text: str = "", url: str = "") -> OfferType | str:
    """
    Normalize offer type. Tries URL first, then text content.
    Returns original value if no match (soft validation).

    Args:
        text: Text content (e.g., title) to search
        url: URL to search for patterns

    Returns:
        OfferType enum if matched, otherwise original string
    """
    # Try URL first (more reliable)
    if url:
        result = _find_in_text(url, OFFER_TYPE_ALIASES)
        if result:
            return result

    # Try text content
    if text:
        result = _find_in_text(text, OFFER_TYPE_ALIASES)
        if result:
            return result

    # Soft validation: log and return original
    original = text or url
    if original:
        _unknown_values["offer_type"].add(original[:100])
        logger.debug(f"Unknown offer_type: {original[:100]}")
    return original


def normalize_property_type(text: str = "", url: str = "") -> PropertyType | str:
    """
    Normalize property type. Tries URL first, then text content.
    Returns original value if no match (soft validation).

    Args:
        text: Text content (e.g., title) to search
        url: URL to search for patterns

    Returns:
        PropertyType enum if matched, otherwise original string
    """
    # Try URL first
    if url:
        result = _find_in_text(url, PROPERTY_TYPE_ALIASES)
        if result:
            return result

    # Try text content
    if text:
        result = _find_in_text(text, PROPERTY_TYPE_ALIASES)
        if result:
            return result

    # Soft validation
    original = text or url
    if original:
        _unknown_values["property_type"].add(original[:100])
        logger.debug(f"Unknown property_type: {original[:100]}")
    return original


def normalize_city(location: str) -> City | str:
    """
    Normalize city from location string.
    Handles formats like "гр. София", "град Пловдив", "Sofia", etc.

    Args:
        location: Location string that may contain city

    Returns:
        City enum if matched, otherwise extracted city string
    """
    if not location:
        return ""

    # Clean the location string
    location_clean = location.lower().strip()
    location_clean = re.sub(r"^(гр\.|град|с\.)\s*", "", location_clean)

    # Try exact match first
    result = _find_exact(location_clean, CITY_ALIASES)
    if result:
        return result

    # Try substring match
    result = _find_in_text(location, CITY_ALIASES)
    if result:
        return result

    # Extract first part before comma
    first_part = location.split(",")[0].strip()
    first_part_clean = re.sub(r"^(гр\.|град|с\.)\s*", "", first_part.lower())
    result = _find_exact(first_part_clean, CITY_ALIASES)
    if result:
        return result

    # Soft validation - return cleaned first part
    if first_part:
        # Only track if it looks like a city name (not too long)
        if len(first_part) < 30:
            _unknown_values["city"].add(first_part[:50])
            logger.debug(f"Unknown city: {first_part[:50]}")
        # Return cleaned version
        cleaned = re.sub(r"^(гр\.|град|с\.)\s*", "", first_part)
        return cleaned.strip()
    return ""


def normalize_neighborhood(
    neighborhood: str,
    city: City | str = "",
) -> SofiaNeighborhood | PlovdivNeighborhood | str:
    """
    Normalize neighborhood based on city context.

    Args:
        neighborhood: Neighborhood name to normalize
        city: City enum or string to determine which alias dict to use

    Returns:
        Neighborhood enum if matched, otherwise cleaned string
    """
    if not neighborhood:
        return ""

    neighborhood_clean = neighborhood.lower().strip()
    # Remove common prefixes
    neighborhood_clean = re.sub(r"^(кв\.|квартал|ж\.к\.|ж\.к|жк)\s*", "", neighborhood_clean)
    neighborhood_clean = neighborhood_clean.strip()

    # Determine city for context
    is_sofia = city == City.SOFIA or (isinstance(city, str) and "соф" in city.lower())
    is_plovdiv = city == City.PLOVDIV or (isinstance(city, str) and "плов" in city.lower())

    # Select alias dict based on city
    if is_sofia:
        result = _find_exact(neighborhood_clean, SOFIA_NEIGHBORHOOD_ALIASES)
        if result:
            return result
        result = _find_in_text(neighborhood, SOFIA_NEIGHBORHOOD_ALIASES)
        if result:
            return result
    elif is_plovdiv:
        result = _find_exact(neighborhood_clean, PLOVDIV_NEIGHBORHOOD_ALIASES)
        if result:
            return result
        result = _find_in_text(neighborhood, PLOVDIV_NEIGHBORHOOD_ALIASES)
        if result:
            return result
    else:
        # Try both (Sofia first as it's more common)
        result = _find_exact(neighborhood_clean, SOFIA_NEIGHBORHOOD_ALIASES)
        if result:
            return result
        result = _find_exact(neighborhood_clean, PLOVDIV_NEIGHBORHOOD_ALIASES)
        if result:
            return result
        result = _find_in_text(neighborhood, SOFIA_NEIGHBORHOOD_ALIASES)
        if result:
            return result
        result = _find_in_text(neighborhood, PLOVDIV_NEIGHBORHOOD_ALIASES)
        if result:
            return result

    # Soft validation
    if neighborhood_clean and len(neighborhood_clean) < 50:
        _unknown_values["neighborhood"].add(neighborhood[:50])
        logger.debug(f"Unknown neighborhood: {neighborhood[:50]}")

    # Return cleaned version
    return neighborhood_clean.title() if neighborhood_clean else neighborhood


def normalize_currency(text: str) -> Currency | str:
    """
    Normalize currency from price text.
    Prioritizes EUR detection since price texts often show EUR first with BGN equivalent.

    Args:
        text: Price text containing currency symbol or name

    Returns:
        Currency enum if matched, otherwise empty string
    """
    if not text:
        return ""

    text_lower = text.lower()

    # Check for EUR first (priority) since prices often show EUR with BGN equivalent
    for alias, currency in CURRENCY_ALIASES.items():
        if currency == Currency.EUR and alias in text_lower:
            return Currency.EUR

    # Then check for BGN
    for alias, currency in CURRENCY_ALIASES.items():
        if currency == Currency.BGN and alias in text_lower:
            return Currency.BGN

    return ""


def normalize_agency(agency: str) -> str:
    """
    Normalize agency name.
    Returns canonical form if known, otherwise cleaned original.

    Args:
        agency: Raw agency name

    Returns:
        Normalized agency name
    """
    if not agency:
        return ""

    agency_lower = agency.lower().strip()

    # Check known agencies
    if agency_lower in KNOWN_AGENCIES:
        return KNOWN_AGENCIES[agency_lower]

    # Clean up: strip whitespace, title case for unknown
    normalized = agency.strip()

    # Track unknown agencies (only if not too long and not obviously generic)
    if normalized and len(normalized) < 50:
        _unknown_values["agency"].add(normalized[:50])

    return normalized


# =============================================================================
# SESSION TRACKING
# =============================================================================


def get_unknown_values() -> dict[str, set[str]]:
    """Get all unknown values encountered during this session."""
    return dict(_unknown_values)


def clear_unknown_values() -> None:
    """Clear the unknown values tracker (call between scrape runs)."""
    _unknown_values.clear()


def log_unknown_values_summary() -> None:
    """Log a summary of all unknown values found."""
    if not _unknown_values:
        logger.info("No unknown values encountered during this session.")
        return

    logger.warning("=== Unknown values summary ===")
    for field, values in sorted(_unknown_values.items()):
        sample = list(values)[:5]
        remaining = len(values) - 5
        sample_str = ", ".join(f"'{v}'" for v in sample)
        if remaining > 0:
            sample_str += f" ... and {remaining} more"
        logger.warning(f"  {field}: {len(values)} unknown - [{sample_str}]")
