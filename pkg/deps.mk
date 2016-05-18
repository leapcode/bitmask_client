get_wheels:
	pip install --upgrade setuptools
	pip install --upgrade pip
	pip install wheel

gather_wheels:
	pip wheel --wheel-dir=../wheelhouse pyzmq --build-option "--zmq=bundled"
	# because fuck u1db externals, that's why...
	pip wheel --wheel-dir=../wheelhouse --allow-external dirspec --allow-unverified dirspec --allow-external u1db --allow-unverified u1db -r pkg/requirements.pip

install_wheel:
	# if it's the first time, you'll need to get_wheels first
	pip install --pre --use-wheel --no-index --find-links=../wheelhouse -r pkg/requirements.pip

gather_deps:
	pipdeptree | pkg/scripts/filter-bitmask-deps

install_base_deps:
	for repo in leap_pycommon keymanager leap_mail soledad/common soledad/client; do cd $(CURDIR)/../$$repo && pkg/pip_install_requirements.sh; done
	pkg/pip_install_requirements.sh

pull_leapdeps:
	for repo in $(LEAP_REPOS); do cd $(CURDIR)/../$$repo && git pull; done

checkout_leapdeps_develop:
	for repo in $(LEAP_REPOS); do cd $(CURDIR)/../$$repo && git checkout develop; done
	git checkout develop

