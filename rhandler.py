import SocketServer
import re
import os, stat, os.path

class GopherRequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        request = self.rfile.readline().strip()
        if re.match('\./', request):    # Weed out ./ and ../
            return
        if re.match('//', request):     # Weed out //
            return
        request = re.sub("\t.*", '', request) # Weed out tab+stuff
        if len(request) and request[-1] == '/':
                request = request[0:-1]
        if len(request) == 0 or request[0] != '/':
            request = '/' + request

        path = self.server.config.get("serving", "root") + '/' + request

        handler = None

        if os.path.isdir(path):
            handler = GopherDirHandler(path, request, self.server.config)
        else:
            handler = GopherFileHandler(path, request, self.server.config)

        handler.write(self.wfile)
        

class GopherHandler:
    def __init__(self, path, request, config):
        self.path = path
        self.request = request
        self.config = config


class GopherDirHandler(GopherHandler):
    def write(self, wfile):
        pass

class GopherFileHandler(GopherHandler):
    def write(self, wfile):
        
        rfile = open(self.path, "rb")
        
        while 1:
            string = rfile.read(4096)
            if not len(string):
                break
            wfile.write(string)
