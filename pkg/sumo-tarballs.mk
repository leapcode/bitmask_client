checkout_leapdeps_release:
	pkg/scripts/checkout_leap_versions.sh

setup_without_namespace:
	awk '!/namespace_packages*/' setup.py > file && mv file setup.py

sumo_tarball_release: checkout_leapdeps_release setup_without_namespace
	python setup.py sdist --sumo
	git checkout -- src/leap/__init__.py
	git checkout -- src/leap/bitmask/_version.py
	rm -rf src/leap/soledad
	git checkout -- setup.py

# XXX We need two sets of sumo-tarballs: the one published for a release
# (that will pick the pinned leap deps), and the other which will be used
# for the nightly builds.
# TODO change naming scheme for sumo-latest: should include date (in case
# bitmask is not updated bu the dependencies are)

sumo_tarball_latest: checkout_leapdeps_develop pull_leapdeps setup_without_namespace
	python setup.py sdist --sumo   # --latest
	git checkout -- src/leap/__init__.py
	git checkout -- src/leap/bitmask/_version.py
	rm -rf src/leap/soledad
	git checkout -- setup.py
