# pygopherd -- Gopher-based protocol server in Python
# module: regular file handling
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
import os, stat, os.path, mimetypes
from pygopherd import protocols, handlers, gopherentry
import pygopherd.pipe
from stat import *

class FileHandler(handlers.base.BaseHandler):
    def canhandlerequest(self):
        """We can handle the request if it's for a file."""
        return self.statresult and S_ISREG(self.statresult[ST_MODE])

    def getentry(self):
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            self.entry.populatefromfs(self.getfspath(), self.statresult)
        return self.entry

    def prepare(self):
        self.rfile = open(self.getfspath(), "rb")

    def write(self, wfile):
        while 1:
            string = self.rfile.read(4096)
            if not len(string):
                break
            wfile.write(string)
        self.rfile.close()
        self.rfile = None

decompressors = None

class CompressedFileHandler(FileHandler):
    def canhandlerequest(self):
        return FileHandler.canhandlerequest(self) and \
               self.getentry().getencoding()
    
    def write(self, wfile):
        global decompressors
        if decompressors == None:
            decompressors = \
                eval(self.config.get("handlers.file.CompressedFileHandler",
                                     "decompressors"))
        if decompressors.has_key(self.getentry().getencoding()):
            decompprog = decompressors[self.getentry().getencoding()]
            pygopherd.pipe.pipedata_unix(decompprog, [decompprog],
                                         childstdin = self.rfile,
                                         childstdout = wfile,
                                         pathsearch = 1)
            self.rfile.close()
            self.rfile = None
        else:
            FileHandler.write(self, wfile)

    
