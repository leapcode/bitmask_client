"""
Configuration Base Class
"""

import grp
import json
import logging
import requests
import os

from leap.util.fileutil import mkdir_p

logger = logging.getLogger(name=__name__)
logger.setLevel('DEBUG')


class Configuration(object):
    """
    All configurations (providers et al) will be managed in this class.
    """
    def __init__(self, provider_url=None):
        try:
            self.providers = {}
            self.error = False
            provider_file = self.check_and_get_definition_file(provider_url)
            self.providers['default'] = get_config_json(provider_file)
        except (requests.HTTPError, requests.RequestException) as e:
            self.error = e.message
        except requests.ConnectionError as e:
            if e.message == "[Errno 113] No route to host":
                if not is_internet_up:
                    self.error = "No valid internet connection found"
                else:
                    self.error = "Provider server appears currently down."

    def check_and_get_definition_file(self, provider_url):
        """
        checks if provider definition.json file is present.
        if not downloads one from the web.
        """
        default_provider_path = get_default_provider_path()

        if not os.path.isdir(default_provider_path):
            mkdir_p(default_provider_path)

        definition_file = get_config_file(
            'definition.json',
            folder=default_provider_path)

        if os.path.isfile(definition_file):
            return

        else:
            r = requests.get(provider_url)
            r.raise_for_status()
            with open(definition_file, 'wb') as f:
                f.write(json.dumps(r.json, indent=4))
            return definition_file


def get_config_dir():
    """
    get the base dir for all leap config
    @rparam: config path
    @rtype: string
    """
    # TODO
    # check for $XDG_CONFIG_HOME var?
    # get a more sensible path for win/mac
    # kclair: opinion? ^^
    return os.path.expanduser(
                os.path.join('~',
                             '.config',
                             'leap'))


def get_config_file(filename, folder=None):
    """
    concatenates the given filename
    with leap config dir.
    @param filename: name of the file
    @type filename: string
    @rparam: full path to config file
    """
    path = []
    path.append(get_config_dir())
    if folder is not None:
        path.append(folder)
    path.append(filename)
    return os.path.join(*path)


def get_default_provider_path():
    default_subpath = os.path.join("providers",
                                   "default")
    default_provider_path = get_config_file(
        '',
        folder=default_subpath)
    return default_provider_path


def validate_ip(ip_str):
    """
    raises exception if the ip_str is
    not a valid representation of an ip
    """
    socket.inet_aton(ip_str)


def get_username():
    return os.getlogin()


def get_groupname():
    gid = os.getgroups()[-1]
    return grp.getgrgid(gid).gr_name


def get_config_json(config_file=None):
    """
    will replace get_config function be developing them
    in parralel for branch purposes.
    @param: configuration file
    @type: file
    @rparam: configuration turples
    @rtype: dictionary
    """
    if not config_file:
        #TODO: NOT SURE WHAT this default should be, if anything
        fpath = get_config_file('eip.json')
        if not os.path.isfile(fpath):
            dpath, cfile = os.path.split(fpath)
            if not os.path.isdir(dpath):
                mkdir_p(dpath)
            with open(fpath, 'wb') as configfile:
                configfile.flush()
        return json.load(open(fpath))

    else:
        #TODO: add validity checks of file
        return json.load(open(config_file))


def is_internet_up():
    """TODO: Build more robust network diagnosis capabilities
    """
    try:
        response = requests.get('http://128.30.52.45', timeout=1)
        return True
    except requests.Timeout as err:
        pass
    return False
