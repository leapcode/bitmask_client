import json

from twisted.python.log import err
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

from pixelated.resources import respond_json_deferred, BaseResource, GenericDeferredErrorHandler
from pixelated.support import replier


class MailTags(Resource):

    isLeaf = True

    def __init__(self, mail_id, mail_service):
        Resource.__init__(self)
        self._mail_service = mail_service
        self._mail_id = mail_id

    def render_POST(self, request):
        new_tags = json.loads(request.content.read()).get('newtags')

        d = self._mail_service.update_tags(self._mail_id, new_tags)
        d.addCallback(lambda mail: respond_json_deferred(
            mail.as_dict(), request))

        def handle403(failure):
            failure.trap(ValueError)
            return respond_json_deferred(failure.getErrorMessage(), request, 403)
        d.addErrback(handle403)
        return NOT_DONE_YET


class Mail(Resource, GenericDeferredErrorHandler):

    def __init__(self, mail_id, mail_service):
        Resource.__init__(self)
        self.putChild('tags', MailTags(mail_id, mail_service))
        self._mail_id = mail_id
        self._mail_service = mail_service

    def render_GET(self, request):
        def populate_reply(mail):
            mail_dict = mail.as_dict()
            current_user = self._mail_service.account_email
            sender = mail.headers.get('Reply-to', mail.headers.get('From'))
            to = mail.headers.get('To', [])
            ccs = mail.headers.get('Cc', [])
            mail_dict['replying'] = replier.generate_recipients(
                sender, to, ccs, current_user)
            return mail_dict

        d = self._mail_service.mail(self._mail_id)
        d.addCallback(lambda mail: populate_reply(mail))
        d.addCallback(
            lambda mail_dict: respond_json_deferred(mail_dict, request))
        d.addErrback(self.generic_error_handling, request)

        return NOT_DONE_YET

    def render_DELETE(self, request):
        def response_failed(failure):
            err(failure, 'something failed')
            request.finish()

        d = self._mail_service.delete_mail(self._mail_id)
        d.addCallback(lambda _: respond_json_deferred(None, request))
        d.addErrback(response_failed)
        return NOT_DONE_YET


class MailResource(BaseResource):

    def __init__(self, services_factory):
        BaseResource.__init__(self, services_factory)

    def getChild(self, mail_id, request):
        _mail_service = self.mail_service(request)
        return Mail(mail_id, _mail_service)
