#!/bin/bash
# Update pip and install LEAP base/testing requirements.
# For convenience, $insecure_packages are allowed with insecure flags enabled.
# Use at your own risk.
# See $usage for help

insecure_packages="dirspec"
leap_wheelhouse=https://lizard.leap.se/wheels

show_help() {
    usage="Usage: $0 [--testing] [--use-leap-wheels]\n --testing\t\tInstall dependencies from requirements-testing.pip\n
\t\t\tOtherwise, it will install requirements.pip\n
--use-leap-wheels\tUse wheels from leap.se"
    echo -e $usage

    exit 1
}

process_arguments() {
    testing=false
    use_leap_wheels=false

    while [ "$#" -gt 0 ]; do
	# From http://stackoverflow.com/a/31443098
	case "$1" in
	    --help) show_help;;
	    --testing) testing=true; shift 1;;
	    --use-leap-wheels) use_leap_wheels=true; shift 1;;

	    -h) show_help;;
	    -*) echo "unknown option: $1" >&2; exit 1;;
	esac
    done
}

return_wheelhouse() {
    if $use_leap_wheels ; then
	WHEELHOUSE=$leap_wheelhouse
    elif [ "$WHEELHOUSE" = "" ]; then
	WHEELHOUSE=$HOME/wheelhouse
    fi

    # Tested with bash and zsh
    if [[ $WHEELHOUSE != http* && ! -d "$WHEELHOUSE" ]]; then
	    mkdir $WHEELHOUSE
    fi

    echo "$WHEELHOUSE"
}

return_install_options() {
    wheelhouse=`return_wheelhouse`
    install_options="-U --find-links=$wheelhouse"
    if $use_leap_wheels ; then
	install_options="$install_options --trusted-host lizard.leap.se"
    fi

    echo $install_options
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
install_options=`return_install_options`
insecure_flags=`return_insecure_flags`
packages=`return_packages`

pip install -U wheel
pip install $install_options pip
pip install $install_options $insecure_flags $packages
