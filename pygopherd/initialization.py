import errno
import io
import mimetypes
import os
import os.path
import typing

# Import lots of stuff so it's here before chrooting.
import socketserver
import sys
import traceback
from configparser import ConfigParser

import pygopherd.fileext
import pygopherd.server
from pygopherd import GopherExceptions, logger, sighandlers
from pygopherd.protocols import ProtocolMultiplexer


def init_config(filename: str) -> ConfigParser:
    if not (os.path.isfile(filename) and os.access(filename, os.R_OK)):
        raise Exception(
            f"Could NOT access config file {filename}\n"
            f"Please specify config file as a command-line argument\n"
        )

    config = ConfigParser()
    config.read(filename)
    return config


def init_logger(config: ConfigParser, filename: str) -> None:
    logger.init(config)
    logger.log(f"Pygopherd starting, using configuration file {filename}")


def init_exceptions(config: ConfigParser) -> None:
    GopherExceptions.init(config.getboolean("pygopherd", "tracebacks"))


def init_mimetypes(config: ConfigParser) -> None:
    files = config.get("pygopherd", "mimetypes").split(":")
    files = [x for x in files if os.path.isfile(x) and os.access(x, os.R_OK)]
    if not files:
        errmsg = "Could not find any mimetypes files; check mimetypes option in config."
        logger.log(errmsg)
        raise Exception(errmsg)

    encoding = eval(config.get("pygopherd", "encoding"))
    mimetypes.encodings_map.clear()
    for key, value in encoding:
        mimetypes.encodings_map[key] = value

    mimetypes.init(files)
    logger.log(f"mimetypes initialized with files: {files}")

    # Set up the inverse mapping file.

    pygopherd.fileext.init()


class GopherRequestHandler(socketserver.StreamRequestHandler):

    rfile: io.BytesIO
    wfile: io.BytesIO
    server: pygopherd.server.BaseServer

    def handle(self) -> None:
        request = self.rfile.readline().decode(errors="surrogateescape")

        protohandler = ProtocolMultiplexer.getProtocol(
            request, self.server, self, self.rfile, self.wfile, self.server.config
        )
        try:
            protohandler.handle()
        except IOError as e:
            if not (e.errno in [errno.ECONNRESET, errno.EPIPE]):
                traceback.print_exc()
            GopherExceptions.log(e, protohandler, None)
        except Exception as e:
            if GopherExceptions.tracebacks:
                # Yes, this may be invalid.  Not much else we can do.
                # traceback.print_exc(file = self.wfile)
                traceback.print_exc()
            GopherExceptions.log(e, protohandler, None)


def get_server(config: ConfigParser) -> pygopherd.server.BaseServer:
    # Pick up the server type from the config.
    server_class: typing.Type[pygopherd.server.BaseServer]

    server_type = config.get("pygopherd", "servertype")
    if server_type == "ForkingTCPServer":
        server_class = pygopherd.server.ForkingTCPServer
    elif server_type == "ThreadingTCPServer":
        server_class = pygopherd.server.ThreadingTCPServer
    else:
        raise RuntimeError(f"Invalid servertype option: {server_type}")

    # Instantiate a server.  Has to be done before the security so we can
    # get a privileged port if necessary.
    interface = ""
    if config.has_option("pygopherd", "interface"):
        interface = config.get("pygopherd", "interface")

    port = config.getint("pygopherd", "port")
    address = (interface, port)

    try:
        server = server_class(config, address, GopherRequestHandler)
    except Exception as e:
        GopherExceptions.log(e, None, None)
        logger.log("Application startup NOT successful!")
        raise

    return server


def init_security(config: ConfigParser) -> None:
    uid = None
    gid = None

    if config.has_option("pygopherd", "setuid"):
        import pwd

        uid = pwd.getpwnam(config.get("pygopherd", "setuid"))[2]

    if config.has_option("pygopherd", "setgid"):
        import grp

        gid = grp.getgrnam(config.get("pygopherd", "setgid"))[2]

    if config.getboolean("pygopherd", "usechroot"):
        chroot_user = config.get("pygopherd", "root")
        os.chroot(chroot_user)
        logger.log(f"Chrooted to {chroot_user}")
        config.set("pygopherd", "root", "/")

    if uid is not None or gid is not None:
        os.setgroups(())
        logger.log("Supplemental group list cleared.")

    if gid is not None:
        os.setregid(gid, gid)
        logger.log(f"Switched to group {gid}")

    if uid is not None:
        os.setreuid(uid, uid)
        logger.log(f"Switched to uid {uid}")


def init_conditional_detach(config: ConfigParser) -> None:
    if config.getboolean("pygopherd", "detach"):
        pid = os.fork()
        if pid:
            logger.log("Parent process detaching; child is %d" % pid)
            sys.exit(0)


def init_pidfile(config: ConfigParser) -> None:
    if config.has_option("pygopherd", "pidfile"):
        pidfile = config.get("pygopherd", "pidfile")

        with open(pidfile, "w") as fd:
            fd.write("%d\n" % os.getpid())


def init_process_group(config: ConfigParser) -> None:
    try:
        os.setpgrp()
        process_group = os.getpgrp()
    except OSError as e:
        logger.log(f"setpgrp() failed with {e}")
    except AttributeError:
        logger.log("setpgrp() unavailable; not initializing process group")
    else:
        logger.log(f"Process group is {process_group}")


def init_signal_handlers() -> None:
    sighandlers.setsighuphandler()
    sighandlers.setsigtermhandler()


def initialize(filename: str) -> pygopherd.server.BaseServer:
    config = init_config(filename)

    init_logger(config, filename)
    init_exceptions(config)
    init_mimetypes(config)
    server = get_server(config)
    init_conditional_detach(config)
    init_pidfile(config)
    init_process_group(config)
    init_signal_handlers()
    init_security(config)

    root = config.get("pygopherd", "root")
    logger.log(f"Running.  Root is '{root}'")
    return server
