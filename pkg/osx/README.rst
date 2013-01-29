environment setup in osx
========================
(I rm'd my README by mistake at some point. Re-do).

basically you need this to setup your environment:

# check and consolidate

# install xcode and macports 
# port -v selfupdate
# port install python26
# port install python_select  # unneeded?
# port install py26-pyqt4
# port install py26-twisted
# port install py26-pip
# port install py26-virtualenv
# port install git-core
# port install gnutls
# port install platypus

Requirements
============
pyinstaller (in ~/pyinstaller)
platypus (tested with latest macports)

... + install environment as usual,
      inside virtualenv.

.. note:: there is something missing here, about troubles building gnutls extension,
          I think I ended by symlinking global install via macports.

Pyinstaller fix for sip api
---------------------------
We need a workaround for setting the right sip api.
Paste this in the top of pyinstaller/support/rthooks/pyi_rth_qt4plugins.py::

    import sip
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)

See www.pyinstaller.org/wiki/Recipe/PyQtChangeApiVersion.

Building the package
====================

Building the binary
-------------------
We use the scripts in openvpn/build.zsh
The packaging Makefile is expecting the final binary in the location::

    ../../openvpn/build/openvpn.leap

Running the build
-----------------
IMPORTANT: activate the VIRTUALENV FIRST!
(you will get an import error otherwise)

For running all steps at once::

    make pkg
