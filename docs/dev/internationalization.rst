.. _i18n:

Internationalization
====================

This part of the documentation covers the localization and translation of LEAP Client.
Because we want to *bring fire to the people*, in as many countries and languages as possible.

Translating the LEAP Client PySide Application
--------------------------------------------

.. raw:: html

   <div><a target="_blank" style="text-decoration:none; color:black; font-size:66%" href="https://www.transifex.com/projects/p/leap-client/resource/leap-client/" title="See more information on Transifex.com">Top translations: leap-client » leap-client</a><br/><img border="0" src="https://www.transifex.com/projects/p/leap-client/resource/leap-client/chart/image_png"/><br/><a target="_blank" href="https://www.transifex.com/"><img border="0" src="https://ds0k0en9abmn1.cloudfront.net/static/charts/images/tx-logo-micro.646b0065fce6.png"/></a></div>


For translators
^^^^^^^^^^^^^^^
.. note::
   We should probably move the translators info to a top level section of the docs, and leave this
   as internal notes.


We are using `transifex <http://transifex.com/projects/p/leap-client>`_ to coordinate translation efforts. If you want to contribute, just sign up there and ...

.. note::
   ... and what??

For devs: i18n conventions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   should say something about our special cases (provider labels and exceptions) when we get decision about it.

Refer to `pyside documentation <http://qt-project.org/wiki/PySide_Internationalization>`_.

tl;dr;::

     self.tr('your string')

for any string that you want to be translated, as long as the instance derives from ``QObject``.

.. If you have to translate something that it is not a ``QObject``, use the magic leap ``translate`` method:
.. .. code-block:: python
..    from leap.util.translations import translate
..   class Foo(object):
..        bar = translate(<Context>, <string>, <comment>)


.. Note about this: there seems to be some problems with the .tr method
   so the translate method could actually be the preferred thing in all the cases.
   Still missing what to do for language labels (json-based).
   --kali

For i18n maintainers
^^^^^^^^^^^^^^^^^^^^

You need ``pyside-lupdate`` and ``lrelease`` for these steps. To get it, in debian::

   $ apt-get install pyside-tools qt4-linguist-tools

If you do not already have it, install the ``transifex-client`` from the cheese shop::

   pip install  transifex-client

You can learn more about the transifex-client `here <http://help.transifex.com/features/client/index.html>`_.

**1.** Add any new source files to the project file, ``data/leap_client.pro``. *We should automate this with some templating, it's tedious.*

**2.** Update the source .ts file ``data/ts/en_US.ts``.::

   $ make translations

**3.** Push source .ts file to transifex::

   $ tx push -s

**4.** Let the translation fairies do their work...

**5.** *Et voila!* Get updated .ts files for each language from ``Transifex``. For instance, to pull updated spanish translations:: 

   $ tx pull -l es
   Pulling new translations for resource leap-client.leap-client (source: data/ts/en_US.ts)
   -> es: data/translations/es.ts
   Done.


Note that there is a configuration option in ``.tx/config`` for setting the minimum completion percentage needed to be able to actually pull a resource.

**6.** Generate .qm files from the updated .ts files::

   $ make translations 

and yes, it's the same command than in step 2. One less thing to remember :)

**7.** Check that the .qm for the language you're working with is listed in ``data/resources/locale.qrc`` file. That should take the translated files from ``data/translations``

**8.** Re-generate ``src/leap/gui/locale_qrc``. This is the embedded resource file that we load in the main app entry point; and from where we load the data for the qt translator object::

    $ make resources

If you want to try it, just set your LANG environment variable::

    $ LANG=es_ES leap-client


Translating the Documentation
------------------------------

.. note::
   ...unfinished

`translating sphinx docs <http://sphinx-doc.org/intl.html>`_
