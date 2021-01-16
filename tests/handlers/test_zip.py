from __future__ import annotations

import configparser
import io
import os.path
import stat
import unittest

from pygopherd import testutil
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.ZIP import VFS_Zip, ZIPHandler


class TestVFSZip(unittest.TestCase):
    def setUp(self):
        self.config = configparser.ConfigParser()
        self.config.add_section("pygopherd")
        self.config.set("pygopherd", "root", os.path.abspath("testdata"))
        self.real = VFS_Real(self.config)
        self.z = VFS_Zip(self.config, self.real, "/testdata.zip")
        self.z2 = VFS_Zip(self.config, self.real, "/testdata2.zip")
        self.zs = VFS_Zip(self.config, self.real, "/symlinktest.zip")

    def test_listdir(self):
        m1 = self.z.listdir("/testdata.zip")
        m2 = self.z2.listdir("/testdata2.zip")

        m1.sort()
        m2.sort()

        self.assertIn("pygopherd", m1)
        self.assertEqual(m1, m2)
        self.assertEqual(
            m1,
            [
                ".abstract",
                "README",
                "pygopherd",
                "testarchive.tar",
                "testarchive.tar.gz",
                "testarchive.tgz",
                "testfile.txt",
                "testfile.txt.gz",
                "testfile.txt.gz.abstract",
            ],
        )

        m1 = self.z.listdir("/testdata.zip/pygopherd")
        m2 = self.z2.listdir("/testdata2.zip/pygopherd")

        m1.sort()
        m2.sort()

        self.assertEqual(m1, m2 + ["ziponly"])
        self.assertEqual(m1, ["pipetest.sh", "pipetestdata", "ziponly"])

    def test_iswritable(self):
        self.assertFalse(self.z.iswritable("/testdata.zip"))
        self.assertFalse(self.z.iswritable("/testdata.zip/README"))
        self.assertFalse(self.z.iswritable("/testdata.zip/pygopherd"))

    def test_getfspath(self):
        self.assertEqual(self.z.getfspath("/testdata.zip/foo"), "foo")
        self.assertEqual(self.z.getfspath("/testdata.zip"), "")
        self.assertEqual(self.z.getfspath("/testdata.zip/foo/bar"), "foo/bar")

    def test_stat(self):
        self.assertRaises(OSError, self.z.stat, "/testdata.zip/nonexistant")
        self.assertTrue(stat.S_ISDIR(self.z.stat("/testdata.zip")[0]))
        self.assertTrue(stat.S_ISREG(self.z.stat("/testdata.zip/README")[0]))
        self.assertTrue(stat.S_ISDIR(self.z.stat("/testdata.zip/pygopherd")[0]))
        self.assertTrue(stat.S_ISDIR(self.z2.stat("/testdata2.zip/pygopherd")[0]))
        self.assertTrue(
            stat.S_ISREG(self.z.stat("/testdata.zip/pygopherd/pipetest.sh")[0])
        )
        self.assertTrue(
            stat.S_ISREG(self.z2.stat("/testdata2.zip/pygopherd/pipetest.sh")[0])
        )

    def test_isdir(self):
        self.assertFalse(self.z.isdir("/testdata.zip/README"))
        self.assertFalse(self.z2.isdir("/testdata.zip/README"))
        self.assertTrue(self.z.isdir("/pygopherd"))
        self.assertTrue(self.z.isdir("/testdata.zip/pygopherd"))
        self.assertTrue(self.z2.isdir("/testdata2.zip/pygopherd"))
        self.assertTrue(self.z.isdir("/testdata.zip"))

    def test_isfile(self):
        self.assertTrue(self.z.isfile("/testdata.zip/README"))
        self.assertFalse(self.z.isfile("/testdata.zip"))
        self.assertFalse(self.z.isfile("/testdata.zip/pygopherd"))
        self.assertFalse(self.z2.isfile("/testdata2.zip/pygopherd"))
        self.assertTrue(self.z.isfile("/testdata.zip/.abstract"))

    def test_exists(self):
        self.assertTrue(self.z.exists("/README"))
        self.assertFalse(self.z.exists("/READMEnonexistant"))
        self.assertTrue(self.z.exists("/testdata.zip"))
        self.assertTrue(self.z.exists("/testdata.zip/README"))
        self.assertTrue(self.z.exists("/testdata.zip/pygopherd"))
        self.assertTrue(self.z2.exists("/testdata2.zip/pygopherd"))

    def test_symlinkexists(self):
        self.assertTrue(self.zs.exists("/symlinktest.zip/real.txt"))
        self.assertTrue(self.zs.exists("/symlinktest.zip/linked.txt"))
        self.assertTrue(self.zs.exists("/symlinktest.zip/subdir/linktosubdir2"))

    def test_symlinkgetfspath(self):
        self.assertEqual(self.zs.getfspath("/symlinktest.zip"), "")
        self.assertEqual(self.zs.getfspath("/symlinktest.zip/real.txt"), "real.txt")
        self.assertEqual(self.zs.getfspath("/symlinktest.zip/subdir"), "subdir")
        self.assertEqual(
            self.zs.getfspath("/symlinktest.zip/subdir2/real2.txt"),
            "subdir2/real2.txt",
        )

    def test_symlink_listdir(self):
        m1 = self.zs.listdir("/symlinktest.zip")
        m1.sort()

        self.assertEqual(
            m1, ["linked.txt", "linktosubdir", "real.txt", "subdir", "subdir2"]
        )

        tm2 = [
            "linked2.txt",
            "linkedabs.txt",
            "linkedrel.txt",
            "linktoself",
            "linktosubdir2",
        ]
        m2 = self.zs.listdir("/symlinktest.zip/subdir")
        m2.sort()
        self.assertEqual(m2, tm2)

        m2 = self.zs.listdir("/symlinktest.zip/linktosubdir")
        m2.sort()
        self.assertEqual(m2, tm2)

        self.assertRaises(OSError, self.zs.listdir, "/symlinktest.zip/nonexistant")
        self.assertRaises(OSError, self.zs.listdir, "/symlinktest.zip/real.txt")
        self.assertRaises(
            OSError, self.zs.listdir, "/symlinktest.zip/linktosubdir/linkedrel.txt"
        )

        m2 = self.zs.listdir("/symlinktest.zip/linktosubdir/linktoself/linktoself")

        m2.sort()
        self.assertEqual(m2, tm2)

        m3 = self.zs.listdir("/symlinktest.zip/linktosubdir/linktoself/linktosubdir2")
        self.assertEqual(m3, ["real2.txt"])

    def test_symlink_open(self):
        realtxt = b"Test.\n"
        real2txt = b"asdf\n"

        # Establish basis for tests is correct.
        self.assertEqual(self.zs.open("/symlinktest.zip/real.txt").read(), realtxt)
        self.assertEqual(
            self.zs.open("/symlinktest.zip/subdir2/real2.txt").read(), real2txt
        )

        # Now, run the tests.
        self.assertEqual(
            self.zs.open("/symlinktest.zip/subdir/linked2.txt").read(), real2txt
        )
        self.assertEqual(
            self.zs.open("/symlinktest.zip/linktosubdir/linked2.txt").read(), real2txt
        )
        self.assertEqual(
            self.zs.open("/symlinktest.zip/linktosubdir/linkedabs.txt").read(), realtxt
        )
        self.assertEqual(
            self.zs.open(
                "/symlinktest.zip/linktosubdir/linktoself/linktoself/linktoself/linkedrel.txt"
            ).read(),
            realtxt,
        )
        self.assertEqual(
            self.zs.open("/symlinktest.zip/subdir/linktosubdir2/real2.txt").read(),
            real2txt,
        )

        self.assertRaises(IOError, self.zs.open, "/symlinktest.zip")
        self.assertRaises(IOError, self.zs.open, "/symlinktest.zip/subdir")
        self.assertRaises(IOError, self.zs.open, "/symlinktest.zip/linktosubdir")
        self.assertRaises(IOError, self.zs.open, "/symlinktest.zip/subdir/linktoself")
        self.assertRaises(
            IOError,
            self.zs.open,
            "/symlinktest.zip/linktosubdir/linktoself/linktosubdir2",
        )

    def test_symlink_isdir(self):
        self.assertTrue(self.zs.isdir("/symlinktest.zip/subdir"))
        self.assertTrue(self.zs.isdir("/symlinktest.zip/linktosubdir"))
        self.assertFalse(self.zs.isdir("/symlinktest.zip/linked.txt"))
        self.assertFalse(self.zs.isdir("/symlinktest.zip/real.txt"))

        self.assertTrue(self.zs.isdir("/symlinktest.zip/subdir/linktoself"))
        self.assertTrue(self.zs.isdir("/symlinktest.zip/subdir/linktosubdir2"))
        self.assertTrue(
            self.zs.isdir("/symlinktest.zip/linktosubdir/linktoself/linktosubdir2")
        )
        self.assertFalse(self.zs.isdir("/symlinktest.zip/nonexistant"))
        self.assertFalse(self.zs.isdir("/symlinktest.zip/subdir/linkedrel.txt"))
        self.assertTrue(self.zs.isdir("/symlinktest.zip"))

    def test_symlink_isfile(self):
        self.assertTrue(self.zs.isfile("/symlinktest.zip/real.txt"))
        self.assertFalse(self.zs.isfile("/symlinktest.zip"))
        self.assertFalse(self.zs.isfile("/symlinktest.zip/subdir"))
        self.assertFalse(self.zs.isfile("/symlinktest.zip/linktosubdir"))
        self.assertTrue(self.zs.isfile("/symlinktest.zip/linktosubdir/linkedrel.txt"))
        self.assertTrue(self.zs.isfile("/symlinktest.zip/linktosubdir/linked2.txt"))
        self.assertTrue(
            self.zs.isfile("/symlinktest.zip/subdir/linktoself/linktosubdir2/real2.txt")
        )
        self.assertFalse(
            self.zs.isfile("/symlinktest.zip/subdir/linktoself/linktosubdir2/real.txt")
        )

    def test_open(self):
        self.assertRaises(IOError, self.z.open, "/testdata.zip/pygopherd")
        self.assertRaises(IOError, self.z2.open, "/testdata2.zip/pygopherd")
        self.assertRaises(IOError, self.z2.open, "/testdata.zip/pygopherd")

        self.assertTrue(self.z.open("/testdata.zip/.abstract"))

        self.assertEqual(self.z.open("/testdata.zip/testfile.txt").read(), b"Test\n")
        shouldbe = b"Word1\nWord2\nWord3\n"
        self.assertEqual(
            self.z.open("/testdata.zip/pygopherd/pipetestdata").read(), shouldbe
        )
        self.assertEqual(
            self.z2.open("/testdata2.zip/pygopherd/pipetestdata").read(), shouldbe
        )


class TestZipHandler(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
        self.vfs = VFS_Real(self.config)
        self.selector = "/testdata.zip"
        self.protocol = testutil.gettestingprotocol(self.selector, config=self.config)
        self.stat_result = self.vfs.stat(self.selector)

        self.config.set("handlers.ZIP.ZIPHandler", "enabled", "true")

    def test_zip_handler_directory(self):
        handler = ZIPHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )
        self.assertTrue(handler.canhandlerequest())

        handler.prepare()
        self.assertTrue(handler.isdir())

        entry = handler.getentry()
        self.assertEqual(entry.selector, "/testdata.zip")
        self.assertEqual(entry.name, "testdata.zip")
        self.assertEqual(entry.mimetype, "application/gopher-menu")

        entries = handler.getdirlist()
        self.assertEqual(len(entries), 7)

        self.assertEqual(entries[0].selector, "/testdata.zip/README")
        self.assertEqual(entries[0].name, "README")
        self.assertEqual(entries[0].mimetype, "text/plain")

    def test_zip_handler_file(self):
        self.selector = "/testdata.zip/README"

        handler = ZIPHandler(
            self.selector, "", self.protocol, self.config, None, self.vfs
        )
        self.assertTrue(handler.canhandlerequest())

        handler.prepare()
        self.assertFalse(handler.isdir())

        entry = handler.getentry()
        self.assertEqual(entry.selector, "/testdata.zip/README")
        self.assertEqual(entry.name, "README")
        self.assertEqual(entry.mimetype, "text/plain")

        wfile = io.BytesIO()
        handler.write(wfile)
        data = wfile.getvalue()
        assert data.startswith(b"This directory contains data for the unit tests.")
