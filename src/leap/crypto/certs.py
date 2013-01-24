import logging
import os
from StringIO import StringIO
import ssl
import time

from dateutil.parser import parse
from OpenSSL import crypto

from leap.util.misc import null_check

logger = logging.getLogger(__name__)


class BadCertError(Exception):
    """
    raised for malformed certs
    """


class NoCertError(Exception):
    """
    raised for cert not found in given path
    """


def get_https_cert_from_domain(domain, port=443):
    """
    @param domain: a domain name to get a certificate from.
    """
    cert = ssl.get_server_certificate((domain, port))
    x509 = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
    return x509


def get_cert_from_file(_file):
    null_check(_file, "pem file")
    if isinstance(_file, (str, unicode)):
        if not os.path.isfile(_file):
            raise NoCertError
        with open(_file) as f:
            cert = f.read()
    else:
        cert = _file.read()
    x509 = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
    return x509


def get_pkey_from_file(_file):
    getkey = lambda f: crypto.load_privatekey(
        crypto.FILETYPE_PEM, f.read())

    if isinstance(_file, str):
        with open(_file) as f:
            key = getkey(f)
    else:
        key = getkey(_file)
    return key


def can_load_cert_and_pkey(string):
    """
    loads certificate and private key from
    a buffer
    """
    try:
        f = StringIO(string)
        cert = get_cert_from_file(f)

        f = StringIO(string)
        key = get_pkey_from_file(f)

        null_check(cert, 'certificate')
        null_check(key, 'private key')
    except Exception as exc:
        logger.error(type(exc), exc.message)
        raise BadCertError
    else:
        return True


def get_cert_fingerprint(domain=None, port=443, filepath=None,
                         hash_type="SHA256", sep=":"):
    """
    @param domain: a domain name to get a fingerprint from
    @type domain: str
    @param filepath: path to a file containing a PEM file
    @type filepath: str
    @param hash_type: the hash function to be used in the fingerprint.
        must be one of SHA1, SHA224, SHA256, SHA384, SHA512
    @type hash_type: str
    @rparam: hex_fpr, a hexadecimal representation of a bytestring
             containing the fingerprint.
    @rtype: string
    """
    if domain:
        cert = get_https_cert_from_domain(domain, port=port)
    if filepath:
        cert = get_cert_from_file(filepath)
    hex_fpr = cert.digest(hash_type)
    return hex_fpr


def get_time_boundaries(certfile):
    cert = get_cert_from_file(certfile)
    null_check(cert, 'certificate')

    fromts, tots = (cert.get_notBefore(), cert.get_notAfter())
    from_, to_ = map(
        lambda ts: time.gmtime(time.mktime(parse(ts).timetuple())),
        (fromts, tots))
    return from_, to_
