class SRPSession(object):

    def __init__(self, username, token, uuid, session_id):
        self.username = username
        self.token = token
        self.uuid = uuid
        self.session_id = session_id
