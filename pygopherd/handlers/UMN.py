2import SocketServer
import re
import os, stat, os.path, mimetypes, protocols, gopherentry
import handlers, handlers.base

def sgn(a):
    """Returns -1 if less than 0, 1 if greater than 0, and 0 if
    equal to zero."""
    if a == 0:
        return 0
    if a < 0:
        return -1
    return 1

def entrycmp(entry1, entry2):
    """This function implements an exact replica of UMN behavior
    GSqsortcmp() behavior."""
    if entry1.getTitle() == None:
        return 1
    if entry2.getTitle() == None:
        return -1

    # Equal numbers or no numbers: sort by title.
    if entry1.getnum() == entry2.getnum():
        return cmp(entry1.getname(), entry2.getname())

    # Same signs: use plain numeric comparison.
    if (sgn(entry1.getnum()) == sgn(entry2.getnum())):
        return cmp(entry1.getnum(), entry2.getnum())

    # Different signs: other comparison.
    if entry1.getnum() > entry2.getnum():
        return -1
    else:
        return 1

class UMNLinkFile:
    def __init__(self, filename, config, pathname, selector = None):
        """Args: filename of the file to process.
        The global config file.
        The name of the directory we are looking at.
        An optional selector default [deprecated]"""
        self.fd = open(filename, "rt")
        self.filename = filename
        self.config = config
        self.pathname = pathname
        self.selector = selector

    def getLinkItem(self):
        """This is an almost exact clone of UMN's GSfromLink function."""
        entry = GopherEntry(self.selector, self.config)

        done = {'path' : 0, 'type' : 0, 'name' : 0, 'host' : 0, 'port' : 0}
        
        while 1:
            line = self.fd.readline()
            if not line:
                break
            line = line.strip()

            # Comment.
            if line[0] == '#':
                if done['path']:
                    break
                else:
                    continue

            # Type.
            if line[0:5] == "Type=":
                entry.settype(line[5])
                # FIXME: handle if line[6] is + or ?
                done['type'] = 1
            elif line[0:5] == "Name=":
                entry.setname(line[5:])
                done['name'] = 1
            elif line[0:5] == "Path=":
                # Handle ./: make full path.
                if line[5:7] == './' or line[5:7] == '~/':
                    entry.setselector(self.pathname + "/" + line[7:])
                else:
                    entry.setselector(line[5:])
                done['path'] = 1
            elif line[0:5] == 'Host=':
                if line[5:] != '+':
                    entry.sethost(line[5:])
                done['host'] = 1
            elif line[0:5] == 'Port=':
                if line[5:] != '+':
                    entry.setport(int(line[5:]))
                done['port'] = 1
            elif line[0:5] == 'Numb=':
                entry.setnum(int(line[5:]))
            ### FIXME: Handle Abstract, Admin, URL, TTL

        if done['path']:
            return entry
        return None

class UMNDirHandler(handlers.dir.DirHandler):

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

        startstr = self.protocol.renderdirstart(self.entry)
        if (startstr):
            wfile.write(startstr)

        for file in self.files:
            # Skip files we're ignoring.
            if re.search(ignorepatt, selectorbase + '/' + file):
                continue
            
            fileentry = gopherentry.GopherEntry(selectorbase + '/' + file,
                                          self.config)
            fileentry.populatefromfs(fsbase + '/' + file)
            wfile.write(self.protocol.renderobjinfo(fileentry))

        endstr = self.protocol.renderdirend(self.entry)
        if (endstr):
            wfile.write(endstr)

            


##################################################
# Port from UMN C source
##################################################

def GSfromLink(gs, fio, host, port, directory, peer):
    
