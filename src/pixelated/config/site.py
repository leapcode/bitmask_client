from twisted.web.server import Site, Request


class AddSecurityHeadersRequest(Request):
    CSP_HEADER_VALUES = "default-src 'self'; style-src 'self' 'unsafe-inline'"

    def process(self):
        self.setHeader('Content-Security-Policy', self.CSP_HEADER_VALUES)
        self.setHeader('X-Content-Security-Policy', self.CSP_HEADER_VALUES)
        self.setHeader('X-Webkit-CSP', self.CSP_HEADER_VALUES)
        self.setHeader('X-Frame-Options', 'SAMEORIGIN')
        self.setHeader('X-XSS-Protection', '1; mode=block')
        self.setHeader('X-Content-Type-Options', 'nosniff')

        if self.isSecure():
            self.setHeader('Strict-Transport-Security',
                           'max-age=31536000; includeSubDomains')

        Request.process(self)


class PixelatedSite(Site):

    requestFactory = AddSecurityHeadersRequest

    @classmethod
    def enable_csp_requests(cls):
        cls.requestFactory = AddSecurityHeadersRequest

    @classmethod
    def disable_csp_requests(cls):
        cls.requestFactory = Site.requestFactory
