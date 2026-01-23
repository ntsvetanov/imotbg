from src.sites.bazarbg import BazarBgParser
from src.sites.bulgarianproperties import BulgarianPropertiesParser
from src.sites.homesbg import HomesBgParser
from src.sites.imoticom import ImotiComParser
from src.sites.imotbg import ImotBgParser
from src.sites.imotinet import ImotiNetParser
from src.sites.luximmo import LuximmoParser
from src.sites.suprimmo import SuprimmoParser

SITE_PARSERS = {
    "BazarBg": BazarBgParser,
    "BulgarianProperties": BulgarianPropertiesParser,
    "HomesBg": HomesBgParser,
    "ImotiCom": ImotiComParser,
    "ImotBg": ImotBgParser,
    "ImotiNet": ImotiNetParser,
    "ImotiNetPlovdiv": ImotiNetParser,
    "Luximmo": LuximmoParser,
    "Suprimmo": SuprimmoParser,
}


def get_parser(site_name: str):
    parser_class = SITE_PARSERS.get(site_name)
    if not parser_class:
        raise ValueError(f"Unknown site: {site_name}")
    return parser_class()
