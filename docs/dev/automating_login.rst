.. _automating_login:

Automating login
================

There's an annoying bug with python keyring module, that makes the 'remember
login' checkbox non functional.

That, and the need to script end-to-end tests with the client inside a docker
environment, made us put a mechanism to pass credentials via environment
variables.

To automate login, set BITMASK_CREDENTIALS env var::

  BITMASK_CREDENTIALS=/tmp/secrets.conf bitmask --debug

where the pointed file looks like this::

  [Credentials]
  username = user@provider
  password = mypass
