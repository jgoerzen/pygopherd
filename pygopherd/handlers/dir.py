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
        self.fsbase = self.getfspath()
        if self.fsbase == '/':
            self.fsbase = ''                 # Avoid dup slashes
        self.selectorbase = self.selector
        if self.selectorbase == '/':
            self.selectorbase = ''           # Avoid dup slashes

    def write(self, wfile):
        ignorepatt = self.config.get("handlers.dir.DirHandler", "ignorepatt")

        startstr = self.protocol.renderdirstart(self.entry)
        if (startstr):
            wfile.write(startstr)

        for file in self.files:
            # Skip files we're ignoring.
            if re.search(ignorepatt, self.selectorbase + '/' + file):
                continue
            
            fileentry = gopherentry.GopherEntry(self.selectorbase + '/' + file,
                                          self.config)
            fileentry.populatefromfs(self.fsbase + '/' + file)
            wfile.write(self.protocol.renderobjinfo(fileentry))

        endstr = self.protocol.renderdirend(self.entry)
        if (endstr):
            wfile.write(endstr)

            
