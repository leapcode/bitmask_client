#!/bin/sh
# Update pip and install LEAP base/testing requirements.
# For convenience, $insecure_packages are allowed with insecure flags enabled.
# Use at your own risk.
# See $usage for help

insecure_packages="dirspec"

return_wheelhouse() {
    if [ "$WHEELHOUSE" = "" ]; then
	WHEELHOUSE=$HOME/wheelhouse
    fi

    if [ ! -d "$WHEELHOUSE" ]; then
	mkdir $WHEELHOUSE
    fi

    echo "$WHEELHOUSE"
}

show_help() {
    usage="Usage: $0 [--testing]\n --testing\tInstall dependencies from requirements-testing.pip\n
\t\tOtherwise, it will install requirements.pip"
    echo $usage

    exit 1
}

process_arguments() {
    testing=false
    while [ "$#" -gt 0 ]; do
	# From http://stackoverflow.com/a/31443098
	case "$1" in
	    --help) show_help;;
	    --testing) testing=true; shift 1;;

	    -h) show_help;;
	    -*) echo "unknown option: $1" >&2; exit 1;;
	esac
    done
}

return_insecure_flags() {
    for insecure_package in $insecure_packages; do
	flags="$flags --allow-external $insecure_package --allow-unverified $insecure_package"
    done

    echo $flags
}

return_packages() {
    if $testing ; then
	packages="-r pkg/requirements-testing.pip"
    else
	packages="-r pkg/requirements.pip"
    fi

    echo $packages
}

process_arguments $@
wheelhouse=`return_wheelhouse`
install_options="-U --find-links=$wheelhouse"
insecure_flags=`return_insecure_flags`
packages=`return_packages`

pip install -U wheel
pip install $install_options pip
pip install $install_options $insecure_flags $packages
