from src.sites.bazarbg import BazarBgParser
from src.sites.homesbg import HomesBgParser
from src.sites.imotbg import ImotBgParser
from src.sites.imotinet import ImotiNetParser

SITE_PARSERS = {
    "BazarBg": BazarBgParser,
    "HomesBg": HomesBgParser,
    "ImotBg": ImotBgParser,
    "ImotiNet": ImotiNetParser,
}


def get_parser(site_name: str):
    parser_class = SITE_PARSERS.get(site_name)
    if not parser_class:
        raise ValueError(f"Unknown site: {site_name}")
    return parser_class()
