import SocketServer
import re
import os, stat, os.path, mimetypes, handlers, protocols

class GopherPlusProtocol(protocols.rfc1436.GopherProtocol):
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

        handler = self.gethandler()
        self.entry = handler.getentry()
        
        if self.handlemethod == 'infoonly':
            self.wfile.write("+-2\r\n")
            self.wfile.write(self.renderobjinfo(entry))
        else:
            self.wfile.write("+" + entry.getsize(-2) + "\r\n")
            entry.write(self, self.wfile)

    def renderobjinfo(self, entry):
        if entry.getmimetype() == 'application/gopher-menu':
            entry.mimetype = 'application/gopher+-menu'
        if self.handlemethod = 'documentonly':
            # It's a Gopher+ request for a gopher0 menu entry.
            retstr = protocols.rfc1436.GopherProtocol.renderobjinfo(self, entry)
            # Strip off the \r\n from the rfc1436 string.  Add our gopher+
            # thing and return.
            retstr = retstr.rstrip()
            retstr += "\t+\r\n"
            return retstr
        else:
            retstr = "+INFO: " + \
                     protocols.rfc1436.GopherProtocol.renderobjinfo(self, entry) + \
                     "+VIEWS:\r\n " + \
                     entry.getmimetype()
            if (entry.getlanguage()):
                retstr += " " + entry.getlanguage()
            retstr += \
                   ": <%d>\r\n" % entry.getsize(-2)
            return retstr
