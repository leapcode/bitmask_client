import logging

import sh

logger = logging.getLogger(__name__)


def run_polkit_auth_agent():
    """
    launches polkit authentication agent
    """
    logger.debug('launching policykit authentication agent in background...')
    polkit = sh.Command('/usr/lib/policykit-1-gnome/'
                        'polkit-gnome-authentication-agent-1')
    polkit(_bg=True)


def check_if_running_polkit_auth():
    """
    check if polkit authentication agent is running
    and launch it if it is not
    """
    from sh import grep
    from sh import ps

    # for some reason, sh is getting us
    # limited line width, so the grep fails
    #grep_pk = lambda: grep(ps('a'), 'polkit-gnome-authentication-agent-1')
    grep_pk = lambda: grep(ps('a'), '[p]olkit-gnome-auth')
    try:
        grep_pk()
    except sh.ErrorReturnCode_1:
        logger.debug('polkit auth agent not found, trying to launch it...')
        run_polkit_auth_agent()
    else:
        logger.debug('polkit auth agent is running, no need to be launched')
