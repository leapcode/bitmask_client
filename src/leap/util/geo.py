"""
experimental geo support.
not yet a feature.
in debian, we rely on the (optional) geoip-database
"""
import os
import platform

from leap.util import HAS_GEOIP

GEOIP = None

if HAS_GEOIP:
    import pygeoip  # we know we can :)

    GEOIP_PATH = None

    if platform.system() == "Linux":
        PATH = "/usr/share/GeoIP/GeoIP.dat"
        if os.path.isfile(PATH):
            GEOIP_PATH = PATH
        GEOIP = pygeoip.GeoIP(GEOIP_PATH, pygeoip.MEMORY_CACHE)


def get_country_name(ip):
    if not GEOIP:
        return
    try:
        country = GEOIP.country_name_by_addr(ip)
    except pygeoip.GeoIPError:
        country = None
    return country if country else "-"
