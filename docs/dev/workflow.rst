.. _workflow:

Development Workflow
====================

This section documents the workflow that the LEAP project team follows and expects for the code contributions.

While reading this guide, you should have in mind the two rules of contributing code:

* The first rule of code contribution is: Nobody will push unreviewed code to the mainline branches.
* The second rule of code contribution is: Nobody will push unreviewed code to the mainline branches.

Code formatting
---------------
In one word: `PEP8`_.

`autopep8` might be your friend. or eat your code.

.. _`PEP8`: http://www.python.org/dev/peps/pep-0008/
.. _`autopep8`: http://pypi.python.org/pypi/autopep8

Dependencies
------------
If you introduce a new dependency, please add it under ``pkg/requirements`` or ``pkg/test-requirements`` as appropiate, under the proper module section.

Git flow
--------
We are basing our workflow on what is described in `A successful git branching model <http://nvie.com/posts/a-successful-git-branching-model/>`_.

.. image:: https://downloads.leap.se/pics/git-branching-model.png

Vincent Driessen, the author of the aforementioned post has also a handy pdf version of it: `branching_model.pdf`_

However, we use a slightly modified setup in which each developer maintains her
own feature branch in her private repo. After a code review, this feature branch
is rebased onto the authoritative integration branch. Thus, the leapcode repo in
leap.se (mirrored in github) only maintains the master and develop branches.  

A couple of tools that help to follow this process are  `git-flow`_ and `git-sweep`_.

.. _`branching_model.pdf`: https://leap.se/code/attachments/14/Git-branching-model.pdf
.. _`git-flow`: https://github.com/nvie/gitflow
.. _`git-sweep`: http://pypi.python.org/pypi/git-sweep

Code review and merges into integration branch
-----------------------------------------------
All code ready to be merged into the integration branch is expected to:

* Have tests
* Be documented
* Pass existing tests: do **run_tests.sh** and **tox -v**. All feature branches are automagically built by our `buildbot farm <http://lemur.leap.se:8010/grid>`_. So please check your branch is green before merging it it to `develop`. Rebasing against the current tip of the integration when possible is preferred in order to keep a clean history.

Using Github
------------

Particularly for the Bitmask client, we are using Github. So you should fork the repo from `github`_ . Depending on what kind of work you are going to do (bug or feature) you should **create a branch** with the following name:

``bug/some_descriptive_text``

or

``feature/some_descriptive_text``

Do your work there, push it, and create a pull request against the develop branch in the main repo (the one owned by leapcode). Now you should wait until we see it, or you can try also posting your pull request in ``#leap-dev`` at `freenode <https://freenode.net>`_.

Your code will get reviewed/discussed by someone else on the team. In case that you need to make some changes, you would do the following::

  git checkout <your branch>

*Edit what you need here ...*

Simple commit, this doesn't need a good commit message::

  git commit -avm "Fix"

This will help you reorder your commits and squash them (so that the
final commit list has good representative messages)::

  git rebase -i develop

Since you've rewritten your history, you'll need a force push::

  git push <your remote> +<your branch>

This will update your pull request automatically, but it won't notify us about the update, so you should add a comment saying so, or re-pingthe reviewer.

.. _`github`: https://github.com/leapcode/

Other methods
-------------

Feel free to use any other methods like format-patch and mail or whatever method you prefer, although we recommend you follow the same workflow as we do.
