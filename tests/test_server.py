import os
import socket
import socketserver
import ssl
import threading
import typing
import unittest

from pygopherd import testutil
from pygopherd.server import BaseServer, ForkingTCPServer, ThreadingTCPServer

crt_file = os.path.join(testutil.TEST_DATA, "demo.crt")
key_file = os.path.join(testutil.TEST_DATA, "demo.key")

context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(crt_file, key_file)


class EchoHandler(socketserver.StreamRequestHandler):
    def handle(self):
        data = self.rfile.readline()
        self.wfile.write(data)


class ServerTestCase(unittest.TestCase):

    server_class: typing.Type[BaseServer]
    server: BaseServer
    thread: threading.Thread

    @classmethod
    def setUpClass(cls):
        """
        Spin up a test server in a separate thread.
        """
        config = testutil.get_config()

        server_address = ("localhost", 0)
        cls.server = cls.server_class(
            config, server_address, EchoHandler, context=context
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)


class ThreadingTCPServerTestCase(ServerTestCase):
    server_class = ThreadingTCPServer

    def test_send_data(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(self.server.server_address)
            sock.sendall(b"Hello World\n")
            self.assertEqual(sock.recv(4096), b"Hello World\n")

    def test_send_data_tls(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            with ssl.wrap_socket(sock) as ssock:
                ssock.connect(self.server.server_address)
                ssock.sendall(b"Hello World\n")
                self.assertEqual(ssock.recv(4096), b"Hello World\n")


class ForkingTCPServerTestCase(ServerTestCase):
    server_class = ForkingTCPServer

    def test_send_data(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(self.server.server_address)
            sock.sendall(b"Hello World\n")
            self.assertEqual(sock.recv(4096), b"Hello World\n")

    def test_send_data_tls(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            with ssl.wrap_socket(sock) as ssock:
                ssock.connect(self.server.server_address)
                ssock.sendall(b"Hello World\n")
                self.assertEqual(ssock.recv(4096), b"Hello World\n")
