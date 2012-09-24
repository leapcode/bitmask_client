leap_provider_spec = {
    'description': 'provider definition',
    'type': 'object',
    'properties': {
        'serial': {
            'type': int,
            'default': 1,
            'required': True,
        },
        'version': {
            'type': unicode,
            'default': '0.1.0'
            #'required': True
        },
        'domain': {
            'type': unicode,  # XXX define uri type
            'default': 'testprovider.example.org'
            #'required': True,
        },
        'display_name': {
            'type': dict,  # XXX multilingual object?
            'default': {u'en': u'Test Provider'}
            #'required': True
        },
        'description': {
            'type': dict,
            'default': {u'en': u'Test provider'}
        },
        'enrollment_policy': {
            'type': unicode,  # oneof ??
            'default': 'open'
        },
        'services': {
            'type': list,  # oneof ??
            'default': ['eip']
        },
        'api_version': {
            'type': unicode,
            'default': '0.1.0'  # version regexp
        },
        'api_uri': {
            'type': unicode  # uri
        },
        'public_key': {
            'type': unicode  # fingerprint
        },
        'ca_cert_fingerprint': {
            'type': unicode,
        },
        'ca_cert_uri': {
            'type': unicode,
            'format': 'https-uri'
        },
        'languages': {
            'type': list,
            'default': ['en']
        }
    }
}
