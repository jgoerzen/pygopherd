# pygopherd -- Gopher-based protocol server in Python
# module: regular file handling
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

import re
from pygopherd import gopherentry
from pygopherd.handlers import base
import pygopherd.pipe
from stat import *


class FileHandler(base.BaseHandler):
    def canhandlerequest(self):
        """We can handle the request if it's for a file."""
        return self.statresult and S_ISREG(self.statresult[ST_MODE])

    def getentry(self):
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            self.entry.populatefromfs(self.getselector(), self.statresult, vfs=self.vfs)
        return self.entry

    def write(self, wfile):
        self.vfs.copyto(self.getselector(), wfile)


class CompressedFileHandler(FileHandler):
    decompressors = None
    decompresspatt = None

    def canhandlerequest(self):
        self.initdecompressors()

        # It's OK to call just canhandlerequest() since we're not
        # overriding the security or isrequestforme functions.

        return (
            FileHandler.canhandlerequest(self)
            and self.getentry().realencoding
            and self.getentry().realencoding in self.decompressors
            and re.search(self.decompresspatt, self.selector)
        )

    def getentry(self):
        if not self.entry:
            self.entry = FileHandler.getentry(self)
            self.entry.realencoding = None
            if (
                self.entry.getencoding()
                and self.entry.getencoding() in self.decompressors
                and self.entry.getencodedmimetype()
            ):
                # When the client gets it, there will not be
                # encoding.  Therefore, we remove the encoding and switch
                # to the real MIME type.
                self.entry.mimetype = self.entry.getencodedmimetype()
                self.entry.encodedmimetype = None
                self.entry.realencoding = self.entry.encoding
                self.entry.encoding = None
                self.entry.type = self.entry.guesstype()
        return self.entry

    def initdecompressors(self):
        if self.decompressors is None:
            self.decompressors = eval(
                self.config.get("handlers.file.CompressedFileHandler", "decompressors")
            )
            self.decompresspatt = self.config.get(
                "handlers.file.CompressedFileHandler", "decompresspatt"
            )

    def write(self, wfile):
        decompprog = self.decompressors[self.getentry().realencoding]
        pygopherd.pipe.pipedata_unix(
            decompprog,
            [decompprog],
            childstdin=self.rfile,
            childstdout=wfile,
            pathsearch=1,
        )
        self.rfile.close()
        self.rfile = None
