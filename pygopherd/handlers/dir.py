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
            if self.prep_initfiles_canaddfile(ignorepatt,
                                              self.selectorbase + '/' + file,
                                              file):
                self.files.append(file)

    def prep_initfiles_canaddfile(self, ignorepatt, pattern, file):
        return not re.search(ignorepatt, pattern)

    def prep_entries(self):
        "Generate entries from the list."

        self.fileentries = []
        for file in self.files:
            fileentry = gopherentry.GopherEntry(self.selectorbase + '/' + file,
                                          self.config)
            fileentry.populatefromfs(self.fsbase + '/' + file)
            self.prep_entrieshook(file, fileentry)
            self.fileentries.append(fileentry)

    def prep_entrieshook(self, file, fileentry):
        """Subclasses can override to do post-processing on the entry while
        we still have the filename around.
        IE, for .cap files."""
        pass

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

            
