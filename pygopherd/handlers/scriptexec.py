# pygopherd -- Gopher-based protocol server in Python
# module: Script execution
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


from pygopherd import protocols, handlers, gopherentry
from pygopherd.handlers.base import BaseHandler
from pygopherd.handlers.virtual import Virtual
import pygopherd.pipe
from stat import *
import imp, re, os

class ExecHandler(Virtual):
    def canhandlerequest(self):
        return self.statresult and S_ISREG(self.statresult[ST_MODE]) and \
               (S_IMODE(self.statresult[ST_MODE]) & S_IXOTH)
        
    def getentry(self):
        entry = gopherentry.GopherEntry(self.getselector(), self.config)
        entry.settype('0')
        entry.setname(os.path.basename(self.getselector()))
        entry.setmimetype('text/plain')
        entry.setgopherpsupport(0)
        return entry

    def write(self, wfile):
        # We work on a separate thing to avoid contaminating our own
        # environment.  Just saying newenv = os.environ would still
        # do that.
        newenv = {}
        for key in os.environ.keys():
            newenv[key] = os.environ[key]
        newenv['SERVER_NAME'] = self.protocol.server.server_name
        newenv['SERVER_PORT'] = str(self.protocol.server.server_port)
        newenv['REMOTE_ADDR'] = self.protocol.requesthandler.client_address[0]
        newenv['REMOTE_PORT'] = str(self.protocol.requesthandler.client_address[1])
        newenv['REMOTE_HOST'] = newenv['REMOTE_ADDR']
        newenv['SELECTOR'] = self.selector
        newenv['REQUEST'] = self.getselector()
        if self.searchrequest:
            newenv['SEARCHREQUEST'] = self.searchrequest
        wfile.flush()

        args = [self.getfspath()]
        if self.selectorargs:
            args.extend(self.selectorags.split(' '))

        pygopherd.pipe.pipedata(self.getfspath(), args, newenv,
                                childstdout = wfile)
