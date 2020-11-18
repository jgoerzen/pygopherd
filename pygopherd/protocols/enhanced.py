# pygopherd -- Gopher-based protocol server in Python
# module: experimental enhanced gopher protocol
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
import os, stat, os.path, mimetypes
from pygopherd import handlers, protocols
from pygopherd.protocols import rfc1436


class EnhancedGopherProtocol(rfc1436.GopherProtocol):
    def renderobjinfo(self, entry):
        return (
            entry.gettype()
            + entry.getname()
            + "\t"
            + entry.getselector()
            + "\t"
            + entry.gethost(default=self.server.server_name)
            + "\t"
            + str(entry.getport(default=self.server.server_port))
            + "\t"
            + str(entry.getsize())
            + "\t"
            + entry.getmimetype()
            + "\t"
            + entry.getencoding()
            + "\t"
            + entry.getlanguage()
        )
