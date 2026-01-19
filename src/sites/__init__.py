from src.sites.imotbg import ImotBgParser
from src.sites.imotinet import ImotiNetParser
from src.sites.homesbg import HomesBgParser

SITE_PARSERS = {
    "ImotBg": ImotBgParser,
    "ImotiNet": ImotiNetParser,
    "HomesBg": HomesBgParser,
}


def get_parser(site_name: str):
    parser_class = SITE_PARSERS.get(site_name)
    if not parser_class:
        raise ValueError(f"Unknown site: {site_name}")
    return parser_class()
