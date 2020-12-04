# pygopherd -- Gopher-based protocol server in Python
# module: serve up gopherspace via http
# $Id: http.py,v 1.21 2002/04/26 15:18:10 jgoerzen Exp $
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
import binascii
import html
import io
import re
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

import pygopherd.version
from pygopherd import GopherExceptions
from pygopherd.protocols.base import BaseGopherProtocol


class HTTPProtocol(BaseGopherProtocol):
    def canhandlerequest(self):
        self.requestparts = [arg.strip() for arg in self.request.split(" ")]
        return (
            len(self.requestparts) == 3
            and (self.requestparts[0] == "GET" or self.requestparts[0] == "HEAD")
            and self.requestparts[2][0:5] == "HTTP/"
        )

    def headerslurp(self):
        if hasattr(self.requesthandler, "pygopherd_http_slurped"):
            # Already slurped.
            self.httpheaders = self.requesthandler.pygopherd_http_slurped
            return
        # Slurp up remaining lines.
        self.httpheaders = {}
        while 1:
            line = self.rfile.readline().decode(errors="surrogateescape")
            if not len(line):
                break
            line = line.strip()
            if not len(line):
                break
            splitline = line.split(":", 1)
            if len(splitline) == 2:
                self.httpheaders[splitline[0].lower()] = splitline[1]
        self.requesthandler.pygopherd_http_slurped = self.httpheaders

    def handle(self):
        self.canhandlerequest()  # To get self.requestparts
        self.iconmapping = eval(
            self.config.get("protocols.http.HTTPProtocol", "iconmapping")
        )

        self.headerslurp()
        splitted = self.requestparts[1].split("?")
        self.selector = splitted[0]
        self.selector = urllib.parse.unquote(self.selector)

        self.selector = self.slashnormalize(self.selector)
        self.formvals = {}
        if len(splitted) >= 2:
            self.formvals = urllib.parse.parse_qs(splitted[1])

        if "searchrequest" in self.formvals:
            self.searchrequest = self.formvals["searchrequest"][0]

        icon = re.match("/PYGOPHERD-HTTPPROTO-ICONS/(.+)$", self.selector)
        if icon:
            iconname = icon.group(1)
            if iconname in icons:
                self.wfile.write(b"HTTP/1.0 200 OK\r\n")
                self.wfile.write(b"Last-Modified: Fri, 14 Dec 2001 21:19:47 GMT\r\n")
                self.wfile.write(b"Content-Type: image/gif\r\n\r\n")
                if self.requestparts[0] == "HEAD":
                    return
                self.wfile.write(binascii.unhexlify(icons[iconname]))
                return

        try:
            handler = self.gethandler()
            self.log(handler)
            self.entry = handler.getentry()
            handler.prepare()
            self.wfile.write(b"HTTP/1.0 200 OK\r\n")
            if self.entry.getmtime() is not None:
                gmtime = time.gmtime(self.entry.getmtime())
                mtime = time.strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime)
                self.wfile.write(f"Last-Modified: {mtime}\r\n".encode())
            mimetype = self.entry.getmimetype()
            mimetype = self.adjustmimetype(mimetype)
            self.wfile.write(f"Content-Type: {mimetype}\r\n\r\n".encode())
            if self.requestparts[0] == "GET":
                if handler.isdir():
                    self.writedir(self.entry, handler.getdirlist())
                else:
                    self.handlerwrite(self.wfile)
        except GopherExceptions.FileNotFound as e:
            self.filenotfound(str(e))
        except IOError as e:
            GopherExceptions.log(e, self, None)
            self.filenotfound(e[1])

    def handlerwrite(self, wfile):
        self.handler.write(wfile)

    def adjustmimetype(self, mimetype):
        if mimetype is None:
            return "text/plain"
        if mimetype == "application/gopher-menu":
            return "text/html"
        return mimetype

    def renderobjinfo(self, entry):
        # Decision time....
        if re.match("(/|)URL:", entry.getselector()):
            # It's a plain URL.  Make it that.
            url = re.match("(/|)URL:(.+)$", entry.getselector()).group(2)
        elif (not entry.gethost()) and (not entry.getport()):
            # It's a link to our own server.  Make it as such.  (relative)
            url = urllib.parse.quote(entry.getselector())
        else:
            # Link to a different server.  Make it a gopher URL.
            url = entry.geturl(self.server.server_name, 70)

        # OK.  Render.
        return self.getrenderstr(entry, url)

    def getrenderstr(self, entry, url):
        retstr = "<TR><TD>"
        retstr += self.getimgtag(entry)
        retstr += "</TD>\n<TD>&nbsp;"
        if entry.gettype() != "i" and entry.gettype() != "7":
            retstr += '<A HREF="%s">' % url
        retstr += "<TT>"
        if entry.getname() is not None:
            retstr += html.escape(entry.getname())
        else:
            retstr += html.escape(entry.getselector())
        retstr += "</TT>"
        if entry.gettype() != "i" and entry.gettype() != "7":
            retstr += "</A>"
        if entry.gettype() == "7":
            retstr += '<BR><FORM METHOD="GET" ACTION="%s">' % url
            retstr += '<INPUT TYPE="text" NAME="searchrequest" SIZE="30">'
            retstr += '<INPUT TYPE="submit" NAME="Submit" VALUE="Submit">'
            retstr += "</FORM>"
        retstr += '</TD><TD><FONT SIZE="-2">'
        if entry.getmimetype():
            subtype = re.search("/.+$", entry.getmimetype())
            if subtype:
                retstr += html.escape(subtype.group()[1:])
        retstr += "</FONT></TD></TR>\n"
        return retstr

    def renderdirstart(self, entry):
        retstr = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN" "http://www.w3.org/TR/REC-html40/loose.dtd">'
        retstr += "\n<HTML><HEAD><TITLE>Gopher"
        if self.entry.getname():
            retstr += ": " + html.escape(self.entry.getname())
        retstr += "</TITLE></HEAD><BODY>"
        if self.config.has_option("protocols.http.HTTPProtocol", "pagetopper"):
            retstr += re.sub(
                "GOPHERURL",
                self.entry.geturl(self.server.server_name, self.server.server_port),
                self.config.get("protocols.http.HTTPProtocol", "pagetopper"),
            )
        retstr += "<H1>Gopher"
        if self.entry.getname():
            retstr += ": " + html.escape(self.entry.getname())
        retstr += '</H1><TABLE WIDTH="100%" CELLSPACING="1" CELLPADDING="0">'
        return retstr

    def renderdirend(self, entry):
        retstr = '</TABLE><HR>\n[<A HREF="/">server top</A>]'
        retstr += ' [<A HREF="%s">view with gopher</A>]' % entry.geturl(
            self.server.server_name, self.server.server_port
        )
        retstr += '<BR>Generated by <A HREF="%s">%s</A>' % (
            pygopherd.version.homepage,
            pygopherd.version.productname,
        )
        return retstr + "\n</BODY></HTML>\n"

    def filenotfound(self, msg: str):
        self.wfile.write(b"HTTP/1.0 404 Not Found\r\n")
        self.wfile.write(b"Content-Type: text/html\r\n\r\n")
        self.wfile.write(
            b'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN" "http://www.w3.org/TR/REC-html40/loose.dtd">'
        )
        self.wfile.write(
            b"""\n<HTML><HEAD><TITLE>Selector Not Found</TITLE>
        <H1>Selector Not Found</H1>
        <TT>"""
        )
        self.wfile.write(html.escape(msg).encode(errors="surrogateescape"))
        self.wfile.write(b"</TT><HR>Pygopherd</BODY></HTML>\n")

    def getimgtag(self, entry):
        name = "generic.gif"
        if entry.gettype() in self.iconmapping:
            name = self.iconmapping[entry.gettype()]
        return '<IMG ALT=" * " SRC="%s" WIDTH="20" HEIGHT="22" BORDER="0">' % (
            "/PYGOPHERD-HTTPPROTO-ICONS/" + name
        )


icons = {
    "binary.gif": "47494638396114001600c20000ffffffccffffcccccc99999933333300000000000000000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000001002c000000001400160000036948babcf1301040ab9d24be590a105d210013a9715e07a8a509a16beab5ae14df6a41e8fc76839d5168e8b3182983e4a0e0038a6e1525d396931d97be2ad482a55a55c6eec429f484a7b4e339eb215fd138ebda1b7fb3eb73983bafee8b094a8182493b114387885309003b",
    "binhex.gif": "47494638396114001600c20000ffffffccffff99999966666633333300000000000000000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000001002c000000001400160000036948babcf1301040ab9d24be59baefc0146adce78555068914985e2b609e0551df9b3c17ba995b408a602828e48a2681856894f44cc1628e07a42e9b985d14ab1b7c9440a9131c0c733b229bb5222ecdb6bfd6da3cd5d29d688a1aee2c97db044482834336113b884d09003b",
    "folder.gif": "47494638396114001600c20000ffffffffcc99ccffff99663333333300000000000000000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000002002c000000001400160000035428badcfe30ca4959b9f8ce12baef45c47d64a629c5407a6a8906432cc72b1c8ef51a13579e0f3c9c8f05ec0d4945e171673cb2824e2234da495261569856c5ddc27882d46c3c2680c3e6b47acd232c4cf08c3b01003b",
    "image3.gif": "47494638396114001600e30000ffffffff3333ccffff9999996600003333330099cc00993300336600000000000000000000000000000000000000000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000002002c0000000014001600000479b0c849a7b85814c0bbdf45766d5e49861959762a3a76442c132ae0aa44a0ef49d1ff2f4e6ea74b188f892020c70c3007d04152b3aa46a7adcaa42355160ee0f041d5a572bee23017cb1abbbf6476d52a0720ee78fc5a8930f8ff06087b66768080832a7d8a81818873744a8f8805519596503e19489b9c5311003b",
    "sound1.gif": "47494638396114001600c20000ffffffff3333ccffffcccccc99999966000033333300000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000002002c000000001400160000036b28badcfe3036c34290ea1c61558f07b171170985c0687e0d9a729e77693401dc5bd7154148fcb6db6b77e1b984c20d4fb03406913866717a842aa7d22af22acd120cdf6fd2d49cd10e034354871518de06b43a17334de42a36243e187d4a7b1a762c7b140b8418898a0b09003b",
    "text.gif": "47494638396114001600c20000ffffffccffff99999933333300000000000000000000000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000001002c000000001400160000035838babcf1300c40ab9d23be693bcf11d75522b88dd7057144eb52c410cf270abb6e8db796e00b849aadf20b4a6ebb1705281c128daca412c03c3a7b50a4f4d9bc5645dae9f78aed6e975932baebfc0e7ef0b84f1691da8d09003b",
    "generic.gif": "47494638396114001600c20000ffffffccffff99999933333300000000000000000000000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000001002c000000001400160000035038babcf1300c40ab9d23be693bcf11d75522b88dd705892831b8f08952446d13f24c09bc804b3a4befc70a027c39e391a8ac2081cd65d2f82c06ab5129b4898d76b94c2f71d02b9b79afc86dcdfe2500003b",
    "blank.gif": "47494638396114001600a10000ffffffccffff00000000000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000001002c00000000140016000002138c8fa9cbed0fa39cb4da8bb3debcfb0f864901003b",
}


class TestHTTPProtocol(unittest.TestCase):
    def setUp(self):
        from pygopherd import testutil

        self.config = testutil.getconfig()
        self.logfile = testutil.getstringlogger()
        self.rfile = io.BytesIO(b"Accept:text/plain\nHost:localhost.com\n\n")
        self.wfile = io.BytesIO()
        self.handler = testutil.gettestinghandler(self.rfile, self.wfile, self.config)

    def test_http_handler(self):
        request = "GET / HTTP/1.1"
        protocol = HTTPProtocol(
            request,
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        self.assertEqual(protocol.httpheaders["host"], "localhost.com")

        response = self.wfile.getvalue().decode()
        self.assertIn("HTTP/1.0 200 OK", response)
        self.assertIn("Content-Type: text/html", response)
        self.assertIn('SRC="/PYGOPHERD-HTTPPROTO-ICONS/text.gif"', response)

    def test_http_handler_icon(self):
        request = "GET /PYGOPHERD-HTTPPROTO-ICONS/text.gif HTTP/1.1"
        protocol = HTTPProtocol(
            request,
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        response = self.wfile.getvalue()
        self.assertIn(b"HTTP/1.0 200 OK", response)
        self.assertIn(b"Content-Type: image/gif", response)
        self.assertIn(b"This art is in the public domain", response)

    def test_http_handler_not_found(self):
        request = "GET /invalid-filename HTTP/1.1"
        protocol = HTTPProtocol(
            request,
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        response = self.wfile.getvalue().decode()
        self.assertIn("HTTP/1.0 404 Not Found", response)
        self.assertIn("Content-Type: text/html", response)
        self.assertIn(
            "&#x27;/invalid-filename&#x27; does not exist (no handler found)", response
        )

    def test_http_handler_search(self):
        request = "GET /?searchrequest=foo%20bar HTTP/1.1"
        protocol = HTTPProtocol(
            request,
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        self.assertEqual(protocol.searchrequest, "foo bar")
