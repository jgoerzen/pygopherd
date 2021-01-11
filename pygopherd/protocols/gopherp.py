# pygopherd -- Gopher-based protocol server in Python
# module: server entry point
# Copyright (C) 2021 Michael Lazar
# Copyright (C) 2002 John Goerzen
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

import io
import time
import typing
import unittest

from pygopherd import GopherExceptions
from pygopherd.protocols.rfc1436 import GopherProtocol


class GopherPlusProtocol(GopherProtocol):
    """Implementation of Gopher+ protocol.  Will handle Gopher+
    queries ONLY."""

    gopherpstring: str
    handlemethod: typing.Optional[str]

    def canhandlerequest(self):
        """We can handle the request IF:
        * It has more than one parameter in the request list
        * The second parameter is ! or starts with + or $"""
        if len(self.requestlist) < 2:
            return False
        if len(self.requestlist) == 2:
            self.gopherpstring = self.requestlist[1]
        elif len(self.requestlist) == 3:
            self.gopherpstring = self.requestlist[2]
            self.searchrequest = self.requestlist[1]
        else:
            return False  # Too many params.

        return (
            self.gopherpstring[0] == "+"
            or self.gopherpstring == "!"
            or self.gopherpstring[0] == "$"
        )

    def handle(self):
        """Handle Gopher+ request."""
        self.handlemethod = None
        if self.gopherpstring[0] == "+":
            self.handlemethod = "documentonly"
        elif self.gopherpstring == "!":
            self.handlemethod = "infoonly"
        elif self.gopherpstring[0] == "$":
            self.handlemethod = "gopherplusdir"

        try:
            handler = self.gethandler()
            self.log(handler)
            self.entry = handler.getentry()

            if self.handlemethod == "infoonly":
                self.wfile.write(b"+-2\r\n")
                self.wfile.write(
                    self.renderobjinfo(self.entry).encode(errors="surrogateescape")
                )
            else:
                handler.prepare()
                self.wfile.write(f"+{self.entry.getsize(-2)}\r\n".encode())
                if handler.isdir():
                    self.writedir(self.entry, handler.getdirlist())
                else:
                    handler.write(self.wfile)
        except GopherExceptions.FileNotFound as e:
            self.filenotfound(str(e))
        except IOError as e:
            GopherExceptions.log(e, self, None)
            self.filenotfound(e[1])

    def getsupportedblocknames(self, entry):
        # Return the always-supported values PLUS any extra ones for
        # this particular entry.
        return ["+INFO", "+ADMIN", "+VIEWS"] + [
            "+" + x for x in list(entry.geteadict().keys())
        ]

    def getallblocks(self, entry):
        retstr = ""
        for block in self.getsupportedblocknames(entry):
            retstr += self.getblock(block, entry)
        return retstr

    def getblock(self, block, entry):
        # If the entry has the block in its eadict, return that.
        # Otherwise, do our own thing.
        # Incoming block: +VIEWS
        blockname = block[1:].lower()

        if blockname.upper() in entry.geteadict():
            return (
                "+"
                + blockname.upper()
                + ":\r\n"
                + "".join(
                    [
                        " " + x + "\r\n"
                        for x in entry.getea(blockname.upper()).splitlines()
                    ]
                )
            )

        # Not in there -- look up a custom function.

        # Name: views
        funcname = "get" + blockname + "block"
        # Funcname: getviewsblock
        func = getattr(self, funcname)
        return func(entry)

    def getinfoblock(self, entry):
        return "+INFO: " + GopherProtocol.renderobjinfo(self, entry)

    def getadminblock(self, entry):
        retstr = "+ADMIN:\r\n"
        retstr += " Admin: "
        retstr += self.config.get("protocols.gopherp.GopherPlusProtocol", "admin")
        retstr += "\r\n"
        if entry.getmtime():
            retstr += " Mod-Date: "
            retstr += time.ctime(entry.getmtime())
            m = time.localtime(entry.getmtime())
            retstr += " <%04d%02d%02d%02d%02d%02d>\r\n" % (
                m[0],
                m[1],
                m[2],
                m[3],
                m[4],
                m[5],
            )
        return retstr

    def getviewsblock(self, entry):
        retstr = ""
        if entry.getmimetype():
            retstr += "+VIEWS:\r\n " + entry.getmimetype()
            if entry.getlanguage():
                retstr += " " + entry.getlanguage()
            retstr += ":"
            if entry.getsize() is not None:
                retstr += " <%dk>" % (entry.getsize() // 1024)
            retstr += "\r\n"
        return retstr

    def renderobjinfo(self, entry):
        if (
            entry.getmimetype("FAKE") == "application/gopher-menu"
            and entry.getgopherpsupport()
        ):
            entry.mimetype = "application/gopher+-menu"
        if self.handlemethod == "documentonly":
            # It's a Gopher+ request for a gopher0 menu entry.
            retstr = GopherProtocol.renderobjinfo(self, entry)
            return retstr
        else:
            return self.getallblocks(entry)

    def filenotfound(self, msg: str) -> None:
        self.wfile.write(b"--2\r\n")
        self.wfile.write(b"1 ")
        self.wfile.write(
            self.config.get("protocols.gopherp.GopherPlusProtocol", "admin").encode()
        )
        self.wfile.write(f"\r\n{msg}\r\n".encode(errors="surrogateescape"))

    def groksabstract(self) -> bool:
        return True


class URLGopherPlus(GopherPlusProtocol):
    def getsupportedblocknames(self, entry):
        return GopherPlusProtocol.getsupportedblocknames(self, entry) + ["+URL"]

    def geturlblock(self, entry):
        return "+URL: %s\r\n" % entry.geturl(
            self.server.server_name, self.server.server_port
        )


class TestGopherPlusProtocol(unittest.TestCase):
    def setUp(self):
        from pygopherd import testutil

        self.config = testutil.getconfig()
        self.logfile = testutil.getstringlogger()
        self.rfile = io.BytesIO()
        self.wfile = io.BytesIO()
        self.handler = testutil.gettestinghandler(self.rfile, self.wfile, self.config)

    def test_get_file(self):
        request = "/README\t+"
        protocol = GopherPlusProtocol(
            request,
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        self.assertEqual(protocol.gopherpstring, "+")
        self.assertEqual(protocol.handlemethod, "documentonly")

        response = self.wfile.getvalue().decode()

        expected = [
            "+142",
            "This directory contains data for the unit tests.",
            "",
            "Some tests are dependant upon the precise length of files; those files are",
            "added with -kb.",
            "",
        ]
        self.assertListEqual(response.splitlines(keepends=False), expected)

        # 142 byte filesize + 6 bytes for the "+142\r\n"
        self.assertTrue(len(response.encode()), 148)

    def test_file_not_found(self):
        protocol = GopherPlusProtocol(
            "/invalid-selector\t+",
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        self.assertEqual(protocol.gopherpstring, "+")
        self.assertEqual(protocol.handlemethod, "documentonly")

        response = self.wfile.getvalue().decode()

        expected = [
            "--2",
            "1 Unconfigured Pygopherd Admin <pygopherd@nowhere.nowhere>",
            "'/invalid-selector' does not exist (no handler found)",
        ]

        self.assertListEqual(response.splitlines(keepends=False), expected)

    def test_get_directory(self):
        protocol = GopherPlusProtocol(
            "/gopherplus\t+",
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        response = self.wfile.getvalue().decode()

        lines = response.splitlines(keepends=False)

        self.assertEqual(lines[0], "+-2")
        self.assertEqual(lines[1][-2:], "\t+")
        self.assertEqual(lines[2][-2:], "\t+")

    def test_get_file_info(self):
        protocol = GopherPlusProtocol(
            "/gopherplus/README\t!",
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        response = self.wfile.getvalue().decode()

        self.assertIn("+VIEWS:\r\n text/plain: <0k>", response)
        self.assertIn("+INFO: 0README\t", response)
        self.assertIn("+ADMIN:", response)
        self.assertIn("+3D:\r\n this is a gopher+ info attribute", response)

    def test_get_directory_info(self):
        protocol = GopherPlusProtocol(
            "/gopherplus\t$",
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        response = self.wfile.getvalue().decode()

        self.assertIn("+INFO: 0README\t", response)
        self.assertIn("+INFO: 0testfile\t", response)

    def test_ask_query(self):
        """
        Not supported by pygopherd :(
        """
