import SocketServer
import re
import os, stat, os.path, mimetypes, protocols, handlers

class GopherRequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        request = self.rfile.readline()

        protos = [protocols.GopherPlusProtocol, protocols.GopherProtocol]
        for protocol in protos:
            protohandler = protocol(path, requestparts, self.server,
                                    self.server.config)
            if (protohandler.canhandlerequest()):
                protohandler.handle(self.rfile, self.wfile)
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
