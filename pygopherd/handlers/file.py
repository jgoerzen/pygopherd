import SocketServer
import re
import os, stat, os.path, mimetypes, protocols, handlers, gopherentry
import handlers.base

class FileHandler(handlers.base.BaseHandler):
    def canhandlerequest(self):
        """We can handle the request if it's for a file."""
        return os.path.isfile(self.getfspath())

    def getentry(self):
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            self.entry.populatefromfs(self.getfspath())
        return self.entry

    def prepare(self):
        self.rfile = open(self.getfspath(), "rb")

    def write(self, wfile):
        while 1:
            string = self.rfile.read(4096)
            if not len(string):
                break
            wfile.write(string)
        self.rfile.close()
        self.rfile = None
