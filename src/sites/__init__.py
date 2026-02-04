"""
Site extractors registry.

Maps site names to their extractor classes.
"""

from src.sites.alobg import AloBgExtractor
from src.sites.bazarbg import BazarBgExtractor
from src.sites.bulgarianproperties import BulgarianPropertiesExtractor
from src.sites.homesbg import HomesBgExtractor
from src.sites.imotbg import ImotBgExtractor
from src.sites.imoticom import ImotiComExtractor
from src.sites.imotinet import ImotiNetExtractor
from src.sites.luximmo import LuximmoExtractor
from src.sites.suprimmo import SuprimmoExtractor

SITE_EXTRACTORS = {
    "AloBg": AloBgExtractor,
    "BazarBg": BazarBgExtractor,
    "BulgarianProperties": BulgarianPropertiesExtractor,
    "HomesBg": HomesBgExtractor,
    "ImotiCom": ImotiComExtractor,
    "ImotBg": ImotBgExtractor,
    "ImotiNet": ImotiNetExtractor,
    "ImotiNetPlovdiv": ImotiNetExtractor,
    "Luximmo": LuximmoExtractor,
    "Suprimmo": SuprimmoExtractor,
}


def get_extractor(site_name: str):
    """Get extractor instance for a site.

    Args:
        site_name: Name of the site (e.g., "ImotBg", "HomesBg")

    Returns:
        Extractor instance for the site

    Raises:
        ValueError: If site name is unknown
    """
    extractor_class = SITE_EXTRACTORS.get(site_name)
    if not extractor_class:
        raise ValueError(f"Unknown site: {site_name}")
    return extractor_class()
