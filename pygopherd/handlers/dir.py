import SocketServer
import re
import os, stat, os.path, mimetypes, protocols, gopherentry
import handlers, handlers.base

class DirHandler(handlers.base.BaseHandler):
    def canhandlerequest(self):
        """We can handle the request if it's for a directory."""
        return os.path.isdir(self.getfspath())

    def getentry(self):
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            self.entry.populatefromfs(self.getfspath())
        return self.entry

    def prepare(self):
        self.files = os.listdir(self.getfspath())
        self.files.sort()

    def write(self, wfile):
        selectorbase = self.selector
        if selectorbase == '/':
            selectorbase = ''           # Avoid dup slashes
        fsbase = self.getfspath()
        if fsbase == '/':
            fsbase = ''                 # Avoid dup slashes

        ignorepatt = self.config.get("handlers.dir.DirHandler", "ignorepatt")

        for file in self.files:
            # Skip files we're ignoring.
            if re.search(ignorepatt, selectorbase + '/' + file):
                continue
            
            fileentry = gopherentry.GopherEntry(selectorbase + '/' + file,
                                          self.config)
            fileentry.populatefromfs(fsbase + '/' + file)
            wfile.write(self.protocol.renderobjinfo(fileentry))
            
