import re

PROPERTY_TYPE_MAPPING = {
    "1-стаен": "едностаен",
    "едностаен": "едностаен",
    "2-стаен": "двустаен",
    "двустаен": "двустаен",
    "3-стаен": "тристаен",
    "тристаен": "тристаен",
    "4-стаен": "четиристаен",
    "четиристаен": "четиристаен",
    "многостаен": "многостаен",
    "мезонет": "мезонет",
    "земеделска": "земя",
    "земя": "земя",
}


def parse_price(text: str) -> float:
    if not text:
        return 0.0
    first_price = text.split("лв")[0].split("€")[0]
    cleaned = re.sub(r"[^\d]", "", first_price.replace(" ", ""))
    return float(cleaned) if cleaned else 0.0


def extract_currency(text: str) -> str:
    if not text:
        return ""
    text_lower = text.lower()
    if "€" in text or "eur" in text_lower:
        return "EUR"
    if "лв" in text_lower or "bgn" in text_lower:
        return "BGN"
    return ""


def is_without_dds(text: str) -> bool:
    return "ддс" in text.lower() if text else False


def extract_city(location: str) -> str:
    if not location:
        return ""
    city = location.split(",")[0].strip()
    prefixes_to_remove = ["град ", "гр. ", "с. "]
    for prefix in prefixes_to_remove:
        city = city.replace(prefix, "")
    return city.strip()


def extract_neighborhood(location: str) -> str:
    if not location:
        return ""
    parts = location.split(",")
    return parts[1].strip() if len(parts) > 1 else ""


def extract_property_type(text: str) -> str:
    if not text:
        return ""
    text_lower = text.lower()
    for pattern, normalized in PROPERTY_TYPE_MAPPING.items():
        if pattern in text_lower:
            return normalized
    return ""


def extract_offer_type(text: str) -> str:
    if not text:
        return ""
    text_lower = text.lower()
    if "продава" in text_lower:
        return "продава"
    if "наем" in text_lower:
        return "наем"
    return ""


def to_int_safe(text: str) -> int:
    if not text:
        return 0
    match = re.search(r"\d+", str(text))
    return int(match.group()) if match else 0


def to_float_safe(text: str) -> float:
    if not text:
        return 0.0
    match = re.search(r"[\d.]+", str(text))
    return float(match.group()) if match else 0.0


def to_float_or_zero(value) -> float:
    if not value:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(",", "").replace(" ", "").split()[0]
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
