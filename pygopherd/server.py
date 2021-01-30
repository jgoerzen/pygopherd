import configparser
import socket
import socketserver
import struct


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
            self.server_name = self.socket.getfqdn(host)

        if self.config.has_option("pygopherd", "advertisedport"):
            self.server_port = self.config.getint("pygopherd", "advertisedport")
        else:
            self.server_port = port


class ForkingTCPServer(BaseServer, socketserver.ForkingTCPServer):
    pass


class ThreadingTCPServer(BaseServer, socketserver.ThreadingTCPServer):
    pass
