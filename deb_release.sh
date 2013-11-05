#!/bin/zsh

VERSION_FILE="src/leap/bitmask/_version.py"
rm ${VERSION_FILE}
python setup.py freeze_debianver
sed -i 's/-dirty//g' ${VERSION_FILE}
git add ${VERSION_FILE}
git ci -m "freeze debian version"	
