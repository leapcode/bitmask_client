leap_provider_spec = {
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
        'type': unicode,  # XXX multilingual object?
        'default': 'test provider'
        #'required': True
    },
    'description': {
        'default': 'test provider'
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
    'ca_cert': {
        'type': unicode
    },
    'ca_cert_uri': {
        'type': unicode
    },
}
