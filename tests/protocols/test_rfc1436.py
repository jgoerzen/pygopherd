import typing
import unittest
from io import BytesIO

from pygopherd import testutil
from pygopherd.handlers import HandlerMultiplexer
from pygopherd.protocols.rfc1436 import GopherProtocol


class RFC1436TestCase(unittest.TestCase):
    def setUp(self):
        self.config = testutil.get_config()
        self.rfile = BytesIO(b"/testfile.txt\n")
        self.wfile = BytesIO()
        self.logfile = testutil.get_string_logger()
        self.handler = testutil.get_testing_handler(self.rfile, self.wfile, self.config)
        self.server = self.handler.server
        self.proto = GopherProtocol(
            "/testfile.txt\n",
            self.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

    def inject_handler(self, handler_name: str, index: typing.Optional[int] = None):
        """
        Add a handler to the HandlerMultiplexer in the configuration.
        """
        handlerlist = self.config.get("handlers.HandlerMultiplexer", "handlers")
        handlers = [x.strip() for x in handlerlist.strip("[] \n").split(",")]
        if index is not None:
            handlers.insert(index, handler_name)
        else:
            handlers.append(handler_name)

        handlerlist = "[" + ",".join(handlers) + "]"
        self.config.set("handlers.HandlerMultiplexer", "handlers", handlerlist)

        # Clear the cache
        HandlerMultiplexer.handlers = None

    def testcanhandlerequest(self):
        assert self.proto.canhandlerequest()
        proto = GopherProtocol(
            "/testfile.txt\tsearch\n",
            self.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )
        assert proto.canhandlerequest()
        self.assertEqual(proto.selector, "/testfile.txt")
        self.assertEqual(proto.searchrequest, "search")

    def testrenderobjinfo(self):
        expected = "0testfile.txt\t/testfile.txt\t%s\t%d\t+\r\n" % (
            self.server.server_name,
            self.server.server_port,
        )
        self.assertEqual(
            self.proto.renderobjinfo(self.proto.gethandler().getentry()), expected
        )

    def testhandle_file(self):
        self.proto.handle()
        self.assertEqual(
            self.logfile.getvalue(),
            "10.77.77.77 [GopherProtocol/FileHandler]: /testfile.txt\n",
        )
        self.assertEqual(self.wfile.getvalue(), b"Test\n")

    def testhandle_file_zipped(self):
        self.config.set("handlers.ZIP.ZIPHandler", "enabled", "true")
        self.inject_handler("ZIP.ZIPHandler", index=0)

        self.proto = GopherProtocol(
            "/testdata.zip/pygopherd/ziponly\n",
            self.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )
        self.proto.handle()
        self.assertEqual(self.wfile.getvalue(), b"ZIPonly\n")
        self.config.set("handlers.ZIP.ZIPHandler", "enabled", "false")

    def testhandle_dir_abstracts(self):
        proto = GopherProtocol(
            "", self.server, self.handler, self.rfile, self.wfile, self.config
        )
        proto.handle()
        self.assertEqual(proto.selector, "/")
        self.assertEqual(
            self.logfile.getvalue(), "10.77.77.77 [GopherProtocol/UMNDirHandler]: /\n"
        )
        # Try to make this easy on us to fix.
        actuallines = (
            self.wfile.getvalue().decode(errors="surrogateescape").splitlines()
        )
        expectedlines = [
            "iThis is the abstract for the testdata directory.\tfake\t(NULL)\t0",
            "iThis is the abstract\tfake\t(NULL)\t0",
            "ifor testfile.txt.gz\tfake\t(NULL)\t0",
        ]

        for line in expectedlines:
            self.assertIn(line, actuallines)

        # Make sure proper line endings are present.
        self.assertEqual(
            "\r\n".join(actuallines) + "\r\n",
            self.wfile.getvalue().decode(errors="surrogateescape"),
        )

    def testhandle_dir_noabstract(self):
        self.config.set("pygopherd", "abstract_headers", "off")
        self.config.set("pygopherd", "abstract_entries", "off")
        proto = GopherProtocol(
            "", self.server, self.handler, self.rfile, self.wfile, self.config
        )
        proto.handle()
        actuallines = (
            self.wfile.getvalue().decode(errors="surrogateescape").splitlines()
        )
        expectedlines = [
            "iThis is the abstract for the testdata directory.\tfake\t(NULL)\t0",
            "iThis is the abstract\tfake\t(NULL)\t0",
            "ifor testfile.txt.gz\tfake\t(NULL)\t0",
        ]

        for line in expectedlines:
            self.assertNotIn(line, actuallines)
