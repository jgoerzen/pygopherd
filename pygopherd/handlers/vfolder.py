from pygopherd import gopherentry
from stat import *
from pygopherd.handlers.base import BaseHandler
import os

class VirtualFolder(BaseHandler):
    """Implementation of virtual folder support.  This class will probably
    not be instantiated itself but it is designed to be instantiated by
    its children."""

    def __init__(self, selector, protocol, config, statresult):
        BaseHandler.__init__(self, selector, protocol, config, statresult)

        # These hold the "real" and the "argument" portion of the selector,
        # respectively.

        self.selectorreal = None
        self.selectorargs = None

        if statresult:
            # Stat succeeded?  Can't be anything fake here.
            self.selectorreal = self.selector
        elif self.selector.index("?"):
            i = self.selector.index("?")
            self.selectorreal = self.selector[0:i]
            self.selectorargs = self.selector[i+1:]
        else:
            # Best guess.
            self.selectorreal = self.selector

        # Now, retry the stat with the real selector.

        self.statresult = os.stat(self.getrootpath() + '/' + self.selectorreal)

    def genargsselector(self, args):
        """Returns a string representing a full selector to this resource, with
        the given string of args.  This is a selector that can be passed
        back to clients."""
        return self.getselector() + "?" + args

    def getselector(self):
        """Overridden to return the 'real' portion of the selector."""
        return self.selectorreal
                                  
