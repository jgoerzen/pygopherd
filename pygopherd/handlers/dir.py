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
import os
import pickle
import re
import stat
import time
import unittest

from pygopherd import gopherentry, handlers
from pygopherd.handlers.base import BaseHandler, VFS_Real


class DirHandler(BaseHandler):
    cachetime: int
    cachefile: str
    cachename: str
    fromcache: bool

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
        self, file: str, handler: BaseHandler, fileentry: gopherentry.GopherEntry
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
        self.fromcache = False
        if not hasattr(self, "cachetime"):
            self.cachetime = self.config.getint("handlers.dir.DirHandler", "cachetime")
            self.cachefile = self.config.get("handlers.dir.DirHandler", "cachefile")
            self.cachename = self.selector + "/" + self.cachefile

        if not self.vfs.iswritable(self.cachename):
            return False

        try:
            statval = self.vfs.stat(self.cachename)
        except OSError:
            return False

        if time.time() - statval[stat.ST_MTIME] < self.cachetime:
            with self.vfs.open(self.cachename, "rb") as fp:
                self.fileentries = pickle.load(fp)
            self.fromcache = True
            return True
        return False

    def savecache(self) -> None:
        if self.fromcache:
            # Don't resave the cache.
            return
        if not self.vfs.iswritable(self.cachename):
            return
        try:
            with self.vfs.open(self.cachename, "wb") as fp:
                pickle.dump(self.fileentries, fp, 1)
        except IOError:
            pass


class TestDirHandler(unittest.TestCase):
    def setUp(self) -> None:
        from pygopherd import testutil

        self.config = testutil.getconfig()
        self.vfs = VFS_Real(self.config)
        self.selector = "/"
        self.protocol = testutil.gettestingprotocol(self.selector, config=self.config)
        self.stat_result = self.vfs.stat(self.selector)

        # Make sure there's no directory cache file from a previous test run
        cachefile = self.config.get("handlers.dir.DirHandler", "cachefile")
        try:
            os.remove(self.vfs.getfspath(self.selector) + "/" + cachefile)
        except OSError:
            pass

    def test_dir_handler(self):
        handler = DirHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )

        self.assertTrue(handler.canhandlerequest())
        self.assertTrue(handler.isdir())

        handler.prepare()
        self.assertFalse(handler.fromcache)

        entry = handler.getentry()
        self.assertEqual(entry.mimetype, "application/gopher-menu")
        self.assertEqual(entry.type, "1")

        entries = handler.getdirlist()
        self.assertTrue(entries)

        # Create a second handler to test that it will load from the cached
        # file that the first handler should have created
        handler = DirHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )

        handler.prepare()
        self.assertTrue(handler.fromcache)

        cached_entries = handler.getdirlist()
        for a, b in zip(entries, cached_entries):
            self.assertEqual(a.selector, b.selector)
