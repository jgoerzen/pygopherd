from pygopherd import protocols, handlers, gopherentry
from pygopherd.handlers.base import BaseHandler
from pygopherd.handlers.virtual import Virtual
from stat import *
import imp, re

class PYGHandler(Virtual):
    def canhandlerequest(self):
        if not (self.statresult and S_ISREG(self.statresult[ST_MODE]) and \
               (S_IMODE(self.statresult[ST_MODE]) & S_IXOTH) and \
               re.search("\.pyg$", self.getselector())):
            return 0
        self.modfd = open(self.getfspath(), "rt")
        self.module = imp.load_module('PYGHandler',
                                      self.modfd,
                                      self.getfspath(),
                                      ('', '', imp.PY_SOURCE))
        self.pygclass = self.module.PYGMain
        self.pygobject = self.pygclass(self.selector, self.protocol,
                                       self.config, self.statresult)
        return self.pygobject.canhandlerequest()
        
    def prepare(self):
        return self.pygobject.prepare()

    def getentry(self):
        return self.pygobject.getentry()

    def write(self, wfile):
        self.pygobject.write(wfile)

class PYGBase(Virtual):
    pass

        

    

    
