# pygopherd -- Gopher-based protocol server in Python
# module: implementation of standard gopher (RFC 1436) protocol
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
from pygopherd import handlers, protocols
from pygopherd.protocols.base import BaseGopherProtocol

class GopherProtocol(BaseGopherProtocol):
    """Implementation of basic protocol.  Will handle every query."""
    def canhandlerequest(self):
        return 1

    def renderobjinfo(self, entry):
        retval = entry.gettype() + \
                 entry.getname() + "\t" + \
                 entry.getselector() + "\t" + \
                 entry.gethost(default = self.server.server_name) + "\t" + \
                 str(entry.getport(default = self.server.server_port))
        if entry.getgopherpsupport():
            return retval + "\t+\r\n"
        else:
            return retval + "\r\n"

