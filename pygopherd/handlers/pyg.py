from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.virtual import Virtual
from stat import *
import imp, re


class PYGHandler(Virtual):
    def canhandlerequest(self):
        if not isinstance(self.vfs, VFS_Real):
            return 0
        if not (
            self.statresult
            and S_ISREG(self.statresult[ST_MODE])
            and (S_IMODE(self.statresult[ST_MODE]) & S_IXOTH)
            and re.search("\.pyg$", self.getselector())
        ):
            return 0
        self.modfd = self.vfs.open(self.getselector(), "rt")
        self.module = imp.load_module(
            "PYGHandler", self.modfd, self.getfspath(), ("", "", imp.PY_SOURCE)
        )
        self.pygclass = self.module.PYGMain
        self.pygobject = self.pygclass(
            self.selector,
            self.searchrequest,
            self.protocol,
            self.config,
            self.statresult,
        )
        return self.pygobject.isrequestforme()

    def prepare(self):
        return self.pygobject.prepare()

    def getentry(self):
        return self.pygobject.getentry()

    def isdir(self):
        return self.pygobject.isdir()

    def getdirlist(self):
        return self.pygobject.getdirlist()

    def write(self, wfile):
        self.pygobject.write(wfile)


class PYGBase(Virtual):
    pass
