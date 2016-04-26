#
# Copyright (c) 2014 ThoughtWorks, Inc.
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.
import cgi
import io
import re
import logging

from twisted.internet import defer
from twisted.protocols.basic import FileSender
from twisted.python.log import msg
from twisted.web import server
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

from pixelated.resources import respond_json_deferred, BaseResource

logger = logging.getLogger(__name__)


class AttachmentResource(Resource):
    isLeaf = True

    def __init__(self, mail_service, attachment_id):
        Resource.__init__(self)
        self.attachment_id = attachment_id
        self.mail_service = mail_service

    def render_GET(self, request):
        def error_handler(failure):
            msg(failure, 'attachment not found')
            request.code = 404
            request.finish()

        encoding = request.args.get('encoding', [None])[0]
        filename = request.args.get('filename', [self.attachment_id])[0]
        content_type = request.args.get(
            'content_type', ['application/octet-stream'])[0]
        request.setHeader(b'Content-Type', content_type)
        request.setHeader(b'Content-Disposition',
                          bytes('attachment; filename="' + filename + '"'))

        d = self._send_attachment(encoding, filename, request)
        d.addErrback(error_handler)

        return server.NOT_DONE_YET

    @defer.inlineCallbacks
    def _send_attachment(self, encoding, filename, request):
        attachment = yield self.mail_service.attachment(self.attachment_id)

        bytes_io = io.BytesIO(attachment['content'])

        try:
            request.code = 200
            yield FileSender().beginFileTransfer(bytes_io, request)
        finally:
            bytes_io.close()
            request.finish()

    def _extract_mimetype(self, content_type):
        match = re.compile('([A-Za-z-]+\/[A-Za-z-]+)').search(content_type)
        return match.group(1)


class AttachmentsResource(BaseResource):
    BASE_URL = 'attachment'

    def __init__(self, services_factory):
        BaseResource.__init__(self, services_factory)

    def getChild(self, attachment_id, request):
        _mail_service = self.mail_service(request)
        return AttachmentResource(_mail_service, attachment_id)

    def render_POST(self, request):
        _mail_service = self.mail_service(request)
        fields = cgi.FieldStorage(fp=request.content, headers=(request.getAllHeaders()),
                                  environ={'REQUEST_METHOD': 'POST'})
        _file = fields['attachment']
        deferred = _mail_service.save_attachment(_file.value, _file.type)

        def send_location(attachment_id):
            request.headers[
                'Location'] = '/%s/%s' % (self.BASE_URL, attachment_id)
            response_json = {"ident": attachment_id,
                             "content-type": _file.type,
                             "encoding": "base64",  # hard coded for now -- not really used
                             "name": _file.filename,
                             "size": len(_file.value)}
            respond_json_deferred(response_json, request, status_code=201)

        def error_handler(error):
            logger.error(error)
            respond_json_deferred(
                {"message": "Something went wrong. Attachment not saved."}, request, status_code=500)

        deferred.addCallback(send_location)
        deferred.addErrback(error_handler)

        return NOT_DONE_YET
