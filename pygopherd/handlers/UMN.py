import SocketServer
import re
import os, stat, os.path, mimetypes, protocols, gopherentry
import handlers, handlers.base
from gopherentry import GopherEntry
from handlers.dir import DirHandler

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

        # Initialize.
        self.linkentries = []

        # Let the parent do the directory walking for us.  Will call
        # prep_initfiles_canaddfile and prep_entriesappend.
        DirHandler.prepare(self)

        # Merge and sort.
        self.MergeLinkFiles()
        self.fileentries.sort(self.entrycmp)
        
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
            return 1                    # Not a dot file -- return true
        else:
            return 0                    # Parent returned 0, do the same.

    def prep_entriesappend(self, file, fileentry):
        """Overridden to process .cap files.  This is called by the
        parent's prepare to append an entry to the list.  Here, we check
        to see if there's a .cap file right before adding it."""
        capfilename = self.fsbase + '/.cap/' + file
        if os.path.isfile(capfilename):
            capinfo = self.processLinkFile(capfilename,
                                           fileentry.getselector())
            if len(capinfo) >= 1:       # We handle one and only one entry.
                if capinfo[0].gettype() == 'X':
                    return              # Type X -- don't append.
                else:
                    self.mergeentries(fileentry, capinfo[0])
        DirHandler.prep_entriesappend(self, file, fileentry)

    def MergeLinkFiles(self):
        """Called to merge the files from .Links and .names into the
        objects obtained by walking the directory.  According to UMN code,
        we ONLY merge if the Path starts with ./ or ~/ in the file.  This
        is set in the getneedsmerge() attribute.  If that attribute is
        not set, don't even bother with it -- just add."""
        
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
        """Takes the set fields from new and modifies old to have their
        value."""
        for field in ['selector', 'type', 'name', 'host', 'port']:
            if getattr(new, field):
                setattr(old, field, getattr(new, field))

    def processLinkFile(self, filename, capfilepath = None):
        """Processes a link file.  If capfilepath is set, it should
        be the equivolent of the Path= in a .names file."""
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
                pathname = line[5:]
                if pathname[-1] == '/':
                    pathname = pathname[0:-1]
                # Handle ./: make full path.
                if line[5:7] == './' or line[5:7] == '~/':
                    entry.setselector(self.selectorbase + "/" + pathname[2:])
                    entry.setneedsmerge(1)
                else:
                    entry.setselector(pathname)
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

    def sgn(self, a):
        """Returns -1 if less than 0, 1 if greater than 0, and 0 if
        equal to zero."""
        if a == 0:
            return 0
        if a < 0:
            return -1
        return 1

    def entrycmp(self, entry1, entry2):
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
        if (self.sgn(entry1.getnum()) == self.sgn(entry2.getnum())):
            return cmp(entry1.getnum(), entry2.getnum())

        # Different signs: other comparison.
        if entry1.getnum() > entry2.getnum():
            return -1
        else:
            return 1

