import configparser
import errno
import io
import socket
import socketserver
import struct
import traceback

from pygopherd import GopherExceptions
from pygopherd.protocols import ProtocolMultiplexer


class BaseServer(socketserver.BaseServer):
    server_name: str
    server_port: int

    allow_reuse_address = True

    def __init__(self, config: configparser.ConfigParser, *args, **kwargs):
        self.config = config
        super().__init__(*args, **kwargs)

    def server_bind(self) -> None:
        super().server_bind()

        if self.config.has_option("pygopherd", "timeout"):
            timeout = struct.pack("ll", int(self.config.get("pygopherd", "timeout")), 0)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, timeout)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDTIMEO, timeout)

        host, port = self.socket.getsockname()
        if self.config.has_option("pygopherd", "servername"):
            self.server_name = self.config.get("pygopherd", "servername")
        else:
            self.server_name = socket.getfqdn(host)

        if self.config.has_option("pygopherd", "advertisedport"):
            self.server_port = self.config.getint("pygopherd", "advertisedport")
        else:
            self.server_port = port


class ForkingTCPServer(BaseServer, socketserver.ForkingTCPServer):
    pass


class ThreadingTCPServer(BaseServer, socketserver.ThreadingTCPServer):
    pass


class GopherRequestHandler(socketserver.StreamRequestHandler):

    rfile: io.BytesIO
    wfile: io.BytesIO
    server: BaseServer

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
