.. _encodings:

Strings encoding problems
=========================

This document is meant to avoid ``UnicodeError`` (``UnicodeEncodeError`` , ``UnicodeDecodeError``) and to set a base that allows the users to keep away headaches.


First approach
--------------

One of the problems with python 2 that makes hard to find out problems is the implicit conversion between ``str`` and ``unicode``.

Look at this code::

    >>> u'ä'.encode('utf-8')
    '\xc3\xa4'
    >>>
    >>> u'ä'.decode('utf-8')
    Traceback (most recent call last):
    File "<stdin>", line 1, in <module>
    File "/usr/lib/python2.7/encodings/utf_8.py", line 16, in decode
        return codecs.utf_8_decode(input, errors, True)
    UnicodeEncodeError: 'ascii' codec can't encode character u'\xe4' in position 0: ordinal not in range(128)

A situation like this could happen if the user confuse one type for another. 'encode' is a method of ``unicode`` and 'decode' is a method of ``str``, since you call 'decode', python "knows" how to convert from ``unicode`` to ``str`` and then call the 'decode' method, *that* conversion is made with the safe default "ascii" which raises an exception.


We need to know which one we are using **every time**. A possible way to avoid mistakes is to use ``leap_assert_type`` at the beginning of each method that has a ``str``/``unicode`` parameter.
The best approach we need to use ``unicode`` internally and when we read/write/transmit data, encode it to bytes (``str``).


Examples of problems found
--------------------------

* **logging data**: ``logger.debug("some string {0}".format(some_data))`` may fail if we have an ``unicode`` parameter because of the conversion needed to output it.
    We need to use ``repr(some_data)`` to avoid encoding problems when sending data to the stdout. An easy way to do it is: ``logger.debug("some string {0!r}".format(some_data))``

- **paths encoding**: we should return always ``unicode`` values from helpers and encode them when we need to use it.
    The stdlib handles correctly ``unicode`` strings path parameters.
    If we want to do something else with the paths, we need to convert them manually using the system encoding.

Regarding the encoding, use a hardcoded encoding may be wrong.
Instead of encode/decode using for instance 'utf-8', we should use this ``sys.getfilesystemencoding()``

For the data stored in a db (or something that is some way isolated from the system) we may want to choose 'utf-8' explicitly.

Steps to improve code
---------------------

#. From now on, keep in mind the difference between ``str`` and ``unicode`` and write code consequently.
#. For each method we can add a ``leap_assert_type(parameter_name, unicode)`` (or ``str``) to avoid type problems.
#. Each time that is possible move towards the unicode 'frontier' (``unicode`` inside, ``str`` (bytes) outside).
#. When is possible update the methods parameters in order to be certain of the data types that we are handling.

Recommended info
----------------

* PyCon 2012 talk: https://www.youtube.com/watch?v=sgHbC6udIqc
    * article and transcription: http://nedbatchelder.com/text/unipain.html
* PyConAr 2012 (Spanish): http://www.youtube.com/watch?v=pQJ0emlYv50
* Overcoming frustrations: http://pythonhosted.org/kitchen/unicode-frustrations.html
* Python's Unicode howto: http://docs.python.org/2/howto/unicode.html
* An encoding primer: http://www.danielmiessler.com/study/encoding/
