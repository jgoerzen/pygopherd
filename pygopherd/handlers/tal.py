# pygopherd -- Gopher-based protocol server in Python
# module: TAL file handling.
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

#try:
from simpletal import simpleTAL, simpleTALES
#    talavailable = 1
#except:
#    talavailable = 0

from pygopherd.handlers.file import FileHandler
from pygopherd import gopherentry
import re

class TALFileHandler(FileHandler):
    def canhandlerequest(self):
        """We can handle the request if it's for a file ending with .thtml."""
        canhandle = FileHandler.canhandlerequest(self) and self.getselector().endswith(".tal")
        if not canhandle:
            return 0
        self.talbasename = self.getselector()[:-4]
        self.allowpythonpath = 1
        if self.config.has_option('handlers.tal.TALFileHandler', 'allowpythonpath'):
            self.allowpythonpath = self.config.getboolean('handlers.tal.TALFileHandler', 'allowpythonpath')
        return 1

    def getentry(self):
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            self.entry.populatefromfs(self.getselector(), self.statresult, vfs = self.vfs)
            assert self.entry.getencoding() == 'tal.TALFileHandler'
            # Remove the TAL encoding and revert to default.
            self.entry.mimetype = self.entry.getencodedmimetype()
            self.entry.encodedmimetype = None
            self.entry.realencoding = self.entry.encoding
            self.entry.encoding = None
            self.entry.type = self.entry.guesstype()
            
        return self.entry

    def write(self, wfile):
        rfile = self.vfs.open(self.getselector())
        context = simpleTALES.Context(allowPythonPath = self.allowpythonpath)
        context.addGlobal("selector", self.getselector())
        context.addGlobal('handler', self)
        context.addGlobal('entry', self.getentry())
        context.addGlobal('talbasename', self.talbasename)
        context.addGlobal('allowpythonpath', self.allowpythonpath)
        context.addGlobal('protocol', self.protocol)

        template = simpleTAL.compileHTMLTemplate(rfile)
        rfile.close()
        template.expand(context, wfile)
