# -*- coding: utf-8 -*-
# pinned_mailbitmask.py
# Copyright (C) 2015 LEAP
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
Pinned provider.json and cacert.pem for mail.bitmask.net
"""

DOMAIN = "mail.bitmask.net"

PROVIDER_JSON = """
{
  "api_uri": "https://api.mail.bitmask.net:4430",
  "api_version": "1",
  "ca_cert_fingerprint": "SHA256: 0f17c033115f6b76ff67871872303ff65034efe7dd1b910062ca323eb4da5c7e",
  "ca_cert_uri": "https://mail.bitmask.net/ca.crt",
  "default_language": "en",
  "description": {
    "el": "Bitmask \u03b5\u03af\u03bd\u03b1\u03b9 \u03ad\u03bd\u03b1 \u03ad\u03c1\u03b3\u03bf \u03c4\u03bf\u03c5 LEAP \u03bc\u03b5 \u03c3\u03ba\u03bf\u03c0\u03cc \u03c4\u03bf\u03bd \u03ad\u03bb\u03b5\u03b3\u03c7\u03bf \u03c4\u03b7\u03c2 \u03b1\u03c0\u03cc\u03b4\u03bf\u03c3\u03b7\u03c2 \u03ba\u03b1\u03b9 \u03c4\u03b7\u03c2 \u03b1\u03be\u03b9\u03bf\u03c0\u03b9\u03c3\u03c4\u03af\u03b1\u03c2 \u03c4\u03bf\u03c5 \u03bb\u03bf\u03b3\u03b9\u03c3\u03bc\u03b9\u03ba\u03bf\u03cd LEAP. Bitmask \u03c4\u03c1\u03ad\u03c7\u03b5\u03b9 \u03b3\u03b9\u03b1 \u03c4\u03b9\u03c2 \u03c4\u03b5\u03bb\u03b5\u03c5\u03c4\u03b1\u03af\u03b5\u03c2 \u03b1\u03b9\u03bc\u03bf\u03c1\u03c1\u03b1\u03b3\u03af\u03b1 \u03ac\u03ba\u03c1\u03bf \u03c4\u03bf\u03c5 \u03ba\u03ce\u03b4\u03b9\u03ba\u03b1 LEAP, \u03ba\u03b1\u03b9 \u03b8\u03b1 \u03ad\u03c7\u03b5\u03b9 \u03c0\u03b9\u03b8\u03b1\u03bd\u03cc\u03c4\u03b1\u03c4\u03b1 \u03c0\u03b5\u03c1\u03b9\u03c3\u03c3\u03cc\u03c4\u03b5\u03c1\u03b5\u03c2 \u03b4\u03c5\u03bd\u03b1\u03c4\u03cc\u03c4\u03b7\u03c4\u03b5\u03c2 \u03ba\u03b1\u03b9 \u03bb\u03b9\u03b3\u03cc\u03c4\u03b5\u03c1\u03b1 \u03b1\u03be\u03b9\u03bf\u03c0\u03b9\u03c3\u03c4\u03af\u03b1 \u03b1\u03c0\u03cc \u03ac\u03bb\u03bb\u03bf\u03c5\u03c2 \u03c6\u03bf\u03c1\u03b5\u03af\u03c2 \u03c0\u03b1\u03c1\u03bf\u03c7\u03ae\u03c2 \u03c5\u03c0\u03b7\u03c1\u03b5\u03c3\u03b9\u03ce\u03bd.",
    "en": "Bitmask is a project of LEAP with the purpose to test the performance and reliability of the LEAP software. Bitmask runs on the latest bleeding edge of the LEAP code, and will likely have more features and less reliability than other service providers.",
    "es": "Bitmask es un proyecto de LEAP con el prop\u00f3sito de probar el rendimiento y la fiabilidad del software LEAP. Bitmask corre la \u00faltima versi\u00f3n del c\u00f3digo LEAP, y es de esperar que tenga m\u00e1s funciones y menos fiabilidad que los proveedores de servicios."
  },
  "domain": "mail.bitmask.net",
  "enrollment_policy": "open",
  "languages": [
    "de",
    "en",
    "es",
    "pt"
  ],
  "name": {
    "en": "Bitmask"
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
    "mx"
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
