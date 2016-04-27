from leap.soledad.client.auth import TokenBasedAuth
import base64
from u1db import errors


def patched_sign_request(self, method, url_query, params):
    if 'token' in self._creds:
        uuid, token = self._creds['token']
        auth = '%s:%s' % (uuid, token)
        return [('Authorization', 'Token %s' % base64.b64encode(auth))]
    else:
        raise errors.UnknownAuthMethod(
            'Wrong credentials: %s' % self._creds)


# TokenBasedAuth._sign_request = patched_sign_request
