# -*- coding: utf-8 -*-
# provider_spec.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

leap_provider_spec = {
    'description': 'provider definition',
    'type': 'object',
    'properties': {
        'version': {
            'type': unicode,
            'default': '0.1.0'
        },
        "default_language": {
            'type': unicode,
            'default': 'en'
        },
        'domain': {
            'type': unicode,  # XXX define uri type
            'default': 'testprovider.example.org'
        },
        'name': {
            'type': dict,
            'format': 'translatable',
            'default': {u'en': u'Test Provider'}
        },
        'description': {
            #'type': LEAPTranslatable,
            'type': dict,
            'format': 'translatable',
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
        },
        'service': {
            'levels': {
                'type': list
            },
            'default_service_level': {
                'type': int,
                'default': 1
            },
            'allow_free': {
                'type': unicode
            },
            'allow_paid': {
                'type': unicode
            },
            'allow_anonymous': {
                'type': unicode
            },
            'allow_registration': {
                'type': unicode
            },
            'bandwidth_limit': {
                'type': int
            },
            'allow_limited_bandwidth': {
                'type': unicode
            },
            'allow_unlimited_bandwidth': {
                'type': unicode
            }
        }
    }
}
