.. _resources:

PyQt Resource files
===================

Compiling resource/ui files
---------------------------

You should refresh resource/ui files every time you change an image or a resource/ui (.ui / .qc). From the root folder::

  % make ui
  % make resources

As there are some tests to guard against unwanted resource updates, you will have to update the resource hash in those failing tests.
