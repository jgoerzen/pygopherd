import SocketServer
import re
import os, stat, os.path, mimetypes, handlers, protocols
import protocols.base

class GopherProtocol(protocols.base.BaseGopherProtocol):
    """Implementation of basic protocol.  Will handle every query."""
    def canhandlerequest(self):
        return 1

    def renderobjinfo(self, entry):
        retval = entry.gettype() + \
                 entry.getname() + "\t" + \
                 entry.getselector() + "\t" + \
                 entry.gethost(default = self.server.server_name) + "\t" + \
                 str(entry.getport(default = self.server.server_port))
        if entry.getgopherpsupport():
            return retval + "\t+\r\n"
        else:
            return retval + "\r\n"

