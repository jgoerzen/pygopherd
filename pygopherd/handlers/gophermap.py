import SocketServer
import re
import os, stat, os.path, mimetypes, protocols, gopherentry
import handlers, handlers.base

class BuckGophermapHandler(handlers.base.BaseHandler):
    """Bucktooth selector handler.  Adheres to the specification
    at gopher://gopher.floodgap.com:70/0/buck/dbrowse%3Ffaquse%201"""
    def canhandlerequest(self):
        """We can handle the request if it's for a directory AND
        the directory has a gophermap file."""
        return os.path.isfile(self.getfspath() + '/gophermap')

    def getentry(self):
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            self.entry.populatefromfs(self.getfspath())
        return self.entry

    def write(self, wfile):
        selectorbase = self.selector
        if selectorbase == '/':
            selectorbase = ''           # Avoid dup slashes
        fsbase = self.getfspath()
        if fsbase == '/':
            fsbase = ''                 # Avoid dup slashes

        rfile = open(fsbase + '/gophermap', 'rb')
        for line in rfile:
            if re.search("\t", line):   # gophermap link
                args = map(lambda arg: arg.strip(), line.split("\t"))

                if len(args) < 2 or not len(args[1]):
                    args[1] = args[0][1:] # Copy display string to selector

                selector = args[1]
                if selector[0] != '/': # Relative link
                    selector = selectorbase + '/' + selector
                
                entry = gopherentry.GopherEntry(selector, self.config)
                entry.type = args[0][0]
                entry.name = args[0][1:]

                if len(args) >= 3 and len(args[2]):
                    entry.host = args[2]

                if len(args) >= 4 and len(args[3]):
                    entry.port = int(args[3])

                if entry.gethost() == None and entry.getport() == None:
                    # If we're using links on THIS server, try to fill
                    # it in for gopher+.
                    if os.path.exists(self.getrootpath() + selector):
                        entry.populatefromfs(self.getrootpath() + selector)
                wfile.write(self.protocol.renderobjinfo(entry))
            else:                       # Info line
                line = line.strip()
                entry = gopherentry.GopherEntry('fake', self.config)
                entry.name = line
                entry.host = '(NULL)'
                entry.port = 0
                entry.type = 'i'
                wfile.write(self.protocol.renderobjinfo(entry))
