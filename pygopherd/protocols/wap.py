# pygopherd -- Gopher-based protocol server in Python
# module: serve up gopherspace via wap
# $Id: http.py,v 1.21 2002/04/26 15:18:10 jgoerzen Exp $
# Copyright (C) 2003 John Goerzen
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

import cgi
import io
import re
from io import StringIO

from .http import HTTPProtocol

accesskeys = "1234567890#*"
wmlheader = """<?xml version="1.0"?>
<!DOCTYPE wml PUBLIC "-//WAPFORUM//DTD WML 1.1//EN"
"http://www.wapforum.org/DTD/wml_1.1.xml">
<wml>
"""


class WAPProtocol(HTTPProtocol):
    # canhandlerequest inherited
    def canhandlerequest(self):
        ishttp = HTTPProtocol.canhandlerequest(self)
        if not ishttp:
            return 0

        waptop = self.config.get("protocols.wap.WAPProtocol", "waptop")
        self.waptop = waptop
        if self.requestparts[1].startswith(waptop):
            # If it starts with waptop, *guaranteed* to be wap.
            self.requestparts[1] = self.requestparts[1][len(waptop) :]
            return 1

        self.headerslurp()

        # See if we can auto-detect a WAP browser.
        if "accept" not in self.httpheaders:
            return 0

        if not re.search("[, ]text/vnd.wap.wml", self.httpheaders["accept"]):
            return 0

        # By now, we know that it lists WML in accept.  Let's try a few
        # more things.

        for tryitem in ["x-wap-profile", "x-up-devcap-max-pdu"]:
            if tryitem in self.httpheaders:
                return 1

        return 0

    def adjustmimetype(self, mimetype):
        self.needsconversion = 0
        if mimetype is None or mimetype == "text/plain":
            self.needsconversion = 1
            return "text/vnd.wap.wml"
        if mimetype == "application/gopher-menu":
            return "text/vnd.wap.wml"
        return mimetype

    def getrenderstr(self, entry, url):
        global accesskeys
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
            thisname = cgi.escape(entry.getname())
        else:
            thisname = cgi.escape(entry.getselector())
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

    def renderdirstart(self, entry):
        global wmlheader
        self.accesskeyidx = 0
        self.postfieldidx = 0
        retval = wmlheader
        title = "Gopher"
        if self.entry.getname():
            title = cgi.escape(self.entry.getname())
        retval += '<card id="index" title="%s" newcontext="true">' % cgi.escape(title)

        retval += "\n<p>\n"
        retval += "<b>%s</b><br/>\n" % cgi.escape(title)
        return retval

    def renderdirend(self, entry):
        return "</p>\n</card>\n</wml>\n"

    def handlerwrite(self, wfile: io.BufferedIOBase):
        global wmlheader
        if not self.needsconversion:
            self.handler.write(wfile)
            return
        fakefile = StringIO()
        self.handler.write(fakefile)
        fakefile.seek(0)
        wfile.write(wmlheader.encode())
        wfile.write(b'<card id="index" title="Text File" newcontext="true">\n')
        wfile.write(b"<p>\n")
        while 1:
            line = fakefile.readline()
            if not len(line):
                break
            line = line.rstrip()
            if len(line):
                wfile.write(cgi.escape(line).encode(errors="surrogateescape") + b"\n")
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
        wfile.write(cgi.escape(msg).encode(errors="surrogateescape") + b"\n")
        wfile.write(b"</p>\n</card>\n</wml>\n")
