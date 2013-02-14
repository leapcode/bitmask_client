==================================
User-facing changes in Leap Client
==================================

Release 0.2.0 "The Eternal Friday Release" (2013-2-15)
------------------------------------------------------

This release is the first functionally working version released for the
LEAP Client.

It can be installed from pypi, or using the official leap repository at
``deb.leap.se``. Packages are built for:

* debian: wheezy and sid
* ubuntu: precise, quantal and raring

On first use, the first connection wizard guides user through steps needed
to stablish a Encrypted Internet Proxy (EIP) connection with the chosen provider.

Python Support
''''''''''''''
This release supports Python2.6 and Python2.7

New Features
''''''''''''
- First run wizard: allows to register an user with the selected provider. It also downloads all
  the config files needed to connect to the eip service on this provider.
- Network checks: we do some basic network testing and warn user in case we cannot find a
  suitable network interface, or if the virtual interface dissapears after a successful eip connection.
- Debug mode and logfiles: the leap-client script allows to be invoked with the --debug flag.
  It also accepts a --logfile option that is useful for documenting bug reports.

Dependencies
''''''''''''
See the ``README.rst`` for a step-to-step install guide.

The following libraries are needed:

- PyQt4
- openssl
- openvpn

for building the package dependencies, you will need also:

- python-setuptools
- python-dev

LEAP-Client depends also on the following python packages:

- requests
- psutil
- netifaces
- pyopenssl
- jsonschema
- srp
- pycrypto
- keyring
- python-dateutil
- sh
- pyxdg


Configuration files
'''''''''''''''''''

Config files are created under ``~/.config/leap``

Currently user should be able to completely remove this folder and have it auto-generated in the first run.

- Current eip service config is stored in ``eip.json``
- Under ``.config/leap/providers``, there is a per-provider folder that contains:
  - ``provider.json``, with all options for connecting to this provider.
  - ``eip-service.json``, with eip-specific configuration options,
  - ``keys/ca``, for a copy of the ca certificates used in the tls connections to provider.
  - ``keys/client``, for a local copy of leap user certificates used in the eip connection.
- ``leap.conf`` for general application configurations (gui windows geometry, ...).
