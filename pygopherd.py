#!/usr/bin/python2.2

# Python-based gopher server
# COPYRIGHT #
# Copyright (C) 2002 John Goerzen
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
# END OF COPYRIGHT #

#

from ConfigParser import ConfigParser
import socket, os, sys, signal, SocketServer
from handlers import GopherRequestHandler
import mimetypes

config = ConfigParser()
config.read("pygopherd.conf")
mimetypes.init(config.get("serving", "mimetypes"))

class MyServer(SocketServer.ForkingTCPServer):
    allow_reuse_address = 1

    def server_bind(self):
        """Override server_bind to store server name."""
        SocketServer.ForkingTCPServer.server_bind(self)
        host, port = self.socket.getsockname()
        self.server_name = socket.getfqdn(host)
        self.server_port = port
        

s = MyServer(('', config.getint('serving', 'port')),
             GopherRequestHandler)
s.config = config
s.mapping = eval(config.get("serving", "mapping"))
s.defaulttype = config.get("serving", "defaulttype")
print s.mapping
s.serve_forever()
