import SocketServer
import re
import os, stat, os.path, mimetypes, protocols

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

        protos = [protocols.GopherPlusProtocol, protocols.GopherProtocol]
        for protocol in protos:
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

