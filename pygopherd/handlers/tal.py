# pygopherd -- Gopher-based protocol server in Python
# module: TAL file handling.
# Copyright (C) 2002, 2003 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from __future__ import annotations

import html
import io
import os
import typing
import unittest

from pygopherd import gopherentry
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.file import FileHandler

try:
    from simpletal import simpleTAL, simpleTALES

    talavailable = True
except ImportError:
    talavailable = False


class TALLoader:
    def __init__(self, vfs: VFS_Real, path: str):
        self.vfs = vfs
        self.path = path

    def getpath(self) -> str:
        return self.path

    def getparent(self) -> TALLoader:
        if self.path == "/":
            return self
        else:
            return self.__class__(self.vfs, os.path.dirname(self.path))

    def getchildrennames(self) -> typing.List[str]:
        return self.vfs.listdir(self.path)

    def __getattr__(self, key):
        fq = os.path.join(self.path, key)
        if self.vfs.isfile(fq + ".html.tal"):
            with self.vfs.open(
                fq + ".html.tal", "r", errors="replace"
            ) as template_file:
                compiled = simpleTAL.compileHTMLTemplate(template_file)
            return compiled
        elif self.vfs.isdir(fq):
            return self.__class__(self.vfs, fq)
        else:
            raise AttributeError("Key %s not found in %s" % (key, self.path))


class RecursiveTALLoader(TALLoader):
    def __getattr__(self, key):
        if self.path == "/":
            # Already at the top -- can't recurse.
            return TALLoader.__getattr__(self, key)
        try:
            return TALLoader.__getattr__(self, key)
        except AttributeError:
            return self.getparent().__getattr__(key)


class TALFileHandler(FileHandler):

    talbasename: str
    allowpythonpath: int

    def canhandlerequest(self):
        """We can handle the request if it's for a file ending with .thtml."""
        canhandle = FileHandler.canhandlerequest(self) and self.getselector().endswith(
            ".tal"
        )
        if not canhandle:
            return False
        self.talbasename = self.getselector()[:-4]
        self.allowpythonpath = 1
        if self.config.has_option("handlers.tal.TALFileHandler", "allowpythonpath"):
            self.allowpythonpath = self.config.getboolean(
                "handlers.tal.TALFileHandler", "allowpythonpath"
            )
        return True

    def getentry(self):
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            self.entry.populatefromfs(self.getselector(), self.statresult, vfs=self.vfs)
            assert self.entry.getencoding() == "tal.TALFileHandler"
            # Remove the TAL encoding and revert to default.
            self.entry.mimetype = self.entry.getencodedmimetype()
            self.entry.encodedmimetype = None
            self.entry.realencoding = self.entry.encoding
            self.entry.encoding = None
            self.entry.type = self.entry.guesstype()

        return self.entry

    def write(self, wfile):
        context = simpleTALES.Context(allowPythonPath=self.allowpythonpath)
        context.addGlobal("selector", self.getselector())
        context.addGlobal("handler", self)
        context.addGlobal("entry", self.getentry())
        context.addGlobal("talbasename", self.talbasename)
        context.addGlobal("allowpythonpath", self.allowpythonpath)
        context.addGlobal("protocol", self.protocol)
        context.addGlobal("root", TALLoader(self.vfs, "/"))
        context.addGlobal("rroot", RecursiveTALLoader(self.vfs, "/"))
        dirname = os.path.dirname(self.getselector())
        context.addGlobal("dir", TALLoader(self.vfs, dirname))
        context.addGlobal("rdir", RecursiveTALLoader(self.vfs, dirname))

        # SimpleTAL doesn't support reading from binary files
        with self.vfs.open(self.getselector(), "r", errors="replace") as rfile:
            template = simpleTAL.compileHTMLTemplate(rfile)
        template.expand(context, wfile)


TEST_TEMPLATE = """
<html>
<head>
<title>TAL Test</title>
</head>
<body>
My selector is: <b>{selector}</b><br>
My MIME type is: <b>text/html</b><br>
Another way of getting that is: <b>text/html</b><br>
Gopher type is: <b>h</b><br>
My handler is: <b>{handler}</b><br>
My protocol is: <b>{protocol}</b><br>
Python path enabling status: <b>1</b><br>
My vfs is: <b>{vfs}</b><br>
Math: <b>4</b>
</body>
</html>
"""


class TestTALHandler(unittest.TestCase):
    def setUp(self) -> None:
        from pygopherd import initialization, testutil

        self.config = testutil.getconfig()
        self.vfs = VFS_Real(self.config)
        self.selector = "/talsample.html.tal"
        self.protocol = testutil.gettestingprotocol(self.selector, config=self.config)
        self.stat_result = self.vfs.stat(self.selector)

        # Initialize the custom mimetypes encoding map
        initialization.initlogger(self.config, "")
        initialization.initmimetypes(self.config)

    def test_tal_available(self):
        self.assertTrue(talavailable)

    def test_tal_handler(self):
        handler = TALFileHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )

        self.assertTrue(handler.canhandlerequest())

        entry = handler.getentry()
        self.assertEqual(entry.mimetype, "text/html")
        self.assertEqual(entry.type, "h")

        wfile = io.BytesIO()
        handler.write(wfile)
        rendered_data = wfile.getvalue().decode()

        expected_data = TEST_TEMPLATE.format(
            selector=handler.selector,
            handler=html.escape(str(handler)),
            protocol=html.escape(str(self.protocol)),
            vfs=html.escape(str(self.vfs)),
        )

        self.assertEqual(rendered_data.strip(), expected_data.strip())
