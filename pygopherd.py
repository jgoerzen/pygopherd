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

# Import lots of stuff so it's here before chrooting.

from ConfigParser import ConfigParser
import socket, os, sys, SocketServer, re, stat, os.path, UserDict
from pygopherd import handlers, protocols
from pygopherd.protocols import *
from pygopherd.protocols import ProtocolMultiplexer
from pygopherd.handlers import *
from pygopherd.handlers import HandlerMultiplexer
from pygopherd import *
import mimetypes

import traceback

config = ConfigParser()
config.read("pygopherd.conf")
mimetypes.init([config.get("pygopherd", "mimetypes")])
logger.init(config)
logger.log("Pygopherd started.")

class GopherRequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        request = self.rfile.readline()

        protohandler = \
                     ProtocolMultiplexer.getProtocol(request, \
                     self.server, self, self.rfile, self.wfile, self.server.config)
        protohandler.handle()

class MyServer(SocketServer.ForkingTCPServer):
    allow_reuse_address = 1

    def server_bind(self):
        """Override server_bind to store server name."""
        SocketServer.ForkingTCPServer.server_bind(self)
        host, port = self.socket.getsockname()
        self.server_name = socket.getfqdn(host)
        self.server_port = port
        
s = MyServer(('', config.getint('pygopherd', 'port')),
             GopherRequestHandler)
s.config = config

idsetuid = None
idsetgid = None

if config.has_option("pygopherd", "setuid"):
    import pwd
    idsetuid = pwd.getpwnam(config.get("pygopherd", "setuid"))[2]

if config.has_option("pygopherd", "setgid"):
    import grp
    idsetgid = grp.getgrnam(config.get("pygopherd", "setgid"))[2]
    
if config.getboolean("pygopherd", "usechroot"):
    os.chroot(config.get("pygopherd", "root"))
    logger.log("Chrooted to " + config.get("pygopherd", "root"))
    config.set("pygopherd", "root", "/")

if idsetuid != None or idsetgid != None:
    os.setgroups( () )
    logger.log("Supplemental group list cleared.")

if idsetgid != None:
    os.setregid(idsetgid, idsetgid)
    logger.log("Switched to group %d" % idsetgid)

if idsetuid != None:
    os.setreuid(idsetuid, idsetuid)
    logger.log("Switched to uid %d" % idsetuid)

logger.log("Root is '%s'" % config.get("pygopherd", "root"))

s.serve_forever()

