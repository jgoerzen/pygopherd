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

    def prep_initfiles(self):
        "Initialize the list of files.  Ignore the files we're suppoed to."
        self.files = []
        dirfiles = os.listdir(self.getfspath())
        ignorepatt = self.config.get("handlers.dir.DirHandler", "ignorepatt")
        for file in dirfiles:
            if not re.search(ignorepatt, self.selectorbase + '/' + file):
                self.files.append(file)

    def prep_entries(self):
        "Generate entries from the list."

        self.fileentries = []
        for file in self.files:
            fileentry = gopherentry.GopherEntry(self.selectorbase + '/' + file,
                                          self.config)
            fileentry.populatefromfs(self.fsbase + '/' + file)
            self.fileentries.append(fileentry)

    def prepare(self):
        # Initialize some variables.

        self.fsbase = self.getfspath()
        if self.fsbase == '/':
            self.fsbase = ''                 # Avoid dup slashes
        self.selectorbase = self.selector
        if self.selectorbase == '/':
            self.selectorbase = ''           # Avoid dup slashes        
            
        self.prep_initfiles()

        # Sort the list.
        self.files.sort()

        self.prep_entries()

    def write(self, wfile):
        startstr = self.protocol.renderdirstart(self.entry)
        if (startstr):
            wfile.write(startstr)

        for fileentry in self.fileentries:
            wfile.write(self.protocol.renderobjinfo(fileentry))

        endstr = self.protocol.renderdirend(self.entry)
        if (endstr):
            wfile.write(endstr)

            
