"""
utils to help in the setup process
"""
import os
import re
import sys


# gets reqs from the first matching file
def get_reqs_from_files(reqfiles):
    for reqfile in reqfiles:
        if os.path.isfile(reqfile):
            return open(reqfile, 'r').read().split('\n')


def parse_requirements(reqfiles=['requirements.txt',
                                 'requirements.pip',
                                 'pkg/requirements.pip']):
    requirements = []
    for line in get_reqs_from_files(reqfiles):
        # -e git://foo.bar/baz/master#egg=foobar
        if re.match(r'\s*-e\s+', line):
            requirements.append(re.sub(r'\s*-e\s+.*#egg=(.*)$', r'\1',
                                line))
        # http://foo.bar/baz/foobar/zipball/master#egg=foobar
        elif re.match(r'\s*https?:', line):
            requirements.append(re.sub(r'\s*https?:.*#egg=(.*)$', r'\1',
                                line))
        # -f lines are for index locations, and don't get used here
        elif re.match(r'\s*-f\s+', line):
            pass

        # argparse is part of the standard library starting with 2.7
        # adding it to the requirements list screws distro installs
        elif line == 'argparse' and sys.version_info >= (2, 7):
            pass
        else:
            if line != '':
                requirements.append(line)

    #print 'REQUIREMENTS', requirements
    return requirements
