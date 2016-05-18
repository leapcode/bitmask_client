Building da bundles
--------------------
Because, you know, bundles are cool. Who needs a decent package manager nowadays? </rant>.

You need a couple of things in your virtualenv:

- All the dependencies. A sumo tarball is probably a good idea.
- PyInstaller. Version 3 or higher.
- A PySide build. While the postmkenv.sh hack is good enough for
  developing, you will need a wheel built with --standalone flag.
  See
  http://pyside.readthedocs.org/en/latest/building/linux.html#building-pyside-distribution::

    $ python2.7 setup.py bdist_wheel --qmake=/usr/bin/qmake-qt4 --standalone

  (since this takes a while, you can probably grab the already built wheel from
  the leap servers).
