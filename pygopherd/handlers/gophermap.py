# pygopherd -- Gopher-based protocol server in Python
# module: Handling of gophermap directory files
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

import SocketServer
import re
import os, stat, os.path, mimetypes
from pygopherd import protocols, gopherentry
from pygopherd.handlers import base
from stat import *

class BuckGophermapHandler(base.BaseHandler):
    """Bucktooth selector handler.  Adheres to the specification
    at gopher://gopher.floodgap.com:70/0/buck/dbrowse%3Ffaquse%201"""
    def canhandlerequest(self):
        """We can handle the request if it's for a directory AND
        the directory has a gophermap file."""
        return self.vfs.isfile(self.getselector() + '/gophermap') or \
               (self.statresult and S_ISREG(self.statresult[ST_MODE]) and \
                self.getselector().endswith(".gophermap"))

    def getentry(self):
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            if (self.statresult and S_ISREG(self.statresult[ST_MODE]) and \
                self.getselector().endswith(".gophermap")):
                self.entry.populatefromvfs(self.vfs, self.getselector())
            else:
                self.entry.populatefromfs(self.getselector(), self.statresult, vfs = self.vfs)
            
        return self.entry

    def prepare(self):
        self.selectorbase = self.selector
        if self.selectorbase == '/':
            self.selectorbase = ''           # Avoid dup slashes

        if self.getselector().endswith(".gophermap") and \
           self.statresult and S_ISREG(self.statresult[ST_MODE]):
            self.rfile = self.vfs.open(self.getselector(), 'rb')
        else:
            self.rfile = self.vfs.open(self.selectorbase + '/gophermap', 'rb')

        self.entries = []

        selectorbase = self.selectorbase
        
        while 1:
            line = self.rfile.readline()
            if not line:
                break
            if re.search("\t", line):   # gophermap link
                args = map(lambda arg: arg.strip(), line.split("\t"))

                if len(args) < 2 or not len(args[1]):
                    args[1] = args[0][1:] # Copy display string to selector

                selector = args[1]
                if selector[0] != '/': # Relative link
                    selector = selectorbase + '/' + selector
                
                entry = gopherentry.GopherEntry(selector, self.config)
                entry.type = args[0][0]
                entry.name = args[0][1:]

                if len(args) >= 3 and len(args[2]):
                    entry.host = args[2]

                if len(args) >= 4 and len(args[3]):
                    entry.port = int(args[3])

                if entry.gethost() == None and entry.getport() == None:
                    # If we're using links on THIS server, try to fill
                    # it in for gopher+.
                    if self.vfs.exists(selector):
                        entry.populatefromvfs(self.vfs, selector)
                self.entries.append(entry)
            else:                       # Info line
                line = line.strip()
                self.entries.append(gopherentry.getinfoentry(line, self.config))

    def isdir(self):
        return 1

    def getdirlist(self):
        return self.entries

