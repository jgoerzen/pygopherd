import SocketServer
import re
import os, stat, os.path, mimetypes, protocols, gopherentry
import handlers, handlers.base
from gopherentry import GopherEntry
from handlers.dir import DirHandler

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
    if entry1.getname() == None:
        return 1
    if entry2.getname() == None:
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

class LinkEntry(GopherEntry):
    def __init__(self, selector, config):
        GopherEntry.__init__(self, selector, config)
        self.needsmerge = 0
    def getneedsmerge(self):
        return self.needsmerge
    def setneedsmerge(self, arg):
        self.needsmerge = arg

class UMNDirHandler(DirHandler):
    """This module strives to be bug-compatible with UMN gopherd."""

    def prepare(self):
        """Override parent to do a few more things and override sort order."""
        self.linkentries = []
        DirHandler.prepare(self)
        self.MergeLinkFiles()
        self.fileentries.sort(entrycmp)
        
    def prep_initfiles_canaddfile(self, ignorepatt, pattern, file):
        """Override the parent to process dotfiles and keep them out
        of the list."""
        if DirHandler.prep_initfiles_canaddfile(self, ignorepatt, pattern,
                                                 file):
            # If the parent says it's OK, then let's see if it's
            # a link file.  If yes, process it and return false.
            if file[0] == '.' and not os.path.isdir(self.fsbase + '/' + file):
                self.linkentries.extend(self.processLinkFile(self.fsbase + '/' + file))
                return 0
            return 1
        else:
            return 0

    def MergeLinkFiles(self):
        for linkentry in self.linkentries:
            if not linkentry.getneedsmerge():
                self.fileentries.append(linkentry)
                continue
            # Find matching directory entry.
            direntry = None
            for direntrytry in self.fileentries:
                if linkentry.getselector() == direntrytry.getselector() and \
                       linkentry.gethost() == direntrytry.gethost() and \
                       linkentry.getport() == direntrytry.getport():
                    direntry = direntrytry
                    break
            if direntry:                # It matches!
                if linkentry.gettype() == 'X':
                    # It's special code to hide something.
                    self.fileentries.remove(direntry)
                else:
                    self.mergeentries(direntry, linkentry)
            else:
                # No match -- add to the directory.
                self.fileentries.append(linkentry)

    def mergeentries(self, old, new):
        for field in ['selector', 'type', 'name', 'host', 'port']:
            if getattr(new, field):
                setattr(old, field, getattr(new, field))


    def prep_entriesappend(self, file, fileentry):
        """Overridden to process .cap files."""
        capfilename = self.fsbase + '/.cap/' + file
        if os.path.isfile(capfilename):
            capinfo = self.processLinkFile(capfilename,
                                           fileentry.getselector())
            if len(capinfo) >= 1:       # We handle one and only one entry.
                if capinfo[0].gettype() == 'X':
                    return
                else:
                    self.mergeentries(fileentry, capinfo[0])
        DirHandler.prep_entriesappend(self, file, fileentry)

    def processLinkFile(self, filename, capfilepath = None):
        linkentries = []
        fd = open(filename, "rt")
        while 1:
            nextstep, entry = self.getLinkItem(fd, capfilepath)
            if entry:
                linkentries.append(entry)
            if nextstep == 'stop':
                break
        return linkentries
        
    def getLinkItem(self, fd, capfilepath = None):
        """This is an almost exact clone of UMN's GSfromLink function."""
        entry = LinkEntry(self.entry.selector, self.config)
        nextstep = 'continue'

        done = {'path' : 0, 'type' : 0, 'name' : 0, 'host' : 0, 'port' : 0}

        if capfilepath != None:
            entry.setselector(capfilepath)
            done['path'] = 1

        while 1:
            line = fd.readline()
            if not line:
                nextstep = 'stop'
                break
            line = line.strip()

            # Empty.
            if len(line) == 0:
                break

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
                    entry.setselector(self.selectorbase + "/" + line[7:])
                    entry.setneedsmerge(1)
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
            elif line[0:9] == 'Abstract=' or \
                 line[0:6] == 'Admin=' or \
                 line[0:4] == 'URL=' or \
                 line[0:4] == 'TTL=':
                pass
            else:
                break
            ### FIXME: Handle Abstract, Admin, URL, TTL

        if done['path']:
            return (nextstep, entry)
        return (nextstep, None)
