# pygopherd -- Gopher-based protocol server in Python
# module: Generic gopher entry object
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

import socketserver
import re
import os, stat, os.path, mimetypes, urllib.request, urllib.parse, urllib.error

mapping = None
eaexts = None


class GopherEntry:
    """The entry object for Gopher.  It holds information about each
    Gopher object."""

    def __init__(self, selector, config):
        """Initialize object based on a selector and config."""
        self.selector = selector  # Gopher path to file
        self.config = config  # Our config object
        self.fspath = None  # Path to the obj in filesystem
        self.type = None  # Gopher0 type char
        self.name = None  # Menu name
        self.host = None  # Hostname
        self.port = None  # Port number (an int)
        self.mimetype = None  # MIME type
        self.encodedmimetype = None  # Real MIME type if encoded.
        self.size = None  # Size
        self.encoding = None  # Encoding type
        self.populated = 0  # Whether or not it's been populated
        self.language = None  # Language
        self.ctime = None  # Creation date
        self.mtime = None  # Modification date
        self.num = 0  # Number in menu
        self.gopherpsupport = 0  # Supports gopher+
        self.ea = {}  # Extended attributes -- Gopher+
        # Abstract, etc.

    def populatefromvfs(self, vfs, selector):
        self.populatefromfs(selector, statval=vfs.stat(selector), vfs=vfs)

    def populatefromfs(self, fspath, statval=None, vfs=None):
        """Fills in self with data gleaned from the filesystem.

        The argument fspath specifies where in the filesystem it will search.
        statval, if present, will be used instead of calling stat() itself
        so as to cut down on the number of system calls.

        The overall idea of this function is to set only those values that
        are not already set and to do so only if a definitive answer for
        them can be obtained from the operating system.  The rest of this
        information describes the details of how it does this.

        If populatefromfs has already been called or self.populated is true,
        this function will note the fspath and the return without modifying
        anything else.

        If either gethost() or getport() return anything other than None,
        the same thing will happen.

        If there is no statval and os.stat returns an error, again,
        the same thing will happen.

        Assuming these tests pass, then:

        self.gopherpsupport will be set to true for any file or directory.

        The remaining values will be set only if they are not set already:

        For both files and directories, the creation and modification times
        will be noted, the name will be set to the filename (as returned
        by os.path.basename on the selector).

        For directories only, the type will be set to 1 and the mimetype to
        application/gopher-menu.  Gopher+ protocols may wish to
        indicate application/gopher+-menu is available as well, but that
        is outside the scope of this function.

        For files only, the size will be noted.  An attempt will be made
        to ascertain a mimetype and an encoding.  If only a mimetype is
        found, it will be noted in self.mimetype.  If both a mimetype
        and an encoding is found, self.mimetype will be
        application/octet-stream, self.encoding will note the encoding,
        and self.encodedmimetype will note the type of the encoded data.
        If no mimetype can be found, it will be set to the default
        from the config file.  If no gopher0 type character is already present,
        self.guesstype() will be called to set it."""

        self.fspath = fspath
        if vfs is None:
            from pygopherd.handlers.base import VFS_Real

            vfs = VFS_Real(self.config)

        if self.populated:
            return

        # Just let the stat catch the OSError rather than testing
        # for existance here.  Help cut down on the number of syscalls.

        if not (self.gethost() is None and self.getport() is None):
            return

        if not statval:
            try:
                statval = vfs.stat(self.fspath)
            except OSError:
                return

        self.populated = 1
        self.gopherpsupport = 1  # Indicate gopher+ support for locals.

        # All this "or" stuff means that we only modify it if it's not already
        # set.

        self.ctime = self.ctime or statval[9]
        self.mtime = self.mtime or statval[8]
        self.name = self.name or os.path.basename(self.selector)

        if stat.S_ISDIR(statval[0]):
            self.type = self.type or "1"
            self.mimetype = self.mimetype or "application/gopher-menu"
            self.handleeaext(self.fspath + "/", vfs)  # Add the / so we get /.abs
            return

        self.handleeaext(self.fspath, vfs)

        self.size = self.size or statval[6]

        mimetype, encoding = mimetypes.guess_type(self.selector, strict=False)

        if encoding:
            self.mimetype = self.mimetype or "application/octet-stream"
            self.encoding = self.encoding or encoding
            self.encodedmimetype = self.encodedmimetype or mimetype
        else:
            self.mimetype = self.mimetype or mimetype

        # Did we get no mime type at all?  Fall back to a default.

        if not self.mimetype:
            self.mimetype = self.config.get("GopherEntry", "defaultmimetype")

        self.type = self.type or self.guesstype()

    def guesstype(self):
        global mapping
        if not mapping:
            mapping = eval(self.config.get("GopherEntry", "mapping"))
        for maprule in mapping:
            if re.match(maprule[0], self.mimetype):
                return maprule[1]
        return "0"

    def handleeaext(self, selector, vfs):
        """Handle getting extended attributes from the filesystem."""
        global eaexts
        if eaexts is None:
            eaexts = eval(self.config.get("GopherEntry", "eaexts"))
        if vfs is None:
            from pygopherd.handlers.base import VFS_Real

            vfs = VFS_Real(self.config)

        for extension, blockname in list(eaexts.items()):
            if blockname in self.ea:
                continue
            try:
                rfile = vfs.open(selector + extension, "rb")
                self.setea(
                    blockname, b"\n".join([x.rstrip() for x in rfile.readlines(20480)])
                )
            except IOError:
                pass

    def getselector(self, default=None):
        if self.selector is None:
            return default
        return self.selector

    def setselector(self, arg):
        self.selector = arg

    def getconfig(self, default=None):
        return self.config or default

    def setconfig(self, arg):
        self.config = arg

    def getfspath(self, default=None):
        if self.fspath is None:
            return default
        return self.fspath

    def setfspath(self, arg):
        self.fspath = arg

    def gettype(self, default=None):
        if self.type is None:
            return default
        return self.type

    def settype(self, arg):
        self.type = arg

    def getname(self, default=None):
        if self.name is None:
            return default
        return self.name

    def setname(self, arg):
        self.name = arg

    def gethost(self, default=None):
        if self.host is None:
            return default
        return self.host

    def sethost(self, arg):
        self.host = arg

    def getport(self, default=None):
        if self.port is None:
            return default
        return self.port

    def setport(self, arg):
        self.port = arg

    def getmimetype(self, default=None):
        if self.mimetype is None:
            return default
        return self.mimetype

    def getencodedmimetype(self, default=None):
        if self.encodedmimetype is None:
            return default
        return self.encodedmimetype

    def setencodedmimetype(self, arg):
        self.encodedmimetype = arg

    def setmimetype(self, arg):
        self.mimetype = arg

    def getsize(self, default=None):
        if self.size is None:
            return default
        return self.size

    def setsize(self, arg):
        self.size = arg

    def getencoding(self, default=None):
        if self.encoding is None:
            return default
        return self.encoding

    def setencoding(self, arg):
        self.encoding = arg

    def getlanguage(self, default=None):
        if self.language is None:
            return default
        return self.language

    def setlanguage(self, arg):
        self.language = arg

    def getctime(self, default=None):
        if self.ctime is None:
            return default
        return self.ctime

    def setctime(self, arg):
        self.ctime = arg

    def getmtime(self, default=None):
        if self.mtime is None:
            return default
        return self.mtime

    def setmtime(self, arg):
        self.mtime = arg

    def getpopulated(self, default=None):
        if self.populated is not None:
            return self.populated
        return default

    def setpopulated(self, arg):
        self.populated = arg

    def geturl(self, defaulthost="MISSINGHOST", defaultport=70):
        """If this selector is a URL: one, then we just return the rest of
        it.  Otherwise, generate a gopher:// URL and quote it."""
        if re.search("^(/|)URL:.+://", self.selector):
            if self.selector[0] == "/":
                return self.selector[5:]
            else:
                return self.selector[4:]

        retval = "gopher://%s:%d/" % (
            self.gethost(defaulthost),
            self.getport(defaultport),
        )
        retval += urllib.parse.quote("%s%s" % (self.gettype(), self.getselector()))
        return retval

    def getnum(self, default=None):
        if self.num is not None:
            return self.num
        return default

    def setnum(self, arg):
        self.num = arg

    def getgopherpsupport(self, default=None):
        if self.gopherpsupport is not None:
            return self.gopherpsupport
        return default

    def setgopherpsupport(self, arg):
        self.gopherpsupport = arg

    def getea(self, name, default=None):
        if name in self.ea:
            return self.ea[name]
        return default

    def geteadict(self):
        return self.ea

    def setea(self, name, value):
        self.ea[name] = value


def getinfoentry(text, config):
    entry = GopherEntry("fake", config)
    entry.name = text
    entry.host = "(NULL)"
    entry.port = 0
    entry.type = "i"
    return entry
