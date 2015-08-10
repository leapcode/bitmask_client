#!/usr/local/bin python
# -*- coding: utf-8 -*-
# apply_updates.py
# Copyright (C) 2015 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Apply downloaded updates to the bundle
"""

import os
import os.path
import shutil
import tuf.client.updater


REPO_DIR = "repo/"
UPDATES_DIR = "updates/"


def update_if_needed():
    if not os.path.isdir(UPDATES_DIR):
        print "No updates found"
        return

    print "Found updates, merging directories before doing anything..."
    try:
        remove_obsolete()
        merge_directories(UPDATES_DIR, ".")
        shutil.rmtree(UPDATES_DIR)
    except Exception as e:
        print "An error has ocurred while updating: " + e.message


def remove_obsolete():
    tuf.conf.repository_directory = REPO_DIR
    updater = tuf.client.updater.Updater('leap-updater', {})
    updater.remove_obsolete_targets(".")


def merge_directories(src, dest):
    for root, dirs, files in os.walk(src):
        if not os.path.exists(root):
            # It was moved as the dir din't exist in dest
            continue

        destroot = os.path.join(dest, root[len(src):])

        for f in files:
            srcpath = os.path.join(root, f)
            destpath = os.path.join(destroot, f)
            if os.path.exists(destpath):
                # FIXME: On windows we can't remove, but we can rename and
                #        afterwards remove. is that still true with python?
                #        or was just something specific of our implementation
                #        with C++?
                os.remove(destpath)
            os.rename(srcpath, destpath)

        for d in dirs:
            srcpath = os.path.join(root, d)
            destpath = os.path.join(destroot, d)

            if os.path.exists(destpath) and not os.path.isdir(destpath):
                os.remove(destpath)

            if not os.path.exists(destpath):
                os.rename(srcpath, destpath)


if __name__ == "__main__":
    update_if_needed()
