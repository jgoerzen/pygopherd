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

from http import HTTPProtocol
import cgi, re

accesskeys = '1234567890#*'

class WAPProtocol(HTTPProtocol):
    # canhandlerequest inherited
    def canhandlerequest(self):
        ishttp = HTTPProtocol.canhandlerequest(self)
        if not ishttp:
            return 0

        waptop = self.config.get("protocols.wap.WAPProtocol",
                                 "waptop")
        if self.requestparts[1].startswith(waptop):
            self.requestparts[1] = self.requestparts[1][len(waptop):]
            return 1
        else:
            return 0

    def adjustmimetype(self, mimetype):
        if mimetype == None:
            return 'text/plain'
        if mimetype == 'application/gopher-menu':
            return 'text/vnd.wap.wml'
        return mimetype

    def getrenderstr(self, entry, url):
        global accesskeys
        retstr = ''
        if not entry.gettype() in ['i', '7']:
            if self.accesskeyidx < len(accesskeys):
                retstr += '%s <a accesskey="%s" href="%s">' % \
                          (accesskeys[self.accesskeyidx],
                           accesskeys[self.accesskeyidx],
                           url)
                self.accesskeyidx += 1
            else:
                retstr += '<a href="%s">' % url
        if entry.getname() != None:
            retstr += cgi.escape(entry.getname())
        else:
            retstr += cgi.escape(etry.getselector())
        if not entry.gettype() in ['i', '7']:
            retstr += '</a>'
        if entry.gettype() == '7':
            retstr += '<do type="accept">\n'
            retstr += '  <input type="text" name="sr%d" size="30>\n' % \
                      self.postfieldidx
            retstr += '  <go href="%s">\n' % url
            retstr += '    <postfield name="searchrequest" value="sr%d"/>\n' % \
                      self.postfieldidx
            retstr += '  </go>\n'
            retstr += '</do>\n'
        retstr += "<br/>\n"
        self.postfieldidx += 1
        return retstr

    def renderdirstart(self, entry):
        self.accesskeyidx = 0
        self.postfieldidx = 0
        retval = """<?xml version="1.0"?>
<!DOCTYPE wml PUBLIC "-//WAPFORUM//DTD WML 1.1//EN"
"http://www.wapforum.org/DTD/wml_1.1.xml">
<wml>
"""
        title = 'Gopher'
        if self.entry.getname():
            title = cgi.escape(self.entry.getname())
        retval += '<card id="index" title="%s" newcontext="true">' % \
                  cgi.escape(title)
        
        retval += "\n<p>\n"
        retval += "<b>%s</b><br/>\n" % cgi.escape(title)
        return retval

    def renderdirend(self, entry):
        return "</p>\n</card>\n</wml>\n"
    
