import SocketServer
import re
import os, stat, os.path, mimetypes, handlers

class GopherProtocol:
    """Implementation of basic protocol.  Will always return valid."""
    def __init__(self, path, requestlist, server, config):
        self.path = path
        self.requestlist = requestlist
        self.server = server
        self.config = config

    def canhandlerequest(self):
        return 1

    def getmenutype(self):
        return 'application/gopher-menu'

    def handle(self, wfile):
        print "Handling Gopher0 request."
        if os.path.isdir(self.path):
            handler = handlers.GopherDirHandler(self, self.path, self.requestlist[0], self.server,
                                       self.server.config)
        else:
            handler = handlers.GopherFileHandler(self, self.path, self.requestlist[0], self.server,
                                        self.server.config)

        handler.write(wfile)

    def direntrystr(self, direntry):
        return direntry.type + \
               direntry.name + "\t" + \
               direntry.gopherpath + "\t" + \
               direntry.host + "\t" + \
               str(direntry.port)

class GopherEnhancedProtocol(GopherProtocol):
    def direntrystr(self, direntry):
        return direntry.type + \
               direntry.name + "\t" + \
               direntry.gopherpath + "\t" + \
               direntry.host + "\t" + \
               str(direntry.port) + "\t" + \
               str(direntry.size) + "\t" + \
               direntry.mimetype + "\t" + \
               direntry.encoding + "\t" + \
               direntry.language

class GopherPlusProtocol(GopherProtocol):
    def canhandlerequest(self):
        return len(self.requestlist) > 1 and \
               (self.requestlist[1][0] == '+' or \
               self.requestlist[1] == '!' or \
               self.requestlist[1][0] == '$')

    def handle(self, wfile):
        print "Handling Gopher+ request."
        if self.requestlist[1][0] == '+':
            self.gopherplusdirs = 0
            wfile.write("+-2\r\n")
            GopherProtocol.handle(self, wfile)
        elif self.requestlist[1] == '!':
            self.gopherplusdirs = 1
            wfile.write("+-2\r\n")
            wfile.write(self.getinfo())
        elif self.requestlist[1][0] == '$':
            self.gopherplusdirs = 1
            wfile.write("+-2\r\n")
            GopherProtocol.handle(self, wfile)

    def getinfo(self):
        return self.fileinfo(self.requestlist[0], self.path)

    def fileinfo(self, request, path):
        entry = GopherDirEntry(self, request, path, self.server.mapping,
                               self.server.defaulttype,
                               self.server.server_name,
                               self.server.server_port)
        return str(entry)

    def getmenutype(self):
        if self.gopherplusdirs:
            return 'application/gopher+-menu'
        else:
            return 'application/gopher-menu'

    def direntrystr(self, direntry):
        if self.gopherplusdirs:
            retstr = \
                   "+INFO: " + GopherProtocol.direntrystr(self, direntry) + "\t+" \
                   "\r\n" + \
                   "+VIEWS:\r\n " + \
                   direntry.mimetype
            if (direntry.language):
                retstr += " " + direntry.language
            retstr += \
                   (": <%dk>" % (direntry.size / 1024) )
            return retstr
        else:
            return GopherProtocol.direntrystr(self, direntry) + "\t+"
                       
