# pygopherd -- Gopher-based protocol server in Python
# module: Generic gopher entry object
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import SocketServer
import re
import os, stat, os.path, mimetypes, protocols, handlers, urllib

mapping = None

class GopherEntry:
    """The entry object for Gopher.  It holds information about each
    Gopher object."""

    def __init__(self, selector, config):
        global mapping
        """Initialize object based on a selector and config."""
        if not mapping:
            mapping = eval(config.get("GopherEntry", "mapping"))
        self.selector = selector
        self.config = config
        self.fspath = None
        self.type = None
        self.name = None
        self.host = None
        self.port = None
        self.mimetype = None
        self.size = None
        self.encoding = None
        self.populated = 0
        self.language = None
        self.ctime = None
        self.mtime = None
        self.num = 0
        self.gopherpsupport = 0

    def populatefromfs(self, fspath, statval = None):
        self.fspath = fspath

        if self.populated:
            return

        # Just let the stat catch the OSError rather than testing
        # for existance here.  Help cut down on the number of syscalls.

        if not (self.gethost() == None and self.getport() == None):
            return

        if not statval:
            try:
                statval = os.stat(self.fspath)
            except OSError:
                return
        
        self.populated = 1
        self.gopherpsupport = 1         # Indicate gopher+ support for locals.

        if self.ctime == None:
            self.ctime = statval[9]
        if self.mtime == None:
            self.mtime = statval[8]

        if self.name == None:
            self.name = os.path.basename(self.selector)

        if stat.S_ISDIR(statval[0]):
            self.type = '1'
            self.mimetype = 'application/gopher-menu'
            return

        if self.size == None:
            self.size = statval[6]          # Only set this if it's not a dir.
        mimetype, encoding = mimetypes.guess_type(self.selector, strict = 0)

        if mimetype and not self.mimetype:
            self.mimetype = mimetype
        if encoding and not self.encoding:
            self.encoding = encoding

        if not self.mimetype:
            self.mimetype = self.config.get("GopherEntry", "defaultmimetype")

        if self.mimetype and self.type == None:
            self.type = 0
            for maprule in mapping:
                if re.match(maprule[0], self.mimetype):
                    self.type = maprule[1]
                    break

    def getselector(self, default = None):
        if self.selector == None:
            return default
        return self.selector
    def setselector(self, arg):
        self.selector = arg
    def getfspath(self, default = None):
        if self.fspath == None:
            return default
        return self.fspath
    def gettype(self, default = None):
        if self.type == None:
            return default
        return self.type
    def settype(self, arg):
        self.type = arg
    def getname(self, default = None):
        if self.name == None:
            return default
        return self.name
    def setname(self, arg):
        self.name = arg
    def gethost(self, default = None):
        if self.host == None:
            return default
        return self.host
    def sethost(self, arg):
        self.host = arg
    def getport(self, default = None):
        if self.port == None:
            return default
        return self.port
    def setport(self, arg):
        self.port = arg
    def getmimetype(self, default = None):
        if self.mimetype == None:
            return default
        return self.mimetype
    def setmimetype(self, arg):
        self.mimetype = arg
    def getsize(self, default = None):
        if self.size == None:
            return default
        return self.size
    def getencoding(self, default = None):
        if self.encoding == None:
            return default
        return self.encoding
    def getlanguage(self, default = None):
        if self.language == None:
            return default
        return self.language
    def getctime(self, default = None):
        if self.ctime == None:
            return default
        return self.ctime
    def getmtime(self, default = None):
        if self.mtime == None:
            return default
        return self.mtime
    
    def geturl(self, defaulthost = 'MISSINGHOST', defaultport = 0):
        retval = 'gopher://%s:%d/' % (self.gethost(defaulthost),
                                      self.getport(defaultport))
        retval += urllib.quote('%s%s' % (self.gettype(), self.getselector()))
        return retval

    def getnum(self):
        return self.num
    def setnum(self, arg):
        self.num = arg

    def getgopherpsupport(self):
        return self.gopherpsupport
    def setgopherpsupport(self, arg):
        self.gopherpsupport = arg
