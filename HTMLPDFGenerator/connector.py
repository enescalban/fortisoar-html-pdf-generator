from connectors.core.connector import Connector, get_logger, ConnectorError

from .builtins import supported_operations
from .constants import LOGGER_NAME
from .health_check import health_check

logger = get_logger(LOGGER_NAME)


class HTMLPDFGeneratorConnector(Connector):

    def execute(self, config, operation, params, *args, **kwargs):
        action = supported_operations.get(operation)
        if action is None:
            raise ConnectorError('Unsupported operation: {0}'.format(operation))
        try:
            return action(config or {}, params or {}, *args, **kwargs)
        except ConnectorError:
            raise
        except Exception as exc:
            logger.exception('Operation "%s" failed', operation)
            raise ConnectorError('{0}: {1}'.format(type(exc).__name__, exc))

    def check_health(self, config=None, *args, **kwargs):
        return health_check(config, *args, **kwargs)
