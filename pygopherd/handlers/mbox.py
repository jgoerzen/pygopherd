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
import os, stat, os.path, mimetypes, protocols, handlers, gopherentry
import handlers.base
from mailbox import UnixMailbox

class FolderHandler(handlers.base.BaseHandler):
    def canhandlerequest(self):
        """Figure out if this is a handleable request."""
        
        if not os.path.isfile(self.getfspath()):
            return 0
        try:
            fd = open(self.getfspath(), "rt")
            startline = fd.readline()
            fd.close()
            
            return re.match(UnixMailbox._fromlinepattern, startline)
        except IOError:
            return 0

    def getentry(self):
        ## Return my own entry.
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            # Populate, then override.
            self.entry.settype('1')
            self.entry.setname(os.path.basename(self.selector))
            self.entry.setmimetype('application/gopher-menu')
            self.entry.setgopherpsupport(0)
        return self.entry

    def prepare(self):
        self.rfile = open(self.getfspath(), "rt")
        self.mbox = UnixMailbox(self.rfile)

    def write(self, wfile):
        startstr = self.protocol.renderdirstart(self.entry)
        if (startstr):
            wfile.write(startstr)

        count = 1
        while 1:
            message = self.mbox.next()
            if not message:
                break
            handler = MessageHandler(self.selector + "/MBOX-MESSAGE/" + \
                                     str(count), self.protocol, self.config)
            wfile.write(self.protocol.renderobjinfo(handler.getentry(message)))
            count += 1

        endstr = self.protocol.renderdirend(self.entry)
        if (endstr):
            wfile.write(endstr)

class MessageHandler(handlers.base.BaseHandler):
    def canhandlerequest(self):
        msgnum = re.search('/MBOX-MESSAGE/(\d+)$', self.selector)
        if not msgnum:
            return 0
        self.msgnum = int(msgnum.group(1))
        self.msgpath = re.sub('/MBOX-MESSAGE/\d+$', '', self.getfspath())
        self.message = None
        return os.path.isfile(self.msgpath)

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
        fd = open(self.msgpath, "rt")
        mbox = UnixMailbox(fd)
        message = None
        for x in range(self.msgnum):
            message = mbox.next()
        self.message = message
        return self.message

    def prepare(self):
        self.canhandlerequest()         # Init the vars

    def write(self, wfile):
        self.rfile = self.getmessage().fp
        while 1:
            string = self.rfile.read(4096)
            if not len(string):
                break
            wfile.write(string)
        self.rfile.close()
        self.rfile = None

