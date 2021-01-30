import io
import tempfile
import unittest

from pygopherd import testutil
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.file import CompressedFileHandler, FileHandler


class TestFileHandler(unittest.TestCase):
    def setUp(self):
        self.config = testutil.get_config()
        self.vfs = VFS_Real(self.config)
        self.selector = "/testfile.txt"
        self.protocol = testutil.get_testing_protocol(self.selector, config=self.config)
        self.stat_result = self.vfs.stat(self.selector)

    def test_file_handler(self):
        handler = FileHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )

        self.assertTrue(handler.canhandlerequest())
        self.assertFalse(handler.isdir())

        entry = handler.getentry()
        self.assertEqual(entry.mimetype, "text/plain")
        self.assertEqual(entry.type, "0")

        wfile = io.BytesIO()
        handler.write(wfile)
        data = wfile.getvalue().decode()
        self.assertEqual(data, "Test\n")

    @unittest.skipUnless(
        testutil.supports_non_utf8_filenames(),
        reason="Filesystem does not support non-utf8 filenames.",
    )
    def test_file_handler_non_utf8(self):
        self.selector = b"/\xAE.txt".decode(errors="surrogateescape")

        handler = FileHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )

        self.assertTrue(handler.canhandlerequest())
        self.assertFalse(handler.isdir())

        entry = handler.getentry()
        self.assertEqual(entry.mimetype, "text/plain")
        self.assertEqual(entry.type, "0")

        wfile = io.BytesIO()
        handler.write(wfile)
        data = wfile.getvalue()
        self.assertEqual(data, b"Hello, \xAE!")


class TestCompressedFileHandler(unittest.TestCase):
    def setUp(self):
        self.config = testutil.get_config()
        self.vfs = VFS_Real(self.config)
        self.selector = "/testfile.txt.gz"
        self.protocol = testutil.get_testing_protocol(self.selector, config=self.config)
        self.stat_result = self.vfs.stat(self.selector)

        self.config.set(
            "handlers.file.CompressedFileHandler", "decompressors", "{'gzip' : 'zcat'}"
        )

    def test_compressed_file_handler(self):
        handler = CompressedFileHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )

        self.assertTrue(handler.canhandlerequest())
        self.assertFalse(handler.isdir())

        entry = handler.getentry()
        self.assertEqual(entry.mimetype, "text/plain")
        self.assertEqual(entry.type, "0")

        with tempfile.TemporaryFile("rb") as wfile:
            handler.write(wfile)
            wfile.seek(0)
            data = wfile.read()

        self.assertEqual(data, b"Test\n")
