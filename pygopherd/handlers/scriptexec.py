from pygopherd import protocols, handlers, gopherentry
from pygopherd.handlers.base import BaseHandler
from pygopherd.handlers.virtual import Virtual
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
        newenv = os.environ.copy()
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
        # ASSUMING WE ARE USING FORKING SERVER!
        # Set stdout to be the wfile.
        os.dup2(wfile.fileno(), 1)
        args = [self.getfspath()]
        if self.selectorargs:
            args.extend(self.selectorags.split(' '))
        os.spawnve(os.P_WAIT, self.getfspath(),
                   args, newenv)
