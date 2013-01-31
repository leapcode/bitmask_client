"""
An u1db server that stores data using couchdb.

This should be run with:
    twistd -n web --wsgi=leap.soledad.server.application
"""

from twisted.web.wsgi import WSGIResource
from twisted.internet import reactor

from u1db.remote import (
    http_app,
    server_state,
)

state = server_state.ServerState()
# TODO: change working dir to something meaningful
state.set_workingdir('/tmp')
# TODO: write a LeapHTTPApp that will use Couch as backend instead of SQLite
application = http_app.HTTPApp(state)

resource = WSGIResource(reactor, reactor.getThreadPool(), application)
