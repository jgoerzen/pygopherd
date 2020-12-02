# pygopherd -- Gopher-based protocol server in Python
# module: regular directory handling
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

import pickle
import re
import stat
import time
import typing

from pygopherd import gopherentry, handlers
from pygopherd.handlers import base


class DirHandler(base.BaseHandler):
    cachetime: int
    cachefile: str

    def canhandlerequest(self) -> bool:
        """We can handle the request if it's for a directory."""
        return self.statresult and stat.S_ISDIR(self.statresult[stat.ST_MODE])

    def getentry(self) -> gopherentry.GopherEntry:
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            self.entry.populatefromfs(self.getselector(), self.statresult, vfs=self.vfs)
        return self.entry

    def prep_initfiles(self) -> None:
        """Initialize the list of files.  Ignore the files we're suppoed to."""
        self.files = []
        dirfiles = self.vfs.listdir(self.getselector())
        ignorepatt = self.config.get("handlers.dir.DirHandler", "ignorepatt")
        for file in dirfiles:
            if self.prep_initfiles_canaddfile(
                ignorepatt, self.selectorbase + "/" + file, file
            ):
                self.files.append(file)

    def prep_initfiles_canaddfile(
        self, ignorepatt: str, pattern: str, file: str
    ) -> bool:
        return not re.search(ignorepatt, pattern)

    def prep_entries(self) -> None:
        """Generate entries from the list."""

        self.fileentries = []
        for file in self.files:
            # We look up the appropriate handler for this object, and ask
            # it to give us an entry object.
            handler = handlers.HandlerMultiplexer.getHandler(
                self.selectorbase + "/" + file,
                self.searchrequest,
                self.protocol,
                self.config,
                vfs=self.vfs,
            )
            fileentry = handler.getentry()
            self.prep_entriesappend(file, handler, fileentry)

    def prep_entriesappend(
        self, file: str, handler: base.BaseHandler, fileentry: gopherentry.GopherEntry
    ):
        """Subclasses can override to do post-processing on the entry while
        we still have the filename around.
        IE, for .cap files."""
        self.fileentries.append(fileentry)

    def prepare(self) -> bool:
        # Initialize some variables.

        self.selectorbase = self.selector
        if self.selectorbase == "/":
            self.selectorbase = ""  # Avoid dup slashes

        if self.loadcache():
            # No need to do anything else.
            return False  # Did nothing.

        self.prep_initfiles()

        # Sort the list.
        self.files.sort()

        self.prep_entries()
        return True  # Did something.

    def isdir(self) -> bool:
        return True

    def getdirlist(self):
        self.savecache()
        return self.fileentries

    def loadcache(self) -> bool:

        self.fromcache = 0
        if not hasattr(self, "cachetime"):
            self.cachetime = self.config.getint("handlers.dir.DirHandler", "cachetime")
            self.cachefile = self.config.get("handlers.dir.DirHandler", "cachefile")
        cachename = self.selector + "/" + self.cachefile
        if not self.vfs.iswritable(cachename):
            return False

        try:
            statval = self.vfs.stat(cachename)
        except OSError:
            return False

        if time.time() - statval[stat.ST_MTIME] < self.cachetime:
            with self.vfs.open(cachename, "rb") as fp:
                self.fileentries = pickle.load(fp)
            self.fromcache = 1
            return True
        return False

    def savecache(self) -> None:
        if self.fromcache:
            # Don't resave the cache.
            return
        if not self.vfs.iswritable(self.selector + "/" + self.cachefile):
            return
        try:
            with self.vfs.open(self.selector + "/" + self.cachefile, "wb") as fp:
                pickle.dump(self.fileentries, fp, 1)
        except IOError:
            pass
