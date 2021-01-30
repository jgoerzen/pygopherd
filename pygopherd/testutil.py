import configparser
import os
import typing
from io import BytesIO, StringIO

from pygopherd import initialization, logger
from pygopherd.protocols import ProtocolMultiplexer
from pygopherd.server import BaseServer, GopherRequestHandler

TEST_DATA = os.path.join(os.path.dirname(__file__), "..", "testdata")


def get_config() -> configparser.ConfigParser:
    config = initialization.init_config("conf/pygopherd.conf")
    config.set("pygopherd", "root", TEST_DATA)
    return config


def get_string_logger():
    config = get_config()
    config.set("logger", "logmethod", "file")
    logger.init(config)
    stringfile = StringIO()

    def log(message: str) -> None:
        stringfile.write(message + "\n")

    logger.log = log
    return stringfile


def get_testing_server(
    config: typing.Optional[configparser.ConfigParser] = None,
) -> BaseServer:
    config = config or get_config()
    config.set("pygopherd", "port", "64777")
    s = initialization.get_server(config)
    s.server_close()
    return s


def get_testing_handler(
    rfile: BytesIO,
    wfile: BytesIO,
    config: typing.Optional[configparser.ConfigParser] = None,
) -> GopherRequestHandler:
    """Creates a testing handler with input from rfile.  Fills in
    other stuff with fake values."""

    config = config or get_config()

    # Kludge to pass to the handler init.

    class RequestClass:
        def __init__(self, rfile: BytesIO, wfile: BytesIO):
            self.rfile = rfile
            self.wfile = wfile

        def makefile(self, mode: str, bufsize):
            if mode[0] == "r":
                return self.rfile
            return self.wfile

    class HandlerClass(GopherRequestHandler):

        # Enable buffering (required to make the HandlerClass invoke RequestClass.makefile())
        rbufsize = -1
        wbufsize = -1

        def __init__(self, request, client_address, server: BaseServer):
            self.request = request
            self.client_address = client_address
            self.server = server
            self.setup()
            # This does everything in the base class up to handle()

        def handle(self):
            # Normally finish() gets called in the __init__, but because we are doing this
            # roundabout method of calling handle() from inside of unit tests, we want to make sure
            # that the server cleans up after itself.
            try:
                super().handle()
            finally:
                self.finish()

    server = get_testing_server(config)
    rhandler = HandlerClass(RequestClass(rfile, wfile), ("10.77.77.77", "7777"), server)
    return rhandler


def get_testing_protocol(request: str, config=None):
    config = config or get_config()

    rfile = BytesIO(request.encode(errors="surrogateescape"))
    # Pass fake rfile, wfile to get_testing_handler -- they'll be closed before
    # we can get the info, and some protocols need to read more from them.

    handler = get_testing_handler(BytesIO(), BytesIO(), config)
    # Now override.
    handler.rfile = rfile
    return ProtocolMultiplexer.getProtocol(
        rfile.readline().decode(errors="surrogateescape"),
        handler.server,
        handler,
        handler.rfile,
        handler.wfile,
        config,
    )


def supports_non_utf8_filenames() -> bool:
    """
    Test non-utf8 filenames only if the host operating system supports them.

    For example, MacOS HFS+ does not and will raise an OSError. These files
    are also a pain to work with in git which is why I'm creating it on the
    fly instead of committing it to the git repo.
    """
    try:
        # \xAE is the ® symbol in the ISO 8859-1 charset
        filename = os.path.join(TEST_DATA.encode(), b"\xAE.txt")
        with open(filename, "wb") as fp:
            fp.write(b"Hello, \xAE!")
    except OSError:
        return False
    else:
        return True
