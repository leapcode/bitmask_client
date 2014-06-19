# -*- coding: utf-8 -*-
# pinned_riseup.py
# Copyright (C) 2013-2014 LEAP
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
"""
Pinned provider.json and cacert.pem for riseup.net
"""

DOMAIN = "riseup.net"

PROVIDER_JSON = """
{
  "api_uri": "https://api.black.riseup.net:4430",
  "api_version": "1",
  "ca_cert_fingerprint": "SHA256: a5244308a1374709a9afce95e3ae47c1b44bc2398c0a70ccbf8b3a8a97f29494",
  "ca_cert_uri": "https://black.riseup.net/ca.crt",
  "default_language": "en",
  "description": {
    "en": "Riseup is a non-profit collective in Seattle that provides online communication tools for people and groups working toward liberatory social change."
  },
  "domain": "riseup.net",
  "enrollment_policy": "open",
  "languages": [
    "en"
  ],
  "name": {
    "en": "Riseup Networks"
  },
  "service": {
    "allow_anonymous": false,
    "allow_free": true,
    "allow_limited_bandwidth": false,
    "allow_paid": false,
    "allow_registration": true,
    "allow_unlimited_bandwidth": true,
    "bandwidth_limit": 102400,
    "default_service_level": 1,
    "levels": {
      "1": {
        "description": "Please donate.",
        "name": "free"
      }
    }
  },
  "services": [
    "openvpn"
  ]
}
"""

CACERT_PEM = """-----BEGIN CERTIFICATE-----
MIIFjTCCA3WgAwIBAgIBATANBgkqhkiG9w0BAQ0FADBZMRgwFgYDVQQKDA9SaXNl
dXAgTmV0d29ya3MxGzAZBgNVBAsMEmh0dHBzOi8vcmlzZXVwLm5ldDEgMB4GA1UE
AwwXUmlzZXVwIE5ldHdvcmtzIFJvb3QgQ0EwHhcNMTQwNDI4MDAwMDAwWhcNMjQw
NDI4MDAwMDAwWjBZMRgwFgYDVQQKDA9SaXNldXAgTmV0d29ya3MxGzAZBgNVBAsM
Emh0dHBzOi8vcmlzZXVwLm5ldDEgMB4GA1UEAwwXUmlzZXVwIE5ldHdvcmtzIFJv
b3QgQ0EwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQC76J4ciMJ8Sg0m
TP7DF2DT9zNe0Csk4myoMFC57rfJeqsAlJCv1XMzBmXrw8wq/9z7XHv6n/0sWU7a
7cF2hLR33ktjwODlx7vorU39/lXLndo492ZBhXQtG1INMShyv+nlmzO6GT7ESfNE
LliFitEzwIegpMqxCIHXFuobGSCWF4N0qLHkq/SYUMoOJ96O3hmPSl1kFDRMtWXY
iw1SEKjUvpyDJpVs3NGxeLCaA7bAWhDY5s5Yb2fA1o8ICAqhowurowJpW7n5ZuLK
5VNTlNy6nZpkjt1QycYvNycffyPOFm/Q/RKDlvnorJIrihPkyniV3YY5cGgP+Qkx
HUOT0uLA6LHtzfiyaOqkXwc4b0ZcQD5Vbf6Prd20Ppt6ei0zazkUPwxld3hgyw58
m/4UIjG3PInWTNf293GngK2Bnz8Qx9e/6TueMSAn/3JBLem56E0WtmbLVjvko+LF
PM5xA+m0BmuSJtrD1MUCXMhqYTtiOvgLBlUm5zkNxALzG+cXB28k6XikXt6MRG7q
hzIPG38zwkooM55yy5i1YfcIi5NjMH6A+t4IJxxwb67MSb6UFOwg5kFokdONZcwj
shczHdG9gLKSBIvrKa03Nd3W2dF9hMbRu//STcQxOailDBQCnXXfAATj9pYzdY4k
ha8VCAREGAKTDAex9oXf1yRuktES4QIDAQABo2AwXjAdBgNVHQ4EFgQUC4tdmLVu
f9hwfK4AGliaet5KkcgwDgYDVR0PAQH/BAQDAgIEMAwGA1UdEwQFMAMBAf8wHwYD
VR0jBBgwFoAUC4tdmLVuf9hwfK4AGliaet5KkcgwDQYJKoZIhvcNAQENBQADggIB
AGzL+GRnYu99zFoy0bXJKOGCF5XUXP/3gIXPRDqQf5g7Cu/jYMID9dB3No4Zmf7v
qHjiSXiS8jx1j/6/Luk6PpFbT7QYm4QLs1f4BlfZOti2KE8r7KRDPIecUsUXW6P/
3GJAVYH/+7OjA39za9AieM7+H5BELGccGrM5wfl7JeEz8in+V2ZWDzHQO4hMkiTQ
4ZckuaL201F68YpiItBNnJ9N5nHr1MRiGyApHmLXY/wvlrOpclh95qn+lG6/2jk7
3AmihLOKYMlPwPakJg4PYczm3icFLgTpjV5sq2md9bRyAg3oPGfAuWHmKj2Ikqch
Td5CHKGxEEWbGUWEMP0s1A/JHWiCbDigc4Cfxhy56CWG4q0tYtnc2GMw8OAUO6Wf
Xu5pYKNkzKSEtT/MrNJt44tTZWbKV/Pi/N2Fx36my7TgTUj7g3xcE9eF4JV2H/sg
tsK3pwE0FEqGnT4qMFbixQmc8bGyuakr23wjMvfO7eZUxBuWYR2SkcP26sozF9PF
tGhbZHQVGZUTVPyvwahMUEhbPGVerOW0IYpxkm0x/eaWdTc4vPpf/rIlgbAjarnJ
UN9SaWRlWKSdP4haujnzCoJbM7dU9bjvlGZNyXEekgeT0W2qFeGGp+yyUWw8tNsp
0BuC1b7uW/bBn/xKm319wXVDvBgZgcktMolak39V7DVO
-----END CERTIFICATE-----"""
