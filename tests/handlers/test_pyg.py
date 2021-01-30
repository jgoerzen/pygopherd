import io
import unittest

from pygopherd import testutil
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.pyg import PYGHandler


class TestPYGHandler(unittest.TestCase):
    def setUp(self):
        self.config = testutil.get_config()
        self.vfs = VFS_Real(self.config)
        self.selector = "/testfile.pyg"
        self.protocol = testutil.get_testing_protocol(self.selector, config=self.config)
        self.stat_result = self.vfs.stat("/testfile.pyg")

    def test_pyg_handler(self):
        handler = PYGHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )

        self.assertTrue(handler.canhandlerequest())
        self.assertFalse(handler.isdir())

        entry = handler.getentry()
        self.assertEqual(entry.selector, "/testfile.pyg")

        wfile = io.BytesIO()
        handler.write(wfile)
        self.assertEqual(wfile.getvalue(), b"hello world!")
