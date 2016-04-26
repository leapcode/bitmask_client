0.10.0 - xxx
+++++++++++++++++++++++++++++++

Please add lines to this file, they will be moved to the CHANGELOG.rst during
the next release.

There are two template lines for each category, use them as reference.

I've added a new category `Misc` so we can track doc/style/packaging stuff.

Features
~~~~~~~~
- `#7552 <https://leap.se/code/issues/7552>`_: Improve UI message and add some margin above the msg box.
- `#7656 <https://leap.se/code/issues/7656>`_: Adapt to multi-user aware events.
- `#4469 <https://leap.se/code/issues/4469>`_: Display randomly generated service token on the Help Window.
- `#6041 <https://leap.se/code/issues/6041>`_: Write service tokens to a file to allow email clients to read them from there.
- Use cred-based authentication on SMTP.
- Experimental support for the Pixelated WebMail.
- Add email panel to preferences window.
- Ability to launch detached bitmask.core daemon, and a simplistic bitmask_cli. Not used by the main client yet.

- `#1234 <https://leap.se/code/issues/1234>`_: Description of the new feature corresponding with issue #1234.
- New feature without related issue number.

Bugfixes
~~~~~~~~
- `#7568 <https://leap.se/code/issues/7568>`_: Fix typo on signal name.
- `#7583 <https://leap.se/code/issues/7583>`_: Fix set_soledad_auth_token event callback signature.
- `#7585 <https://leap.se/code/issues/7585>`_: Open email help link on browser.
- `#7598 <https://leap.se/code/issues/7598>`_: Fix errback on InvalidAuthToken.
- `#7869 <https://leap.se/code/issues/7869>`_: Redownload smtp certificate if needed.
- Do not translate 'https' text on QLabel.

- `#1235 <https://leap.se/code/issues/1235>`_: Description for the fixed stuff corresponding with issue #1235.
- Bugfix without related issue number.

Misc
~~~~
- `#1236 <https://leap.se/code/issues/1236>`_: Description of the new feature corresponding with issue #1236.
- Some change without issue number.

Known Issues
~~~~~~~~~~~~
- `#8057 <https://leap.se/code/issues/8057>`_: Logging out twice produces a segfault in Qt
- `#1236 <https://leap.se/code/issues/1236>`_: Description of the known issue corresponding with issue #1236.
