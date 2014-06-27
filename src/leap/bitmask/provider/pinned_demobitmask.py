# -*- coding: utf-8 -*-
# pinned_demobitmask.py
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
Pinned provider.json and cacert.pem for demo.bitmask.net
"""

DOMAIN = "demo.bitmask.net"

PROVIDER_JSON = """
{
  "api_uri": "https://api.demo.bitmask.net:4430",
  "api_version": "1",
  "ca_cert_fingerprint": "SHA256: 0f17c033115f6b76ff67871872303ff65034efe7dd1b910062ca323eb4da5c7e",
  "ca_cert_uri": "https://demo.bitmask.net/ca.crt",
  "default_language": "en",
  "description": {
    "el": "demo.bitmask.net allows you to test the Bitmask application. User accounts may be periodically deleted.",
    "en": "demo.bitmask.net allows you to test the Bitmask application. User accounts may be periodically deleted.",
    "es": "demo.bitmask.net allows you to test the Bitmask application. User accounts may be periodically deleted."
  },
  "domain": "demo.bitmask.net",
  "enrollment_policy": "open",
  "languages": [
    "en"
  ],
  "name": {
    "en": "Bitmask"
  },
  "service": {
    "allow_anonymous": true,
    "allow_free": true,
    "allow_limited_bandwidth": false,
    "allow_paid": true,
    "allow_registration": true,
    "allow_unlimited_bandwidth": true,
    "bandwidth_limit": 102400,
    "default_service_level": 1,
    "levels": [
      {
        "id": 1,
        "name": "free",
        "storage": 50
      },
      {
        "id": 2,
        "name": "basic",
        "rate": [
          "US$10",
          "\u20ac10"
        ],
        "storage": 1000
      },
      {
        "id": 3,
        "name": "pro",
        "rate": [
          "US$20",
          "\u20ac20"
        ],
        "storage": 10000
      }
    ]
  },
  "services": [
    "openvpn"
  ]
}
"""

CACERT_PEM = """-----BEGIN CERTIFICATE-----
MIIFbzCCA1egAwIBAgIBATANBgkqhkiG9w0BAQ0FADBKMRgwFgYDVQQDDA9CaXRt
YXNrIFJvb3QgQ0ExEDAOBgNVBAoMB0JpdG1hc2sxHDAaBgNVBAsME2h0dHBzOi8v
Yml0bWFzay5uZXQwHhcNMTIxMTA2MDAwMDAwWhcNMjIxMTA2MDAwMDAwWjBKMRgw
FgYDVQQDDA9CaXRtYXNrIFJvb3QgQ0ExEDAOBgNVBAoMB0JpdG1hc2sxHDAaBgNV
BAsME2h0dHBzOi8vYml0bWFzay5uZXQwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAw
ggIKAoICAQC1eV4YvayaU+maJbWrD4OHo3d7S1BtDlcvkIRS1Fw3iYDjsyDkZxai
dHp4EUasfNQ+EVtXUvtk6170EmLco6Elg8SJBQ27trE6nielPRPCfX3fQzETRfvB
7tNvGw4Jn2YKiYoMD79kkjgyZjkJ2r/bEHUSevmR09BRp86syHZerdNGpXYhcQ84
CA1+V+603GFIHnrP+uQDdssW93rgDNYu+exT+Wj6STfnUkugyjmPRPjL7wh0tzy+
znCeLl4xiV3g9sjPnc7r2EQKd5uaTe3j71sDPF92KRk0SSUndREz+B1+Dbe/RGk4
MEqGFuOzrtsgEhPIX0hplhb0Tgz/rtug+yTT7oJjBa3u20AAOQ38/M99EfdeJvc4
lPFF1XBBLh6X9UKF72an2NuANiX6XPySnJgZ7nZ09RiYZqVwu/qt3DfvLfhboq+0
bQvLUPXrVDr70onv5UDjpmEA/cLmaIqqrduuTkFZOym65/PfAPvpGnt7crQj/Ibl
DEDYZQmP7AS+6zBjoOzNjUGE5r40zWAR1RSi7zliXTu+yfsjXUIhUAWmYR6J3KxB
lfsiHBQ+8dn9kC3YrUexWoOqBiqJOAJzZh5Y1tqgzfh+2nmHSB2dsQRs7rDRRlyy
YMbkpzL9ZsOUO2eTP1mmar6YjCN+rggYjRrX71K2SpBG6b1zZxOG+wIDAQABo2Aw
XjAdBgNVHQ4EFgQUuYGDLL2sswnYpHHvProt1JU+D48wDgYDVR0PAQH/BAQDAgIE
MAwGA1UdEwQFMAMBAf8wHwYDVR0jBBgwFoAUuYGDLL2sswnYpHHvProt1JU+D48w
DQYJKoZIhvcNAQENBQADggIBADeG67vaFcbITGpi51264kHPYPEWaXUa5XYbtmBl
cXYyB6hY5hv/YNuVGJ1gWsDmdeXEyj0j2icGQjYdHRfwhrbEri+h1EZOm1cSBDuY
k/P5+ctHyOXx8IE79DBsZ6IL61UKIaKhqZBfLGYcWu17DVV6+LT+AKtHhOrv3TSj
RnAcKnCbKqXLhUPXpK0eTjPYS2zQGQGIhIy9sQXVXJJJsGrPgMxna1Xw2JikBOCG
htD/JKwt6xBmNwktH0GI/LVtVgSp82Clbn9C4eZN9E5YbVYjLkIEDhpByeC71QhX
EIQ0ZR56bFuJA/CwValBqV/G9gscTPQqd+iETp8yrFpAVHOW+YzSFbxjTEkBte1J
aF0vmbqdMAWLk+LEFPQRptZh0B88igtx6tV5oVd+p5IVRM49poLhuPNJGPvMj99l
mlZ4+AeRUnbOOeAEuvpLJbel4rhwFzmUiGoeTVoPZyMevWcVFq6BMkS+jRR2w0jK
G6b0v5XDHlcFYPOgUrtsOBFJVwbutLvxdk6q37kIFnWCd8L3kmES5q4wjyFK47Co
Ja8zlx64jmMZPg/t3wWqkZgXZ14qnbyG5/lGsj5CwVtfDljrhN0oCWK1FZaUmW3d
69db12/g4f6phldhxiWuGC/W6fCW5kre7nmhshcltqAJJuU47iX+DarBFiIj816e
yV8e
-----END CERTIFICATE-----"""
