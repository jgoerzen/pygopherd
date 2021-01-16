import tempfile
import unittest

from pygopherd import testutil
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.scriptexec import ExecHandler


class TestExecHandler(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
        self.vfs = VFS_Real(self.config)
        # The "hello" will be sent as an additional script argument. Multiple
        # query arguments can be provided using " " as the separator.
        self.selector = "/pygopherd/cgitest.sh?hello"
        self.protocol = testutil.gettestingprotocol(self.selector, config=self.config)
        self.stat_result = None

    def test_exec_handler(self):
        handler = ExecHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )

        self.assertTrue(handler.isrequestforme())

        entry = handler.getentry()
        self.assertEqual(entry.mimetype, "text/plain")
        self.assertEqual(entry.type, "0")
        self.assertEqual(entry.name, "cgitest.sh")
        self.assertEqual(entry.selector, "/pygopherd/cgitest.sh")

        # The test script will print $REQUEST and exit
        with tempfile.TemporaryFile(mode="w+") as wfile:
            handler.write(wfile)
            wfile.seek(0)
            output = wfile.read()
            self.assertEqual(output, "hello from /pygopherd/cgitest.sh\n")
