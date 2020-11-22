# pygopherd -- Gopher-based protocol server in Python
# module: Implementation of features first found in UMN gopherd
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os
import os.path

import pygopherd.fileext
from pygopherd.gopherentry import GopherEntry
from pygopherd.handlers.dir import DirHandler
from pygopherd.handlers.file import FileHandler

extstrip = None

###########################################################################
# UMN Directory handler
# Handles .Links, .names, and .cap/* files
###########################################################################


class LinkEntry(GopherEntry):
    def __init__(self, selector, config):
        super().__init__(selector, config)
        self.needsmerge = 0
        self.needsabspath = 0

    def getneedsmerge(self):
        return self.needsmerge

    def getneedsabspath(self):
        return self.needsabspath

    def setneedsmerge(self, arg):
        self.needsmerge = arg

    def setneedsabspath(self, arg):
        self.needsabspath = arg


class UMNDirHandler(DirHandler):
    """This module strives to be bug-compatible with UMN gopherd."""

    def prepare(self):
        """Override parent to do a few more things and override sort order."""
        # Initialize.
        self.linkentries = []

        # Let the parent do the directory walking for us.  Will call
        # prep_initfiles_canaddfile and prep_entriesappend.
        if DirHandler.prepare(self):
            # Returns 1 if it didn't load from the cache.
            # Merge and sort.
            self.MergeLinkFiles()
            self.fileentries.sort(key=cmp_to_key(self.entrycmp))

    def prep_initfiles_canaddfile(self, ignorepatt, pattern, file):
        """Override the parent to process dotfiles and keep them out
        of the list."""
        if DirHandler.prep_initfiles_canaddfile(self, ignorepatt, pattern, file):
            # If the parent says it's OK, then let's see if it's
            # a link file.  If yes, process it and return false.
            if file[0] == ".":
                if not self.vfs.isdir(self.selectorbase + "/" + file):
                    self.linkentries.extend(
                        self.processLinkFile(self.selectorbase + "/" + file)
                    )
                    return 0
                else:
                    return 0  # A "dot dir" -- ignore.
            return 1  # Not a dot file -- return true
        else:
            return 0  # Parent returned 0, do the same.

    def prep_entriesappend(self, file, handler, fileentry):
        """Overridden to process .cap files and modify extensions.
        This is called by the
        parent's prepare to append an entry to the list.  Here, we check
        to see if there's a .cap file right before adding it."""

        global extstrip
        if extstrip is None:
            extstrip = self.config.get("handlers.UMN.UMNDirHandler", "extstrip")
        if extstrip != "none" and isinstance(handler, FileHandler):
            if extstrip == "full" or (
                extstrip == "nonencoded" and not fileentry.getencoding()
            ):
                # If it's a file, has a MIME type, and we know about it..
                fileentry.setname(
                    pygopherd.fileext.extstrip(
                        file, fileentry.getencodedmimetype() or fileentry.getmimetype()
                    )
                )

        capfilename = self.selectorbase + "/.cap/" + file

        try:
            capinfo = self.processLinkFile(capfilename, fileentry.getselector())
            if len(capinfo) >= 1:  # We handle one and only one entry.
                if capinfo[0].gettype() == "X" or capinfo[0].gettype() == "-":
                    return  # Type X -- don't append.
                else:
                    self.mergeentries(fileentry, capinfo[0])
        except IOError:  # Ignore no capfile situation
            pass
        DirHandler.prep_entriesappend(self, file, handler, fileentry)

    def MergeLinkFiles(self):
        """Called to merge the files from .Links and .names into the
        objects obtained by walking the directory.  According to UMN code,
        we ONLY merge if the Path starts with ./ or ~/ in the file.  This
        is set in the getneedsmerge() attribute.  If that attribute is
        not set, don't even bother with it -- just add."""

        # For faster matching, make a dictionary out of the list.

        fileentriesdict = {}
        for entry in self.fileentries:
            fileentriesdict[entry.selector] = entry

        for linkentry in self.linkentries:
            if not linkentry.getneedsmerge():
                self.fileentries.append(linkentry)
                continue
            if linkentry.selector in fileentriesdict:
                if linkentry.gettype() == "X":
                    # It's special code to hide something.
                    self.fileentries.remove(fileentriesdict[linkentry.selector])
                else:
                    self.mergeentries(fileentriesdict[linkentry.selector], linkentry)
            else:
                self.fileentries.append(linkentry)

    def mergeentries(self, old, new):
        """Takes the set fields from new and modifies old to have their
        value."""
        for field in ["selector", "type", "name", "host", "port"]:
            if getattr(new, field):
                setattr(old, field, getattr(new, field))

        for field in list(new.geteadict().keys()):
            old.setea(field, new.getea(field))

    def processLinkFile(self, filename, capfilepath=None):
        """Processes a link file.  If capfilepath is set, it should
        be the equivolent of the Path= in a .names file."""
        linkentries = []
        with self.vfs.open(filename, "r") as fd:
            while 1:
                nextstep, entry = self.getLinkItem(fd, capfilepath)
                if entry:
                    linkentries.append(entry)
                if nextstep == "stop":
                    break
        return linkentries

    def getLinkItem(self, fd, capfilepath=None):
        """This is an almost exact clone of UMN's GSfromLink function."""
        entry = LinkEntry(self.entry.selector, self.config)
        nextstep = "continue"

        done = {"path": 0, "type": 0, "name": 0, "host": 0, "port": 0}

        if capfilepath is not None:
            entry.setselector(capfilepath)
            done["path"] = 1

        while 1:
            line = fd.readline()
            if not line:
                nextstep = "stop"
                break
            line = line.strip()

            # Empty.
            if len(line) == 0:
                break

            # Comment.
            if line[0] == "#":
                if done["path"]:
                    break
                else:
                    continue

            # Type.
            if line[0:5] == "Type=":
                entry.settype(line[5])
                # FIXME: handle if line[6] is + or ?
                done["type"] = 1
            elif line[0:5] == "Name=":
                entry.setname(line[5:])
                done["name"] = 1
            elif line[0:5] == "Path=":
                pathname = line[5:]
                if len(pathname) and pathname[-1] == "/":
                    pathname = pathname[0:-1]
                if len(line) >= 7 and (line[5:7] == "./" or line[5:7] == "~/"):
                    # Handle ./: make full path.
                    entry.setselector(self.selectorbase + "/" + pathname[2:])
                    entry.setneedsmerge(1)
                elif len(pathname) and pathname[0] != "/" and pathname[0:4] != "URL:":
                    entry.setselector(pathname)
                    entry.setneedsabspath(1)
                else:
                    entry.setselector(pathname)
                done["path"] = 1
            elif line[0:5] == "Host=":
                if line[5:] != "+":
                    entry.sethost(line[5:])
                done["host"] = 1
            elif line[0:5] == "Port=":
                if line[5:] != "+":
                    entry.setport(int(line[5:]))
                done["port"] = 1
            elif line[0:5] == "Numb=":
                try:  # Don't crash if we can't parse the number
                    entry.setnum(int(line[5:]))
                except:
                    pass
            elif line[0:9] == "Abstract=":
                abstractstr = ""
                abstractline = line[9:]
                while len(abstractline) and abstractline[-1] == "\\":
                    abstractstr += abstractline[0:-1] + "\n"
                    abstractline = fd.readline().strip()
                abstractstr += abstractline

                if abstractstr:
                    entry.setea("ABSTRACT", abstractstr)
            elif line[0:6] == "Admin=" or line[0:4] == "URL=" or line[0:4] == "TTL=":
                pass
            else:
                break
            ### FIXME: Handle Admin, URL, TTL

        if done["path"]:
            if (
                entry.getneedsabspath()
                and entry.gethost() is None
                and entry.getport() is None
            ):
                entry.setselector(
                    os.path.normpath(self.selectorbase + "/" + entry.getselector())
                )
            return nextstep, entry
        return nextstep, None

    def sgn(self, a):
        """Returns -1 if less than 0, 1 if greater than 0, and 0 if
        equal to zero."""
        if a == 0:
            return 0
        if a < 0:
            return -1
        return 1

    def entrycmp(self, entry1, entry2):
        """This function implements an exact replica of UMN behavior
        GSqsortcmp() behavior."""
        if entry1.name is None:
            return 1
        if entry2.name is None:
            return -1
        e1num = entry1.getnum(0)
        e2num = entry2.getnum(0)

        # Equal numbers or no numbers: sort by title.
        if e1num == e2num:
            return cmp(entry1.name, entry2.name)

        # Same signs: use plain numeric comparison.
        if self.sgn(e1num) == self.sgn(e2num):
            return cmp(e1num, e2num)

        # Different signs: other comparison.
        if e1num > e2num:
            return -1
        else:
            return 1


# For Python 3 compat
# https://docs.python.org/3.0/whatsnew/3.0.html#ordering-comparisons
def cmp(a, b):
    return (a > b) - (a < b)


# Python 3 conversion tool: from http://code.activestate.com/recipes/576653-convert-a-cmp-function-to-a-key-function/
def cmp_to_key(mycmp):
    """Convert a cmp= function into a key= function"""

    class K(object):
        def __init__(self, obj, *_):
            self.obj = obj

        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0

        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0

        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0

        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0

        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0

        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0

    return K
