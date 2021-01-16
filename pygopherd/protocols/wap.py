from __future__ import annotations

import html
import io
import re
import typing

from pygopherd.protocols.http import HTTPProtocol

if typing.TYPE_CHECKING:
    from pygopherd.protocols.base import GopherEntry


accesskeys = "1234567890#*"
wmlheader = """<?xml version="1.0"?>
<!DOCTYPE wml PUBLIC "-//WAPFORUM//DTD WML 1.1//EN"
"http://www.wapforum.org/DTD/wml_1.1.xml">
<wml>
"""


class WAPProtocol(HTTPProtocol):
    def canhandlerequest(self) -> bool:
        ishttp = HTTPProtocol.canhandlerequest(self)
        if not ishttp:
            return False

        waptop = self.config.get("protocols.wap.WAPProtocol", "waptop")
        self.waptop = waptop
        if self.requestparts[1].startswith(waptop):
            # If it starts with waptop, *guaranteed* to be wap.
            self.requestparts[1] = self.requestparts[1][len(waptop) :]
            return True

        self.headerslurp()

        # See if we can auto-detect a WAP browser.
        if "accept" not in self.httpheaders:
            return False

        if not re.search("[, ]text/vnd.wap.wml", self.httpheaders["accept"]):
            return False

        # By now, we know that it lists WML in accept.  Let's try a few
        # more things.

        for tryitem in ["x-wap-profile", "x-up-devcap-max-pdu"]:
            if tryitem in self.httpheaders:
                return True

        return False

    def adjustmimetype(self, mimetype: typing.Optional[str]) -> str:
        self.needsconversion = 0
        if mimetype is None or mimetype == "text/plain":
            self.needsconversion = 1
            return "text/vnd.wap.wml"
        if mimetype == "application/gopher-menu":
            return "text/vnd.wap.wml"
        return mimetype

    def getrenderstr(self, entry: GopherEntry, url: str) -> str:
        if url.startswith("/"):
            url = self.waptop + url
        retstr = ""
        if not entry.gettype() in ["i", "7"]:
            if self.accesskeyidx < len(accesskeys):
                retstr += '%s <a accesskey="%s" href="%s">' % (
                    accesskeys[self.accesskeyidx],
                    accesskeys[self.accesskeyidx],
                    url,
                )
                self.accesskeyidx += 1
            else:
                retstr += '<a href="%s">' % url
        if entry.getname() is not None:
            thisname = html.escape(entry.getname())
        else:
            thisname = html.escape(entry.getselector())
        retstr += thisname
        if not entry.gettype() in ["i", "7"]:
            retstr += "</a>"
        if entry.gettype() == "7":
            retstr += "<br/>\n"
            retstr += '  <input name="sr%d"/>\n' % self.postfieldidx
            retstr += "<anchor>Go\n"
            # retstr += '<do type="accept">\n'
            retstr += '  <go method="get" href="%s">\n' % url  # .replace('%', '%25')
            retstr += (
                '    <postfield name="searchrequest" value="$(sr%d)"/>\n'
                % self.postfieldidx
            )
            # retstr += '    <postfield name="text" value="1234"/>\n'
            retstr += "  </go>\n"
            # retstr += '</do>\n'
            retstr += "</anchor>\n"
        retstr += "<br/>\n"
        self.postfieldidx += 1
        return retstr

    def renderdirstart(self, entry: GopherEntry) -> str:
        self.accesskeyidx = 0
        self.postfieldidx = 0
        retval = wmlheader
        title = "Gopher"
        if self.entry.getname():
            title = html.escape(self.entry.getname())
        retval += '<card id="index" title="%s" newcontext="true">' % html.escape(title)

        retval += "\n<p>\n"
        retval += "<b>%s</b><br/>\n" % html.escape(title)
        return retval

    def renderdirend(self, entry: GopherEntry) -> str:
        return "</p>\n</card>\n</wml>\n"

    def handlerwrite(self, wfile: typing.BinaryIO) -> None:
        if not self.needsconversion:
            self.handler.write(wfile)
            return

        fakefile = io.BytesIO()
        self.handler.write(fakefile)
        fakefile.seek(0)
        wfile.write(wmlheader.encode())
        wfile.write(b'<card id="index" title="Text File" newcontext="true">\n')
        wfile.write(b"<p>\n")
        while 1:
            line = fakefile.readline().decode(errors="surrogateescape")
            if not len(line):
                break
            line = line.rstrip()
            if len(line):
                wfile.write(html.escape(line).encode(errors="surrogateescape") + b"\n")
            else:
                wfile.write(b"</p>\n<p>")
        wfile.write(b"</p>\n</card>\n</wml>\n")

    def filenotfound(self, msg):
        wfile = self.wfile
        wfile.write(b"HTTP/1.0 200 Not Found\r\n")
        wfile.write(b"Content-Type: text/vnd.wap.wml\r\n\r\n")
        wfile.write(wmlheader.encode())
        wfile.write(b'<card id="index" title="404 Error" newcontext="true">\n')
        wfile.write(b"<p><b>Gopher Error</b></p><p>\n")
        wfile.write(html.escape(msg).encode(errors="surrogateescape") + b"\n")
        wfile.write(b"</p>\n</card>\n</wml>\n")
