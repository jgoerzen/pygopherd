from pygopherd import gopherentry
from stat import *
from pygopherd.handlers.base import BaseHandler
import os

class Virtual(BaseHandler):
    """Implementation of virtual folder support.  This class will probably
    not be instantiated itself but it is designed to be instantiated by
    its children."""

    def __init__(self, selector, searchrequest, protocol, config, statresult,
                 vfs = None):
        BaseHandler.__init__(self, selector, searchrequest,
                             protocol, config, statresult, vfs)

        # These hold the "real" and the "argument" portion of the selector,
        # respectively.

        self.selectorreal = None
        self.selectorargs = None

        if self.selector.find("?") != -1 or self.selector.find("|") != -1:
            try:
                i = self.selector.index("?")
            except:
                i = self.selector.index("|")
                
            self.selectorreal = self.selector[0:i]
            self.selectorargs = self.selector[i+1:]
            # Now, retry the stat with the real selector.
            self.statresult = None
            try:
                self.statresult = self.vfs.stat(self.selectorreal)
            except OSError:
                pass
        else:
            # Best guess.
            self.selectorreal = self.selector


    def genargsselector(self, args):
        """Returns a string representing a full selector to this resource, with
        the given string of args.  This is a selector that can be passed
        back to clients."""
        return self.getselector() + "|" + args

    def getselector(self):
        """Overridden to return the 'real' portion of the selector."""
        return self.selectorreal
                                  
