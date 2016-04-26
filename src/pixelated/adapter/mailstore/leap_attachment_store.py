
import quopri
import base64
from email import encoders
from leap.mail.adaptors.soledad import SoledadMailAdaptor, ContentDocWrapper
from twisted.internet import defer
from email.mime.nonmultipart import MIMENonMultipart
from email.mime.multipart import MIMEMultipart
from leap.mail.mail import Message


class LeapAttachmentStore(object):

    def __init__(self, soledad):
        self.soledad = soledad

    @defer.inlineCallbacks
    def get_mail_attachment(self, attachment_id):
        results = yield self.soledad.get_from_index('by-type-and-payloadhash', 'cnt', attachment_id) if attachment_id else []
        if results:
            content = ContentDocWrapper(**results[0].content)
            defer.returnValue({'content-type': content.content_type, 'content': self._try_decode(
                content.raw, content.content_transfer_encoding)})
        else:
            raise ValueError('No attachment with id %s found!' % attachment_id)

    @defer.inlineCallbacks
    def add_attachment(self, content, content_type):
        cdoc = self._attachment_to_cdoc(content, content_type)
        attachment_id = cdoc.phash
        try:
            yield self.get_mail_attachment(attachment_id)
        except ValueError:
            yield self.soledad.create_doc(cdoc.serialize(), doc_id=attachment_id)
        defer.returnValue(attachment_id)

    def _try_decode(self, raw, encoding):
        encoding = encoding.lower()
        if encoding == 'base64':
            data = base64.decodestring(raw)
        elif encoding == 'quoted-printable':
            data = quopri.decodestring(raw)
        else:
            data = str(raw)

        return bytearray(data)

    def _attachment_to_cdoc(self, content, content_type, encoder=encoders.encode_base64):
        major, sub = content_type.split('/')
        attachment = MIMENonMultipart(major, sub)
        attachment.set_payload(content)
        encoder(attachment)
        attachment.add_header('Content-Disposition',
                              'attachment', filename='does_not_matter.txt')

        pseudo_mail = MIMEMultipart()
        pseudo_mail.attach(attachment)

        tmp_mail = SoledadMailAdaptor().get_msg_from_string(
            MessageClass=Message, raw_msg=pseudo_mail.as_string())

        cdoc = tmp_mail.get_wrapper().cdocs[1]
        return cdoc

    def _calc_attachment_id_(self, content, content_type, encoder=encoders.encode_base64):
        cdoc = self._attachment_to_cdoc(content, content_type, encoder)
        return cdoc.phash
