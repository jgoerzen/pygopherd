import pickle
import re
import stat
import time
import typing

from pygopherd import gopherentry, handlers
from pygopherd.handlers.base import BaseHandler


class DirHandler(BaseHandler):
    cachetime: int
    cachefile: str
    cachename: str
    fromcache: bool
    files: typing.List[str]
    fileentries: typing.List[gopherentry.GopherEntry]
    selectorbase: str

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
