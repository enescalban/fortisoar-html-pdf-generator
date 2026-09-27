from connectors.core.connector import get_logger, ConnectorError

from .constants import LOGGER_NAME, ENGINE_ORDER
from .pdf_engines import available_engines

logger = get_logger(LOGGER_NAME)


def health_check(config=None, *args, **kwargs):
    """The connector has no remote endpoint; it is healthy when at least one
    local HTML -> PDF engine is installed on the FortiSOAR appliance."""
    engines = available_engines()
    if not engines:
        raise ConnectorError('No HTML to PDF engine found on this host. Install one of: {0}'
                             .format(', '.join(ENGINE_ORDER)))
    logger.info('Available PDF engines: %s', engines)
    return 'Connector is Available (engines: {0})'.format(
        ', '.join(e for e in ENGINE_ORDER if e in engines))
