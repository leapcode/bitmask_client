#!/bin/sh
cat pkg/leap_versions.txt | while read line
do
	package=$(echo $line | cut -f1 -d' ')
	tag=$(echo $line | cut -f2 -d' ')
	cd ../$package && git checkout $tag
done
