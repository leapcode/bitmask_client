"""
An u1db server that stores data using couchdb.

This should be run with:
    twistd -n web --wsgi=leap.soledad.server.application
"""

from twisted.web.wsgi import WSGIResource
from twisted.internet import reactor
from u1db.remote import http_app
from leap.soledad.backends.couch import CouchServerState

couch_url = 'http://localhost:5984'
state = CouchServerState(couch_url)
# TODO: change working dir to something meaningful
state.set_workingdir('/tmp')
# TODO: write a LeapHTTPApp that will use Couch as backend instead of SQLite
application = http_app.HTTPApp(state)

resource = WSGIResource(reactor, reactor.getThreadPool(), application)
