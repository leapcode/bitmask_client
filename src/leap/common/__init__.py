import logging
logger = logging.getLogger(__name__)

try:
    import pygeoip
    HAS_GEOIP = True
except ImportError:
    logger.debug('PyGeoIP not found. Disabled Geo support.')
    HAS_GEOIP = False
