# pygopherd -- Gopher-based protocol server in Python
# module: Present a mbox file as if it were a folder.
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


import SocketServer
import re
import os, stat, os.path, mimetypes
from pygopherd import protocols, handlers, gopherentry
from pygopherd.handlers.vfolder import VirtualFolder
from mailbox import UnixMailbox, Maildir
from stat import *


###########################################################################
# Basic mailbox support
###########################################################################

class FolderHandler(VirtualFolder):
    def getentry(self):
        ## Return my own entry.
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.getselector(),
                                                 self.config)
            self.entry.settype('1')
            self.entry.setname(os.path.basename(self.getselector()))
            self.entry.setmimetype('application/gopher-menu')
            self.entry.setgopherpsupport(0)
        return self.entry

    def write(self, wfile):
        startstr = self.protocol.renderdirstart(self.entry)
        if (startstr):
            wfile.write(startstr)

        count = 1
        while 1:
            message = self.mbox.next()
            if not message:
                break
            handler = MessageHandler(self.genargsselector(self.getargflag() + \
                                     str(count)), self.protocol, self.config,
                                     None)
            wfile.write(self.protocol.renderobjinfo(handler.getentry(message)))
            count += 1

        endstr = self.protocol.renderdirend(self.entry)
        if (endstr):
            wfile.write(endstr)

class MessageHandler(VirtualFolder):
    def canhandlerequest(self):
        """We put MBOX-MESSAGE in here so we don't have to re-check
        the first line of the mbox file before returning a true or false
        result."""
        if not self.selectorargs:
            return 0
        msgnum = re.search('^' + self.getargflag() + '(\d+)$',
                           self.selectorargs)
        if not msgnum:
            return 0
        self.msgnum = int(msgnum.group(1))
        self.message = None
        return 1

    def getentry(self, message = None):
        """Set the message if called from, eg, the dir handler.  Saves
        having to rescan the file.  If not set, will figure it out."""
        if not message:
            message = self.getmessage()
            
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            self.entry.settype('0')
            self.entry.setmimetype('text/plain')
            self.entry.setgopherpsupport(0)

            subject = message.getheader('Subject')
            # Sanitize, esp. for continuations.
            subject = re.sub('\s+', ' ', subject)
            if subject:
                self.entry.setname(subject)
            else:
                self.entry.setname('<no subject>')
        return self.entry

    def getmessage(self):
        if self.message:
            return self.message
        mbox = self.openmailbox()
        message = None
        for x in range(self.msgnum):
            message = mbox.next()
        self.message = message
        return self.message

    def prepare(self):
        self.canhandlerequest()         # Init the vars

    def write(self, wfile):
        # Print out the headers first.
        for header in self.getmessage().headers:
            wfile.write(header)

        # Now the message body.
        self.rfile = self.getmessage().fp
        while 1:
            string = self.rfile.read(4096)
            if not len(string):
                break
            wfile.write(string)
        self.rfile.close()
        self.rfile = None

###########################################################################
# Unix MBOX support
###########################################################################

class MBoxFolderHandler(FolderHandler):
    def canhandlerequest(self):
        """Figure out if this is a handleable request."""

        if self.selectorargs:
            return 0
        
        if not S_ISREG(self.statresult[ST_MODE]):
            return 0
        try:
            fd = open(self.getfspath(), "rt")
            startline = fd.readline()
            fd.close()
            
            return re.match(UnixMailbox._fromlinepattern, startline)
        except IOError:
            return 0

    def prepare(self):
        self.rfile = open(self.getfspath(), "rt")
        self.mbox = UnixMailbox(self.rfile)

    def getargflag(self):
        return "/MBOX-MESSAGE/"

class MBoxMessageHandler(MessageHandler):
    def getargflag(self):
        return "/MBOX-MESSAGE/"

    def openmailbox(self):
        fd = open(self.getfspath(), "rt")
        return UnixMailbox(fd)

###########################################################################
# Maildir support
###########################################################################

class MaildirFolderHandler(FolderHandler):
    def canhandlerequest(self):
        if self.selectorargs:
            return 0
        if not S_ISDIR(self.statresult[ST_MODE]):
            return 0
        return os.path.isdir(self.getfspath() + "/new") and \
               os.path.isdir(self.getfspath() + "/cur")

    def prepare(self):
        self.mbox = Maildir(self.getfspath())

    def getargflag(self):
        return "/MAILDIR-MESSAGE/"

class MaildirMessageHandler(MessageHandler):
    def getargflag(self):
        return "/MAILDIR-MESSAGE/"

    def openmailbox(self):
        return Maildir(self.getfspath())

