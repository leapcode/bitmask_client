.. _introduction:

Introduction
============

Bitmask
-------
.. if yoy change this, change it also in the index.rst
**Bitmask** is the multiplatform desktop client for the services offered by :ref:`the LEAP Platform <leapplatform>`.
It is written in python using `PySide`_ and :ref:`licensed under the GPL3 <gpl3>`.
Currently we distribute pre-compiled bundles for Linux and OSX, with Windows
bundles following soon.

Features
^^^^^^^^

Bitmask allows to easily secure communications.

- Provider selection.
- User registration.
- Encrypted Internet Proxy support (autoconfigured service using openvpn).
- Encrypted email.

Coming soon
^^^^^^^^^^^^

- Encrypted chat.


.. _leapplatform:

The LEAP Platform
^^^^^^^^^^^^^^^^^

.. image:: leap-color-small.*

The LEAP Provider Platform is the server-side part of LEAP that is run by service providers. It consists of a set of complementary packages and recipes to automate the maintenance of LEAP services in a hardened GNU/Linux environment. Our goal is to make it painless for service providers and ISPs to deploy a secure communications platform.

Read `more about the LEAP Platform <https://leap.se/en/technology/platform>`_ or `check out the code <https://github.com/leapcode/leap_platform>`_.


.. _philosophy:

Philosophy
----------

The Right to Whisper
^^^^^^^^^^^^^^^^^^^^
LEAP fights for *the right to whisper*.

Like free speech, the right to whisper is an necessary precondition for **a free society**. Without it, civil society and political freedom become impossible. As the importance of digital communication for civic participation increases, so does the importance of the ability to digitally whisper.

Unfortunately, advances in surveillance technology are rapidly eroding the ability to whisper. This is a worldwide problem, not simply an issue for people in repressive contexts. Acceptance of poor security in the West creates a global standard of insecure practice, even among civil society actors who urgently need the ability to communicate safely.

The stakes could not be higher. Activists are dying because their communication technologies betray their identity, location, and conversations. When activists attempt to secure their communications, they face confusing software, a dearth of secure providers, and a greater risk of being flagged as potential troublemakers. In other words, problems of usability, availability, and adoption.

Our vision
^^^^^^^^^^
The LEAP vision is to attack these problems of usability, availability, and adoption head on.

To address **usability**:
        we are creating a complete system where the user-facing client software is
        tightly coupled with the cloud-base components of the system. All our software 
        will be auto-configuring, prevent users from practicing insecure behavior, and 
        primarily limit the configuration options to those moments when the user is placing i
        their trust in another entity.

To address **availability**:
        LEAP will work closely with service providers to adopt our open source, automatedl
        platform for running high-availability communication services. By lowering the 
        barriers of entry to become a reliable provider, we can increase the supply and 
        decrease the cost of secure communications.

To address **adoption**:
        the LEAP platform layers higher security on top of existing protocols to allow 
        users a gradual transition path and backward compatibility. Our goal is to create 
        services that are attractive in terms of features, usability, and price for users in
        both democratic and repressive contexts.

All contributions should have these three points in mind.

.. _`gpl3`:

GPLv3 License
--------------

.. image:: gpl.*

Bitmask is released under the terms of the `GNU GPL version 3`_ or later.

::

    Bitmask is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Bitmask is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Bitmask.  If not, see http://www.gnu.org/licenses/.

.. _`GNU GPL version 3`: http://www.gnu.org/licenses/gpl.txt

.. _`PySide`: http://qt-project.org/wiki/PySide

.. ??? include whole version?
    .. include:: ../COPYING
