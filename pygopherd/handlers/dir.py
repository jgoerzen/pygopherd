
# pygopherd -- Gopher-based protocol server in Python
# module: regular directory handling
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
import os, stat, os.path, mimetypes, time
from pygopherd import protocols, gopherentry, handlers
from stat import *
import cPickle

cachetime = None
cachefile = None

class DirHandler(handlers.base.BaseHandler):
    def canhandlerequest(self):
        """We can handle the request if it's for a directory."""
        return self.statresult and S_ISDIR(self.statresult[ST_MODE])

    def getentry(self):
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            self.entry.populatefromfs(self.getfspath(), self.statresult)
        return self.entry

    def prep_initfiles(self):
        "Initialize the list of files.  Ignore the files we're suppoed to."
        self.files = []
        dirfiles = os.listdir(self.getfspath())
        ignorepatt = self.config.get("handlers.dir.DirHandler", "ignorepatt")
        for file in dirfiles:
            if self.prep_initfiles_canaddfile(ignorepatt,
                                              self.selectorbase + '/' + file,
                                              file):
                self.files.append(file)

    def prep_initfiles_canaddfile(self, ignorepatt, pattern, file):
        return not re.search(ignorepatt, pattern)

    def prep_entries(self):
        "Generate entries from the list."

        self.fileentries = []
        for file in self.files:
            # We look up the appropriate handler for this object, and ask
            # it to give us an entry object.
            handler = handlers.HandlerMultiplexer.\
                        getHandler(self.selectorbase + '/' \
                                   + file, self.searchrequest, self.protocol,
                                   self.config)
            fileentry = handler.getentry()
            self.prep_entriesappend(file, handler, fileentry)

    def prep_entriesappend(self, file, handler, fileentry):
        """Subclasses can override to do post-processing on the entry while
        we still have the filename around.
        IE, for .cap files."""
        self.fileentries.append(fileentry)

    def prepare(self):
        # Initialize some variables.

        self.fsbase = self.getfspath()
        if self.fsbase == '/':
            self.fsbase = ''                 # Avoid dup slashes
        self.selectorbase = self.selector
        if self.selectorbase == '/':
            self.selectorbase = ''           # Avoid dup slashes        
            
        if self.loadcache():
            # No need to do anything else.
            return 0                    # Did nothing.

        self.prep_initfiles()

        # Sort the list.
        self.files.sort()

        self.prep_entries()
        return 1                        # Did something.

    def write(self, wfile):
        startstr = self.protocol.renderdirstart(self.entry)
        if (startstr):
            wfile.write(startstr)

        for fileentry in self.fileentries:
            wfile.write(self.protocol.renderobjinfo(fileentry))

        endstr = self.protocol.renderdirend(self.entry)
        if (endstr):
            wfile.write(endstr)
        self.savecache()

            
    def loadcache(self):
        global cachetime, cachefile
        self.fromcache = 0
        if cachetime == None:
            cachetime = self.config.getint("handlers.dir.DirHandler",
                                           "cachetime")
            cachefile = self.config.get("handlers.dir.DirHandler",
                                        "cachefile")

        cachename = self.fsbase + "/" + cachefile
        try:
            statval = os.stat(cachename)
        except OSError:
            return 0

        if (time.time() - statval[stat.ST_MTIME] < cachetime):
            fp = open(cachename, "rb")
            self.fileentries = cPickle.load(fp)
            fp.close()
            self.fromcache = 1
            return 1
        return 0

    def savecache(self):
        global cachefile
        if self.fromcache:
            # Don't resave the cache.
            return
        try:
            fp = open(self.fsbase + "/" + cachefile, "wb")
            cPickle.dump(self.fileentries, fp, 1)
            fp.close()
        except IOError:
            pass

    
