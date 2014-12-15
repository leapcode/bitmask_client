# -*- coding: utf-8 -*-
# pinned_calyx.py
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

DOMAIN = "calyx.net"

PROVIDER_JSON = """
{
  "api_uri": "https://api.calyx.net:4430",
  "api_version": "1",
  "ca_cert_fingerprint": "SHA256: 43683c9ba3862c5384a8c1885072fcac40b5d2d4dd67331443f13a3077fa2e69",
  "ca_cert_uri": "https://calyx.net/ca.crt",
  "default_language": "en",
  "description": {
    "en": "Calyx Institute privacy focused ISP testbed"
  },
  "domain": "calyx.net",
  "enrollment_policy": "open",
  "languages": [
    "en"
  ],
  "name": {
    "en": "calyx"
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
MIIFYzCCA0ugAwIBAgIBATANBgkqhkiG9w0BAQ0FADBEMQ4wDAYDVQQKDAVjYWx5
eDEaMBgGA1UECwwRaHR0cHM6Ly9jYWx5eC5uZXQxFjAUBgNVBAMMDWNhbHl4IFJv
b3QgQ0EwHhcNMTMwNzAyMDAwMDAwWhcNMjMwNzAyMDAwMDAwWjBEMQ4wDAYDVQQK
DAVjYWx5eDEaMBgGA1UECwwRaHR0cHM6Ly9jYWx5eC5uZXQxFjAUBgNVBAMMDWNh
bHl4IFJvb3QgQ0EwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQDupdnx
Bgat537XOqrZOulE/RvjoXB1S07sy9/MMtksXFoQuWJZRCSTp1Jaqg3H/e9o1nct
LQO91+izfJe07TUyajFl7CfllYgMeyKTYcT85dFwNX4pcIHZr8UpmO0MpGBoR4W1
8cPa3vxAG0CsyUmrASJVyhRouk4qazRosM5RwBxTdMzCK7L3SwqPQoxlY9YmRJlD
XYZlK5VMJd0dj9XxhMeFs5n43R0bsDENryrExSbuxoNfnUoQg3wffKk+Z0gW7YgW
ivPsbObqOgXUuBEU0xr9xMNBpU33ffLIsccrHq1EKp8zGfCOcww6v7+zEadUkVLo
6j/rRhYYgRw9lijZG1rMuV/mTGnUqbjHsdoz5mzkFFWeTSqo44lvhveUyCcwRNmi
2sjS77l0fCTzfreufffFoOEcRVMRfsnJdu/xPeARoXILEx8nQ421mSn6spOZlDQr
Tt0T0BAWt+VNc+m0IGSW3SwS7r5MUyQ/M5GrbQBGi5W2SzPriKZ79YTOwPVmXKLZ
vJoEuKRDkEPJLBAhcD5oSQljOm/Wp/hjmRH4HnI1y4XMshWlDsyRDB1Au5yrsfwN
noFVSskEcbXlZfNgml4lktLBqz+qwsw+voq6Ak7ROKbc0ii5s8+iNMbAtIK7GcFF
kuKKIyRmmGlDim/SDhlNdWo7Ah4Akde7zfWufwIDAQABo2AwXjAdBgNVHQ4EFgQU
AY8+K4ZupAQ+L9ttFJG3vaLBq5gwDgYDVR0PAQH/BAQDAgIEMAwGA1UdEwQFMAMB
Af8wHwYDVR0jBBgwFoAUAY8+K4ZupAQ+L9ttFJG3vaLBq5gwDQYJKoZIhvcNAQEN
BQADggIBAOpXi5o3g/2o2rPa53iG7Zgcy8RpePGgZk6xknGYWeLamEqSh+XWQZ2w
2kQP54bf8HfPj3ugJBWsVtYAs/ltJwzeBfYDrwEJd1N8tw2IRuGlQOWiTAVVLBj4
Zs+dikSuMoA399f/7BlUIEpVLUiV/emTtbkjFnDeKEV9zql6ypR0BtR8Knf8ALvL
YfMsWLvTe4rXeypzxIaE2pn8ttcXLYAX0ml2MofTi5xcDhMn1vznKIvs82xhncQx
I1MJMWqPHNHgJUJpA+y1IFh5LPbpag9PKQ0yQ9sM+/dyGumF2jElsMw71flh/Txr
2dEv8+FNV1pPK26XJZBK24rNWFs30eAFfH9EQCwVla174I4PDoWqsIR7vtQMObDt
Bq34R3TjjJJIt2sCSlYLooWwiK7Q+d/SgYqA+MSDmmwhzm86ToK6cwbCsvuw1AxR
X6VIs4U8wOotgljzX/CSpKqlxcqZjhnAuelZ1+KiN8RHKPj7AzSLYOv/YwTjLTIq
EOxquoNR58uDa5pBG22a7xWbSaKosn/mEl8SrUr6klzzc8Vh09IMoxrw74uLdAg2
1jnrhm7qg91Ttb0aXiqbV+Kg/qQzojdewnnoBFnv4jaQ3y8zDCfMhsBtWlWz4Knb
Zqga1WyRm3Gj1j6IV0oOincYMrw5YA7bgXpwop/Lo/mmliMA14ps
-----END CERTIFICATE-----"""
