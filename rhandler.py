import SocketServer
import re
import os, stat, os.path, mimetypes

gopherplushack = "+-1\r\n" + \
"+INFO: 1Main menu (non-gopher+)\t/\tsam.forinstance.com\t1170\r\n" + \
"+ADMIN:\r\n" + \
" Admin: Server Administrator\r\n" + \
" Server: \r\n" + \
"+VIEWS:\r\n" + \
" application/gopher+-menu: <512b>\r\n" + \
"+ABSTRACT:\r\n" + \
" Foo.\r\n"

class GopherRequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        request = self.rfile.readline()
        tabindex = request.find("\t")
        if (tabindex != -1):
            self.wfile.write(gopherplushack)
            return

        request = request.strip()

        if re.match('\./', request):    # Weed out ./ and ../
            return
        if re.match('//', request):     # Weed out //
            return

        if len(request) and request[-1] == '/':
                request = request[0:-1]
        if len(request) == 0 or request[0] != '/':
            request = '/' + request

        path = self.server.config.get("serving", "root") + request

        handler = None

        if os.path.isdir(path):
            handler = GopherDirHandler(path, request, self.server,
                                       self.server.config)
        else:
            handler = GopherFileHandler(path, request, self.server,
                                        self.server.config)

        handler.write(self.wfile)
        

class GopherHandler:
    def __init__(self, path, request, server, config):
        self.path = path
        self.request = request
        self.config = config
        self.server = server

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
            entry = GopherDirEntry(gopherbase + '/' + file,
                                   fsbase + '/' + file,
                                   self.server.mapping,
                                   self.server.defaulttype,
                                   'enhanced',
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
    def __init__(self, gopherpath, fspath, mapping, protocol = 'enhanced',
                 defaulttype = 'text/plain', defaulthost = 'localhost',
                 defaultport = 70):
        self.gopherpath = gopherpath
        self.fspath = fspath
        self.type = '0'
        self.name = os.path.basename(gopherpath)
        self.host = defaulthost
        self.port = defaultport
        self.mimetype = defaulttype
        self.size = -2
        self.populated = 0
        self.encoding = ''
        self.mapping = mapping
        self.language = ''
        self.protocol = protocol

    def populate(self):
        if self.populated:
            return

        statval = os.stat(self.fspath)
        self.populated = 1
        self.size = statval[6]
        
        if stat.S_ISDIR(statval[0]):
            self.type = '1'
            self.mimetype = 'application/gopher-menu'
            return

        type, encoding = mimetypes.guess_type(self.gopherpath)
        print "Mime result for", self.gopherpath, type, encoding
        if type:
            self.mimetype = type

        if encoding:
            self.encoding = encoding
        else:
            self.encoding = ''

        for maprule in self.mapping:
            if re.match(maprule[0], self.mimetype):
                self.type = maprule[1]
                break

    def __str__(self):
        self.populate()
        return self.type + \
               self.name + "\t" + \
               self.gopherpath + "\t" + \
               self.host + "\t" + \
               str(self.port) + "\t" + \
               str(self.size) + "\t" + \
               self.mimetype + "\t" + \
               self.encoding + "\t" + \
               self.language

