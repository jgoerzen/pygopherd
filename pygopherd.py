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

###########################################################################
# Initialize the config file.
###########################################################################

conffile = '/etc/pygopherd/pygopherd.conf'

if len(sys.argv) > 1:
    conffile = sys.argv[1]

if not (os.path.isfile(conffile) and os.access(conffile, os.R_OK)):
    sys.stderr.write("Could NOT access config file %s\nPlease specify config file as a command-line argument\n" % conffile)
    sys.exit(200)

config = ConfigParser()
config.read(conffile)
logger.init(config)
logger.log("Pygopherd starting, using configuration file %s" % conffile)

###########################################################################
# Initialize the MIME types file.
###########################################################################

mimetypesfiles = config.get("pygopherd", "mimetypes").split(":")
mimetypesfiles = filter(lambda x: os.path.isfile(x) and os.access(x, os.R_OK),
                        mimetypesfiles)

if not mimetypesfiles:
    errmsg = "Could not find any mimetypes files; check mimetypes option in config."
    logger.log(errmsg)
    sys.stderr.write(errmsg + "\n")
    sys.exit(201)
    
mimetypes.init(mimetypesfiles)
logger.log("mimetypes initialized with files: " + str(mimetypesfiles))

###########################################################################
# Declare the server classes.
###########################################################################

class GopherRequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        request = self.rfile.readline()

        protohandler = \
                     ProtocolMultiplexer.getProtocol(request, \
                     self.server, self, self.rfile, self.wfile, self.server.config)
        protohandler.handle()

# Pick up the server type from the config.

servertype = eval("SocketServer." + config.get("pygopherd", "servertype"))

class MyServer(servertype):
    allow_reuse_address = 1

    def server_bind(self):
        """Override server_bind to store server name."""
        servertype.server_bind(self)
        host, port = self.socket.getsockname()
        if config.has_option("pygopherd", "servername"):
            self.server_name = config.get("pygopherd", "servername")
        else:
            self.server_name = socket.getfqdn(host)
        self.server_port = port
        
# Instantiate a server.  Has to be done before the security so we can
# get a privileged port if necessary.

s = MyServer(('', config.getint('pygopherd', 'port')),
             GopherRequestHandler)
s.config = config

###########################################################################
# Handle security -- dropping privileges.
###########################################################################

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

###########################################################################
# Start it up!
###########################################################################

s.serve_forever()

