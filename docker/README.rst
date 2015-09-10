Bitmask and Docker
==================

Here we have several tools that leverages docker to ease Bitmask testing.

``bitmask-docker.sh`` is a helper script to ``build`` and ``run`` the bitmask app,
here is an example usage::

    $ ./bitmask-docker build  # build docker image
    $ ./bitmask-docker init ro bitmask-nightly.json  # initialize all the stuff needed
    # ....
    $ ./bitmask-docker.sh run


``bitmask-nightly.json`` is the version specifier for each bitmask component that
will be used to run bitmask.

``Dockerfile`` is the file used to build the docker image that will run bitmask.

``leap_bootstrap.sh`` is the script that takes care of cloning repos, installing
python dependencies, running bitmask, etc.


debian/
-------

``apt-bitmask.sh`` script that installs bitmask from the debian packages.

``bitmask-on-docker.sh`` installs bitmask and runs it in a dummy X server,
waits a little and takes a screenshot.

``leap-experimental.key`` is needed by ``apt-bitmask.sh`` to ``apt-key add``
and verify apt sources.

``run-docker-for-bitmask.sh`` is a helper script that runs an ubuntu/debian
container ready to run the ``apt-bitmask.sh`` command, it does (among other
stuff) X11 forwarding to display Bitmask UI on the host linux.

An example usage::

    $ ./run-docker-for-bitmask.sh
    non-network local connections being added to access control list
    root@hostname:/# cd /host/
    root@hostname:/host# ./apt-bitmask.sh unstable
    # [... not so relevant output ...]
    root@hostname:/host# apt-get install -y lxpolkit  # install a small polkit agent
    # [... not so relevant output ...]
    root@hostname:/host# lxpolkit &  # run the polkit agent in the background, ignore the "No session for pid 6034" error.
    root@hostname:/host# bitmask -d  # tadaa, you have bitmask running in a container!
