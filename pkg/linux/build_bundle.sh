#!/bin/bash
#
# USAGE NOTES:
#
# This script is meant to be used as follows:
#   user@host ~ $ ./build_bundle.sh ~/tmp 0.3.2 ~/tmp/0.3.1/Bitmask-linux64-0.3.1/ /media/Shared/CHANGELOG ~/tmp/bundle_out/
#
# So we would have:
#    REPOS_ROOT      -> ~/tmp
#    VERSION         -> 0.3.2
#    TEMPLATE_BUNDLE -> ~/tmp/0.3.1/Bitmask-linux64-0.3.1/
#    JOINT_CHANGELOG -> /media/Shared/CHANGELOG
#    DEST            -> ~/tmp/bundle_out/
#
# We need to set different PATHs in order to use a specific version of PySide,
# supposing that we have our compiled pyside in '~/pyside/sandbox', the above command would be:
#   user@host ~ $ PYTHONPATH=~/pyside/sandbox/lib/python2.7/site-packages/ LD_LIBRARY_PATH=~/pyside/sandbox/lib/ PATH=$PATH:~/pyside/sandbox/bin/ ./build_bundle.sh ~/tmp 0.3.2 ~/tmp/0.3.1/Bitmask-linux64-0.3.1/ /media/sf_Shared/CHANGELOG ~/tmp/bundle_out/


# Required arguments
REPOS_ROOT=$1       # Root path for all the needed repositories
VERSION=$2          # Version number that we are building
TEMPLATE_BUNDLE=$3  # A template used to create the new bundle
JOINT_CHANGELOG=$4  # Joint changelog for all the repositories
DEST=$5             # Destination folder for the bundle

# Helper variables
REPOSITORIES="bitmask_client leap_pycommon soledad keymanager leap_mail"
ARCH=$(uname -m | sed 's/x86_//;s/i[3-6]86/32/')

# Bundle structure
LEAP_LIB=$TEMPLATE_BUNDLE/lib/leap/
BITMASK_BIN=$TEMPLATE_BUNDLE/bitmask
BUNDLE_NAME=Bitmask-linux$ARCH-$VERSION

# clean template
rm $TEMPLATE_BUNDLE/CHANGELOG
rm $TEMPLATE_BUNDLE/relnotes.txt
rm -rf $TEMPLATE_BUNDLE/apps/leap
rm -rf $TEMPLATE_BUNDLE/lib/leap/{common,keymanager,soledad,mail}

# checkout the latest tag in all repos
for repo in $REPOSITORIES; do
    cd $REPOS_ROOT/$repo
    git fetch
    # checkout to the latest annotated tag, supress 'detached head' warning
    git checkout --quiet `git describe --abbrev=0`
done

# make: compile ui and resources in client
cd $REPOS_ROOT/bitmask_client
make

# copy the latest client code to the template
cp -r $REPOS_ROOT/bitmask_client/src/leap $TEMPLATE_BUNDLE/apps/leap

# setup sdist client
cd $REPOS_ROOT/bitmask_client
python setup.py sdist

# extract $VERSION and copy _version.py to TEMPLATE_BUNDLE/Bitmask.app/Contents/MacOS/apps/leap/bitmask/_version.py
# copy _version.py (versioneer) and reqs.txt (requirements) to the bundle template
cd dist
rm -rf leap.bitmask-$VERSION
tar xzf leap.bitmask-$VERSION.tar.gz
cp leap.bitmask-$VERSION/src/leap/bitmask/_version.py $TEMPLATE_BUNDLE/apps/leap/bitmask/_version.py
cp leap.bitmask-$VERSION/src/leap/bitmask/util/reqs.txt $TEMPLATE_BUNDLE/apps/leap/bitmask/util/reqs.txt

# add the other needed projects to $LEAP_LIB
# e.g. TEMPLATE_BUNDLE/Bitmask.app/Contents/MacOS/lib/leap/
cp -r $REPOS_ROOT/leap_pycommon/src/leap/common $LEAP_LIB
cp -r $REPOS_ROOT/soledad/common/src/leap/soledad $LEAP_LIB
cp -r $REPOS_ROOT/soledad/client/src/leap/soledad/client $LEAP_LIB/soledad
cp -r $REPOS_ROOT/leap_mail/src/leap/mail $LEAP_LIB
cp -r $REPOS_ROOT/keymanager/src/leap/keymanager $LEAP_LIB

# copy bitmask launcher to the bundle template 
# e.g. TEMPLATE_BUNDLE/Bitmask.app/Contents/MacOS/Bitmask
cd $REPOS_ROOT/bitmask_launcher/build/
make
cp src/launcher $BITMASK_BIN

# copy launcher.py to template bundle
# e.g. TEMPLATE_BUNDLE/Bitmask.app/Contents/MacOS/apps/
cd $REPOS_ROOT/bitmask_client_launcher/src/
cp launcher.py $TEMPLATE_BUNDLE/apps/

# copy relnotes, joint changelog and LICENSE to TEMPLATE_BUNDLE
cp $REPOS_ROOT/bitmask_client/relnotes.txt $TEMPLATE_BUNDLE
cp $JOINT_CHANGELOG $TEMPLATE_BUNDLE/CHANGELOG
cp $REPOS_ROOT/bitmask_client/LICENSE $TEMPLATE_BUNDLE/LICENSE

# clean *.pyc files
cd $TEMPLATE_BUNDLE
find . -name "*.pyc" -delete

# remove execution flags (because vbox fs) and set read permissions for all
chmod 644 CHANGELOG LICENSE README

# create tarball
TMP=/tmp/$BUNDLE_NAME

rm -rf $TMP && mkdir -p $TMP  # clean temp dir
cp -R $TEMPLATE_BUNDLE/* $TMP
cd /tmp
tar cjf $DEST/$BUNDLE_NAME.tar.bz2 $BUNDLE_NAME
cd
rm -rf $TMP

# go back to develop in all repos
for repo in $REPOSITORIES; do
    cd $REPOS_ROOT/$repo
    git checkout develop
done
