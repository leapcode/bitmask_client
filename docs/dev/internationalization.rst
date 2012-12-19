.. _i18n:

Internationalization
====================

This part of the documentation covers the localization and translation of LEAP Client.
Because we want to *bring fire to the people*, in as many countries and languages as possible.

.. note::
   We should probably move the translators info to a top level section of the docs, and leave this
   as internal/tech-savvy notes.

Translating the LEAP Client PyQt Application
--------------------------------------------

.. raw:: html

   <div> <a target="_blank" style="text-decoration:none; color:black; font-size:66%" href="https://www.transifex.com/projects/p/leap-client/resource/leap_client_es/" title="See more information on Transifex.com">Top translations: leap-client » leap_client_es</a><br/> <img border="0" src="https://www.transifex.com/projects/p/leap-client/resource/leap_client_es/chart/image_png"/><br/><a target="_blank" href="https://www.transifex.com/"><img border="0" src="https://ds0k0en9abmn1.cloudfront.net/static/charts/images/tx-logo-micro.646b0065fce6.png"/></a></div>


For translators
^^^^^^^^^^^^^^^
.. note::
   ... unfinished

We are using `transifex <http://transifex.com/projects/p/leap-client>`_ site to coordinate translation efforts. If you want to contribute, just sign up there and ...

.. note::
   ... and what??

For devs: i18n conventions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   should link to PyQt docs on i18n
   also our special cases (labels and exceptions)

tl;dr;::

     self.tr('your string')

for any string that you want to be translated.

For i18n maintainers
^^^^^^^^^^^^^^^^^^^^

.. note::

   how do we use the transifex client; automation.

If you do not already have it, install the ``transifex-client`` from the cheese shop::

   pip install  transifex-client


Translating the Documentation
------------------------------

.. note::
   ...unfinished

`translating sphinx docs <http://sphinx-doc.org/intl.html>`_
