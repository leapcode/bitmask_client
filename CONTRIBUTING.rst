Contributing to Bitmask
=======================

:+1::tada: First off, thanks for taking the time to contribute! :tada::+1:

The following is a set of guidelines for contributing to Bitmask and its packages,
which are hosted in the `LEAP git repo`_ and mirrored on the `LEAP
organization`_ on GitHub.
These are just guidelines, not rules, use your best judgment and feel free to
propose changes to this document in a pull request.

This project adheres to the `Contributor Covenant 1.2`_.
By participating, you are expected to uphold this code. Please report
unacceptable behavior to `info@leap.se`_.

.. _`LEAP git repo`: https://leap.se/git/
.. _`LEAP organization`: https://github.com/leapcode
.. _`Contributor Covenant 1.2`: http://contributor-covenant.org/version/1/2/0
.. _`info@leap.se`: info@leap.se


Reporting bugs
--------------

Report all the bugs you can find to us! If something is not quite working yet,
we really want to know. Reporting a bug to us is the best way to get it fixed
quickly, and get our unconditional gratitude.

It is quick, easy, and probably the best way to contribute to Bitmask
development, other than submitting patches.

**Reporting better bugs:** New to bug reporting? Here you have a `great
document about this noble art`_.

.. _`great document about this noble art`: http://www.chiark.greenend.org.uk/~sgtatham/bugs.html

Where to report bugs
~~~~~~~~~~~~~~~~~~~~

We use the `LEAP Issue Tracker`_, although you can also use `Github issues`_.
But we reaaaally prefer if you sign up in the former to send your bugs our way.

.. _`LEAP Issue Tracker`: https://leap.se/code/
.. _`Github issues`: https://github.com/leapcode/bitmask_client/issues

What to include in your bug report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* The symptoms of the bug itself: what went wrong? What items appear broken, or
  do not work as expected? Maybe an UI element that appears to freeze?
* The Bitmask version you are running. You can get it by doing ``bitmask
  --version``, or you can go to ``Help -> About Bitmask`` menu.
* The installation method you used: bundle? from source code? debian package?
* Your platform version and other details: Ubuntu 14.04? Debian unstable?
  Windows 8? OSX 10.8.4? If relevant, your desktop system also (gnome, kde...)
* When does the bug appear? What actions trigger it? Does it always happen, or
  is it sporadic?
* Maybe a screenshot of the problem you're seeing.
* The exact error message, if any.
* Attachments of the log files, if possible (see section below).

Also, try not to mix several issues in your bug report. If you are
finding several problems, it's better to issue a separate bug report for
each one of them.

Attaching log files
~~~~~~~~~~~~~~~~~~~

If you can spend a little time getting them, please add some logs to the
bug report. They are **really** useful when it comes to debug a problem.
To do it:

Launch Bitmask in debug mode. Logs are way more verbose that way::

    bitmask --debug

Get your hand on the logs. You can achieve that either by clicking on
the "Help -\> Show log" menu, and saving to file, or getting the log files from
the config folder.

Need human interaction?
~~~~~~~~~~~~~~~~~~~~~~~

You can also find us in the ``#leap`` channel on the `freenode network`_. If you
do not have a IRC client at hand, you can `enter the channel via web`_.

.. _`freenode network`: https://freenode.net
.. _`enter the channel via web`: http://webchat.freenode.net/?nick=leaper....&channels=%23leap&uio=d4


Pull Requests
=============

* Fork our repo
* Work your code in a separate branch
* Create a pull request against ``develop``
* All tests should pass
* The code needs to be pep8 compliant (run ``pep8 .`` from the top folder)
* Remember to add an entry in the ``changes/`` folder, from where the CHANGELOG
  for a given release is gathered.

Git Commit Messages
-------------------

* Use the present tense ("add feature" not "added feature")
* Use the imperative mood ("move cursor to..." not "moves cursor to...")
* Short (50 chars or less) summary on the first line
* Separate subject from body with a blank line
* Wrap the body at 72 characters or less
* Do not end the subject line with a period
* Use the body to explain what and why vs. how

For a good reference on commit messages and why does it matter see:
http://chris.beams.io/posts/git-commit/

Template for commits
--------------------

You can activate a standard template for your commits on this repo with:

::

    git config commit.template docs/leap-commit-template


The template looks like this:

::

    [type] <subject>

    <body>
    <footer>

Type should be one of the following:

- bug (bug fix)
- feat (new feature)
- docs (changes to documentation)
- style (formatting, pep8 violations, etc; no code change)
- refactor (refactoring production code)
- test (adding missing tests, refactoring tests; no production code change)
- pkg (packaging related changes; no production code change)
- i18n translation related changes

Subject should use imperative tone and say what you did.
For example, use 'change', NOT 'changed' or 'changes'.

The body should go into detail about changes made.

The footer should contain any issue references or actions.
You can use one or several of the following:

- Resolves: #XYZ
- Related: #XYZ
- Documentation: #XYZ
- Releases: XYZ

The Documentation field should be included in every new feature commit, and it
should link to an issue in the bug tracker where the new feature is analyzed
and documented.


Example
-------

::

    [feat] add soledad sync progress to the UI

    Register to Soledad's sync (send and receive) events and display the
    progress in the UI.

    - Resolves: #7353
