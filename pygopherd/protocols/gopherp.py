# pygopherd -- Gopher-based protocol server in Python
# module: server entry point
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import SocketServer
import re
import os, stat, os.path, mimetypes, time
from pygopherd import handlers, protocols, GopherExceptions
from pygopherd.protocols.rfc1436 import GopherProtocol

class GopherPlusProtocol(GopherProtocol):
    """Implementation of Gopher+ protocol.  Will handle Gopher+
    queries ONLY."""

    def canhandlerequest(self):
        """We can handle the request IF:
           * It has more than one parameter in the request list
           * The second parameter is ! or starts with + or $"""
        return len(self.requestlist) > 1 and \
               (self.requestlist[1][0] == '+' or \
               self.requestlist[1] == '!' or \
               self.requestlist[1][0] == '$')
    
    def handle(self):
        """Handle Gopher+ request."""
        self.handlemethod = None
        if self.requestlist[1][0] == '+':
            self.handlemethod = 'documentonly'
        elif self.requestlist[1] == '!':
            self.handlemethod = 'infoonly'
        elif self.requestlist[1][0] == '$':
            self.handlemethod = 'gopherplusdir'

        try:
            handler = self.gethandler()
            self.entry = handler.getentry()
            
            if self.handlemethod == 'infoonly':
                self.wfile.write("+-2\r\n")
                self.wfile.write(self.renderobjinfo(self.entry))
            else:
                handler.prepare()
                self.wfile.write("+" + str(self.entry.getsize(-2)) + "\r\n")
                handler.write(self.wfile)
        except GopherExceptions.FileNotFound, e:
            self.filenotfound(str(e))
        except IOError, e:
            self.filenotfound(e[1])

    def getsupportedblocknames(self):
        return ['+INFO', '+ADMIN', '+VIEWS']

    def getallblocks(self, entry):
        retstr = ''
        for block in self.getsupportedblocknames():
            retstr += self.getblock(block, entry)
        return retstr

    def getblock(self, block, entry):
        # Incoming block: +VIEWS
        blockname = block[1:].lower()
        # Name: views
        funcname = "get" + blockname + "block"
        # Funcname: getviewsblock
        func = getattr(self, funcname)
        return func(entry)

    def getinfoblock(self, entry):
        return "+INFO: " + \
               GopherProtocol.renderobjinfo(self, entry)

    def getadminblock(self, entry):
        retstr = "+ADMIN:\r\n"
        retstr += " Admin: "
        retstr += self.config.get("protocols.gopherp.GopherPlusProtocol",
                                  "admin")
        retstr += "\r\n"
        if entry.getmtime():
            retstr += " Mod-Date: "
            retstr += time.ctime(entry.getmtime())
            m = time.localtime(entry.getmtime())
            retstr += " <%04d%02d%02d%02d%02d%02d>\r\n" % \
                      (m[0], m[1], m[2], m[3], m[4], m[5])
        return retstr

    def getviewsblock(self, entry):
        retstr = ''
        if entry.getmimetype():
            retstr += "+VIEWS:\r\n " + entry.getmimetype()
            if (entry.getlanguage()):
                retstr += " " + entry.getlanguage()
            retstr += ":"
            if (entry.getsize() != None):
                retstr += " <%dk>" % (entry.getsize() / 1024)
            retstr += "\r\n"
        return retstr

    def renderobjinfo(self, entry):
        if entry.getmimetype('FAKE') == 'application/gopher-menu' and \
               entry.getgopherpsupport():
            entry.mimetype = 'application/gopher+-menu'
        if self.handlemethod == 'documentonly':
            # It's a Gopher+ request for a gopher0 menu entry.
            retstr = GopherProtocol.renderobjinfo(self, entry)
            return retstr
        else:
            return self.getallblocks(entry)

    def filenotfound(self, msg):
        self.wfile.write("--2\r\n")
        self.wfile.write("1 ")
        self.wfile.write(self.config.get("protocols.gopherp.GopherPlusProtocol", "admin"))
        self.wfile.write("\r\n" + msg + "\r\n")

class URLGopherPlus(GopherPlusProtocol):
    def getsupportedblocknames(self):
        return GopherPlusProtocol.getsupportedblocknames(self) + \
               ['+URL']

    def geturlblock(self, entry):
        return "+URL: %s\r\n" % entry.geturl(self.server.server_name,
                                            self.server.server_port)
