import logging

import sh
from sh import grep
from sh import ps

logger = logging.getLogger(__name__)


def run_polkit_auth_agent():
    logger.debug('launching policykit authentication agent in background...')
    polkit = sh.Command('/usr/lib/policykit-1-gnome/'
                        'polkit-gnome-authentication-agent-1')
    polkit(_bg=True)


def check_if_running_polkit_auth():
    """
    check if polkit authentication agent is running
    and launch it if it is not
    """
    try:
        grep(ps('aux'), '[p]olkit-gnome-authentication-agent-1')
    except sh.ErrorReturnCode_1:
        logger.debug('polkit auth agent not found, trying to launch it...')
        run_polkit_auth_agent()
