import SocketServer
import re
import os, stat, os.path, mimetypes

class GopherRequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        request = self.rfile.readline()

        requestparts = request.split("\t")
        for i in range(0, len(requestparts)):
            requestparts[i] = requestparts[i].strip()

        if re.match('\./', requestparts[0]):    # Weed out ./ and ../
            return
        if re.match('//', requestparts[0]):     # Weed out //
            return

        if len(requestparts[0]) and requestparts[0][-1] == '/':
                requestparts[0] = requestparts[0][0:-1]
        if len(requestparts[0]) == 0 or requestparts[0][0] != '/':
            requestparts[0] = '/' + requestparts[0]

        path = self.server.config.get("serving", "root") + requestparts[0]

        protocols = [GopherPlusProtocol, GopherProtocol]
        for protocol in protocols:
            protohandler = protocol(path, requestparts, self.server,
                                    self.server.config)
            if (protohandler.canhandlerequest()):
                protohandler.handle(self.wfile)
                break

class GopherHandler:
    def __init__(self, protocol, path, request, server, config):
        self.path = path
        self.request = request
        self.config = config
        self.server = server
        self.protocol = protocol

class GopherDirHandler(GopherHandler):
    def write(self, wfile):
        files = os.listdir(self.path)
        files.sort()
        gopherbase = self.request
        if gopherbase == '/':
            gopherbase = ''
        fsbase = self.path
        if fsbase == '/':
            fsbase = ''

        for file in files:
            entry = GopherDirEntry(self.protocol, gopherbase + '/' + file,
                                   fsbase + '/' + file,
                                   self.server.mapping,
                                   self.server.defaulttype,
                                   self.server.server_name,
                                   self.server.server_port)
            wfile.write(str(entry) + "\r\n")

class GopherFileHandler(GopherHandler):
    def write(self, wfile):
        
        rfile = open(self.path, "rb")
        
        while 1:
            string = rfile.read(4096)
            if not len(string):
                break
            wfile.write(string)

class GopherDirEntry:
    def __init__(self, protocol,
                 gopherpath, fspath, mapping,
                 defaulttype = 'text/plain', defaulthost = 'localhost',
                 defaultport = 70):
        self.gopherpath = gopherpath
        self.fspath = fspath
        self.type = None
        self.name = os.path.basename(gopherpath)
        self.host = defaulthost
        self.port = defaultport
        self.mimetype = None
        self.size = -2
        self.populated = 0
        self.encoding = ''
        self.mapping = mapping
        self.language = ''
        self.protocol = protocol
        self.defaulttype = defaulttype

    def populate(self):
        if self.populated:
            return

        statval = os.stat(self.fspath)
        self.populated = 1
        self.size = statval[6]
        
        if stat.S_ISDIR(statval[0]):
            self.type = '1'
            self.mimetype = self.protocol.getmenutype()
            return

        type, encoding = mimetypes.guess_type(self.gopherpath)
        if type:
            self.mimetype = type

        if encoding:
            self.encoding = encoding
        else:
            self.encoding = ''

        if not self.mimetype:
            self.mimetype = self.defaulttype

        if self.mimetype and not self.type:
            self.type = 0
            for maprule in self.mapping:
                if re.match(maprule[0], self.mimetype):
                    self.type = maprule[1]
                    break

    def __str__(self):
        self.populate()
        return self.protocol.direntrystr(self)

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
            handler = GopherDirHandler(self, self.path, self.requestlist[0], self.server,
                                       self.server.config)
        else:
            handler = GopherFileHandler(self, self.path, self.requestlist[0], self.server,
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
                       
