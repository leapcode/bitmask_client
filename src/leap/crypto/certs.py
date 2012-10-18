import ctypes
import socket

import gnutls.connection
import gnutls.library


def get_https_cert_fingerprint(domain):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cred = gnutls.connection.X509Credentials()

    session = gnutls.connection.ClientSession(sock, cred)
    session.connect((domain, 443))
    session.handshake()
    cert = session.peer_certificate

    _buffer = ctypes.create_string_buffer(20)
    buffer_length = ctypes.c_size_t(20)

    gnutls.library.functions.gnutls_x509_crt_get_fingerprint(
        cert._c_object, gnutls.library.constants.GNUTLS_DIG_SHA1,  # 3
        ctypes.byref(_buffer), ctypes.byref(buffer_length))

    # deinit
    #server_cert._X509Certificate__deinit(server_cert._c_object)
    # needed? is segfaulting

    fpr = ctypes.string_at(_buffer, buffer_length.value)
    hex_fpr = u":".join(u"%02X" % ord(char) for char in fpr)

    return hex_fpr
