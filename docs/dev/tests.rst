.. _tests:

Running and writing tests
=========================

.. note::
   should include seeAlso to virtualenv

This section covers the documentation about the tests for the LEAP Client code.
All patches should have tests for them ...


Testing dependencies
--------------------

have a look at ``pkg/test-requirements.pip``
The ``./run_tests.sh`` command should install all of them in your virtualenv for you.

If you prefer to install them system wide, this should do in a Debian system::

    $ apt-get install python-nose python-mock python-coverage


Running tests
-------------

There is a convenience script at ``./run_tests.sh``

If you want to run specific tests, pass the (sub)module to nose::

  $ nosetests leap.util

or::

  $ nosetests leap.util.tests.test_leap_argparse

Hint: colorized output
^^^^^^^^^^^^^^^^^^^^^^

Install ``rednose`` locally, export the ``NOSE_REDNOSE`` variable, and give your eyes a rest :)::

  (bitmask)% pip install rednose
  (bitmask)% export NOSE_REDNOSE=1

Testing all the supported python versions
-----------------------------------------

For running testsuite against all the supported python versions (currently 2.6 and 2.7), run::

  % tox -v

Coverage reports
----------------

Pass the ``-c`` flat to the ``run_tests.sh`` script::

    $ run_tests.sh -c

Using ``coverage`` it will generate beautiful html reports that you can access pointing your browser to ``docs/covhtml/index.html``

.. note::
   The coverage reports will not be generated if all tests are not passing.
