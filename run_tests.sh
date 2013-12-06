#!/bin/bash

set -e

function usage {
  echo "Usage: $0 [OPTION]...[@virtualenv-name]"
  echo "Run leap-client test suite"
  echo ""
  echo "  -V, --virtual-env        Always use virtualenv.  Install automatically if not present"
  echo "  -N, --no-virtual-env     Don't use virtualenv.  Run tests in local environment"
  echo "  -s, --no-site-packages   Isolate the virtualenv from the global Python environment"
  echo "  -x, --stop               Stop running tests after the first error or failure."
  echo "  -f, --force              Force a clean re-build of the virtual environment. Useful when dependencies have been added."
  echo "  -p, --pep8               Just run pep8"
  echo "  -P, --no-pep8            Don't run pep8"
  echo "  -c, --coverage           Generate coverage report"
  echo "  -h, --help               Print this usage message"
  echo "  -A, --all		   Run all tests, without excluding any"
  echo "  -i, --progressive	   Run with nose-progressive plugin"
  echo "  --hide-elapsed           Don't print the elapsed time for each test along with slow test list"
  echo ""
  echo "Note: with no options specified, the script will try to run the tests in a virtual environment,"
  echo "      If no virtualenv is found, the script will ask if you would like to create one.  If you "
  echo "      prefer to run tests NOT in a virtual environment, simply pass the -N option."
  echo "      If you pass @virtualenv-name, the given virtualenv will be used as long as "
  echo "      virtualenvwrapper.sh can be found in the PATH."
  exit
}

function process_option {
  case "$1" in
    -h|--help) usage;;
    -V|--virtual-env) always_venv=1; never_venv=0;;
    -N|--no-virtual-env) always_venv=0; never_venv=1;;
    -s|--no-site-packages) no_site_packages=1;;
    -f|--force) force=1;;
    -p|--pep8) just_pep8=1;;
    -P|--no-pep8) no_pep8=1;;
    -c|--coverage) coverage=1;;
    -A|--all) alltests=1;;
    -i|--progressive) progressive=1;;
    @*) venvwrapper=1; source_venv=`echo $1 | cut -c 2-`;;
    -*) noseopts="$noseopts $1";;
    *) noseargs="$noseargs $1"
  esac
}

venv=.venv
with_venv=pkg/tools/with_venv.sh
with_venvwrapper=pkg/tools/with_venvwrapper.sh
always_venv=0
never_venv=0
force=0
no_site_packages=0
installvenvopts=
noseargs=
noseopts=
venvwrapper=0
source_venv=
wrapper=""
just_pep8=0
no_pep8=0
coverage=0
alltests=0
progressive=0

for arg in "$@"; do
  process_option $arg
done

# If enabled, tell nose to collect coverage data
if [ $coverage -eq 1 ]; then
    noseopts="$noseopts --with-coverage --cover-package=leap --cover-html --cover-html-dir=docs/covhtml/ --cover-erase"
fi

if [ $no_site_packages -eq 1 ]; then
  installvenvopts="--no-site-packages"
fi

# If alltests flag is not set, let's exclude some dirs that are troublesome.
if [ $alltests -eq 0 ]; then
  echo "[+] Running ALL tests..."
  #noseopts="$noseopts --exclude-dir=leap/soledad"
fi

# If progressive flag enabled, run with this nice plugin :)
if [ $progressive -eq 1 ]; then
    noseopts="$noseopts --with-progressive"
fi

function run_tests {
  echo "running tests..."

  if [ $venvwrapper -eq 1 ]; then
	  VIRTUAL_ENV=$WORKON_HOME/$source_venv
	  wrapper="$with_venvwrapper $source_venv"

  fi

  #NOSETESTS="nosetests leap --exclude=soledad* $noseopts $noseargs"
  NOSETESTS="$VIRTUAL_ENV/bin/nosetests . $noseopts $noseargs"
  #--with-coverage --cover-package=leap"

  # Just run the test suites in current environment
  echo "NOSETESTS=$NOSETESTS"
  ${wrapper} $NOSETESTS
  # If we get some short import error right away, print the error log directly
  RESULT=$?
  return $RESULT
}

function run_pep8 {
  echo "Running pep8 ..."
  srcfiles="src/leap"
  # Just run PEP8 in current environment
  pep8_opts="--ignore=E202,W602 --exclude=*_rc.py,ui_*,_version.py --repeat"

  ${wrapper} pep8 ${pep8_opts} ${srcfiles}
}

# XXX we cannot run tests that need X server
# in the current debhelper build process,
# so I exclude the topmost tests


if [ $never_venv -eq 0 ]
then
  # Remove the virtual environment if --force used
  if [ $force -eq 1 ]; then
    echo "Cleaning virtualenv..."
    rm -rf ${venv}
  fi
  if [ -e ${venv} ]; then
    wrapper="${with_venv}"
  else
    if [ $always_venv -eq 1 ]; then
      # Automatically install the virtualenv
      python pkg/install_venv.py $installvenvopts
      wrapper="${with_venv}"
    else
      echo -e "No virtual environment found...create one? (Y/n) \c"
      read use_ve
      if [ "x$use_ve" = "xY" -o "x$use_ve" = "x" -o "x$use_ve" = "xy" ]; then
        # Install the virtualenv and run the test suite in it
        python pkg/install_venv.py $installvenvopts
        wrapper=${with_venv}
      fi
    fi
  fi
fi

# Delete old coverage data from previous runs
if [ $coverage -eq 1 ]; then
    ${wrapper} coverage erase
fi

if [ $just_pep8 -eq 1 ]; then
    run_pep8
    exit
fi

run_tests

if [ -z "$noseargs" ]; then
  if [ $no_pep8 -eq 0 ]; then
    run_pep8
  fi
fi

if [ $coverage -eq 1 ]; then
    echo "Generating coverage report in docs/covhtml/"
    echo "now point your browser at docs/covhtml/index.html"
    exit
fi
