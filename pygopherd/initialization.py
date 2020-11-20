# Python-based gopher server
# Module: initialization
# COPYRIGHT #
# Copyright (C) 2002 John Goerzen
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
# END OF COPYRIGHT #

from configparser import ConfigParser

# Import lots of stuff so it's here before chrooting.
import socket, os, sys, socketserver, os.path
import errno, struct

from pygopherd import GopherExceptions, logger, sighandlers
from pygopherd.protocols import ProtocolMultiplexer
import pygopherd.fileext
import mimetypes

import traceback


def initconffile(conffile):
    if not (os.path.isfile(conffile) and os.access(conffile, os.R_OK)):
        raise Exception(
            "Could NOT access config file %s\nPlease specify config file as a command-line argument\n"
            % conffile
        )

    config = ConfigParser()
    config.read(conffile)
    return config


def initlogger(config, conffile):
    logger.init(config)
    logger.log("Pygopherd starting, using configuration file %s" % conffile)


def initexceptions(config):
    GopherExceptions.init(config.getboolean("pygopherd", "tracebacks"))


def initmimetypes(config):
    mimetypesfiles = config.get("pygopherd", "mimetypes").split(":")
    mimetypesfiles = [
        x for x in mimetypesfiles if os.path.isfile(x) and os.access(x, os.R_OK)
    ]

    if not mimetypesfiles:
        errmsg = "Could not find any mimetypes files; check mimetypes option in config."
        logger.log(errmsg)
        raise Exception(errmsg)

    configencoding = eval(config.get("pygopherd", "encoding"))
    mimetypes.encodings_map.clear()
    for key, value in configencoding:
        mimetypes.encodings_map[key] = value
    mimetypes.init(mimetypesfiles)
    logger.log("mimetypes initialized with files: " + str(mimetypesfiles))

    # Set up the inverse mapping file.

    pygopherd.fileext.init()


class GopherRequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        request = self.rfile.readline()

        protohandler = ProtocolMultiplexer.getProtocol(
            request, self.server, self, self.rfile, self.wfile, self.server.config
        )
        try:
            protohandler.handle()
        except socket.error as e:
            if not (e[0] in [errno.ECONNRESET, errno.EPIPE]):
                traceback.print_exc()
            GopherExceptions.log(sys.exc_info()[1], protohandler, None)
        except:
            if GopherExceptions.tracebacks:
                # Yes, this may be invalid.  Not much else we can do.
                # traceback.print_exc(file = self.wfile)
                traceback.print_exc()
            GopherExceptions.log(sys.exc_info()[1], protohandler, None)


def getserverobject(config):
    # Pick up the server type from the config.

    servertype = eval("socketserver." + config.get("pygopherd", "servertype"))

    class MyServer(servertype):
        allow_reuse_address = 1

        def server_bind(self):
            """Override server_bind to store server name."""
            servertype.server_bind(self)

            # Set a timeout.
            if config.has_option("pygopherd", "timeout"):
                mytimeout = struct.pack(
                    "ll", int(config.get("pygopherd", "timeout")), 0
                )
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, mytimeout)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDTIMEO, mytimeout)
                # self.socket.settimeout(int(config.get('pygopherd', 'timeout')))
            host, port = self.socket.getsockname()
            if config.has_option("pygopherd", "servername"):
                self.server_name = config.get("pygopherd", "servername")
            else:
                self.server_name = socket.getfqdn(host)
            if config.has_option("pygopherd", "advertisedport"):
                self.server_port = config.getint("pygopherd", "advertisedport")
            else:
                self.server_port = port

    # Instantiate a server.  Has to be done before the security so we can
    # get a privileged port if necessary.

    interface = ""
    if config.has_option("pygopherd", "interface"):
        servername = config.get("pygopherd", "interface")
        interface = config.get("pygopherd", "interface")

    try:
        s = MyServer(
            (interface, config.getint("pygopherd", "port")), GopherRequestHandler
        )
    except:
        GopherExceptions.log(sys.exc_info()[1], None, None)
        logger.log("Application startup NOT successful!")
        raise

    s.config = config
    return s


def initsecurity(config):
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

    if idsetuid is not None or idsetgid is not None:
        os.setgroups(())
        logger.log("Supplemental group list cleared.")

    if idsetgid is not None:
        os.setregid(idsetgid, idsetgid)
        logger.log("Switched to group %d" % idsetgid)

    if idsetuid is not None:
        os.setreuid(idsetuid, idsetuid)
        logger.log("Switched to uid %d" % idsetuid)


def initconditionaldetach(config):
    if config.getboolean("pygopherd", "detach"):
        pid = os.fork()
        if pid:
            logger.log("Parent process detaching; child is %d" % pid)
            sys.exit(0)


def initpidfile(config):
    if config.has_option("pygopherd", "pidfile"):
        pidfile = config.get("pygopherd", "pidfile")
        fd = open(pidfile, "wt")
        fd.write("%d\n" % os.getpid())
        fd.close()


def initpgrp(config):
    if "setpgrp" in os.__dict__:
        os.setpgrp()
        pgrp = os.getpgrp()
        logger.log("Process group is %d" % pgrp)
        return pgrp
    else:
        logger.log("setpgrp() unavailable; not initializing process group")
        return None


def initsighandlers(config, pgrp):
    sighandlers.setsighuphandler()
    sighandlers.setsigtermhandler(pgrp)


def initeverything(conffile):
    config = initconffile(conffile)
    initlogger(config, conffile)
    initexceptions(config)
    initmimetypes(config)
    s = getserverobject(config)
    initconditionaldetach(config)
    initpidfile(config)
    pgrp = initpgrp(config)
    initsighandlers(config, pgrp)
    initsecurity(config)
    os.chdir(config.get("pygopherd", "root"))

    logger.log("Running.  Root is '%s'" % config.get("pygopherd", "root"))
    return s
