import configparser
import errno
import io
import os
import socket
import socketserver
import ssl
import struct
import traceback
import typing

from pygopherd import GopherExceptions
from pygopherd.protocols import ProtocolMultiplexer


class BaseServer(socketserver.BaseServer):
    server_name: str
    server_port: int

    allow_reuse_address: bool = True

    def __init__(
        self,
        config: configparser.ConfigParser,
        *args: typing.Any,
        context: typing.Optional[ssl.SSLContext] = None,
        **kwargs: typing.Any
    ):
        self.config = config
        self.context = context
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

    def wrap_socket(self, sock: socket.SocketType) -> socket.SocketType:
        """
        Check the first byte of the TCP request for a TLS handshake by looking
        for the SYN (\x16) and wrap the connection in a TLS context.

        This will wait for the first byte to be received through the socket,
        therefore it should be treated as *blocking* and should only be invoked
        from inside of the handler thread/forked process.
        """
        if self.context:
            if sock.recv(1, socket.MSG_PEEK) == b"\x16":
                return self.context.wrap_socket(sock, server_side=True)
        return sock


class ForkingTCPServer(BaseServer, socketserver.ForkingTCPServer):
    def process_request(
        self, request: socket.SocketType, client_address: typing.Tuple[str, int]
    ) -> None:
        """
        Copied directly from the parent class with the addition of the call to
        self.wrap_socket() inside of the child process.
        """
        pid = os.fork()
        if pid:
            # Parent process
            if self.active_children is None:
                self.active_children = set()
            self.active_children.add(pid)
            self.close_request(request)
            return
        else:
            status = 1
            try:
                request = self.wrap_socket(request)
                self.finish_request(request, client_address)
                status = 0
            except Exception:
                self.handle_error(request, client_address)
            finally:
                try:
                    self.shutdown_request(request)
                finally:
                    os._exit(status)


class ThreadingTCPServer(BaseServer, socketserver.ThreadingTCPServer):
    def process_request_thread(
        self, request: socket.SocketType, client_address: typing.Tuple[str, int]
    ) -> None:
        """
        Copied directly from the parent class with the addition of the call to
        self.wrap_socket() inside of the child thread.
        """
        try:
            request = self.wrap_socket(request)
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


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
