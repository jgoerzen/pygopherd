import imp
import io
import re
import unittest
import stat

from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.virtual import Virtual


class PYGHandler(Virtual):
    def canhandlerequest(self) -> bool:
        if not isinstance(self.vfs, VFS_Real):
            return False
        if not (
            self.statresult
            # Is it a regular file?
            and stat.S_ISREG(self.statresult[stat.ST_MODE])
            # Is it executable?
            and (stat.S_IMODE(self.statresult[stat.ST_MODE]) & stat.S_IXOTH)
            and re.search(r"\.pyg$", self.getselector())
        ):
            return False
        with self.vfs.open(self.getselector(), "r") as modf:
            self.module = imp.load_module(
                "PYGHandler", modf, self.getfspath(), ("", "", imp.PY_SOURCE)
            )
        self.pygclass = self.module.PYGMain
        self.pygobject = self.pygclass(
            self.selector,
            self.searchrequest,
            self.protocol,
            self.config,
            self.statresult,
        )
        return self.pygobject.isrequestforme()

    def prepare(self):
        return self.pygobject.prepare()

    def getentry(self):
        return self.pygobject.getentry()

    def isdir(self):
        return self.pygobject.isdir()

    def getdirlist(self):
        return self.pygobject.getdirlist()

    def write(self, wfile):
        self.pygobject.write(wfile)


class PYGBase(Virtual):
    pass


class TestPYGHandler(unittest.TestCase):
    def setUp(self) -> None:
        from pygopherd import testutil

        self.config = testutil.getconfig()
        self.vfs = VFS_Real(self.config)
        self.selector = "/testfile.pyg"
        self.protocol = testutil.gettestingprotocol(self.selector, config=self.config)
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
