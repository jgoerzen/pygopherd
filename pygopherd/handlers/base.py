import SocketServer
import re
import os, stat, os.path, mimetypes, protocols, handlers, gopherentry

class BaseHandler:
    """Skeleton handler -- includes commonly-used routines."""
    def __init__(self, selector, protocol, config):
        """Parameters are:
        selector -- requested selector.  The selector must always start
        with a slash and never end with a slash UNLESS it is a one-char
        selector that contains only a slash.  This should be handled
        by the default protocol.

        config -- config object."""
        self.selector = selector
        self.protocol = protocol
        self.config = config
        self.fspath = None
        self.entry = None

    def canhandlerequest(self):
        """Decides whether or not a given request is valid for this
        handler.  Should be overridden by all subclasses."""
        return 0

    def getentry(self):
        """Returns an entry object for this request."""
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
        return self.entry

    def getrootpath(self):
        """Gets the root path."""
        return self.config.get("pygopherd", "root")

    def getfspath(self):
        """Gets the filesystem path corresponding to the selector."""
        if self.fspath:
            return self.fspath

        self.fspath = self.getrootpath() + self.selector

        return self.fspath

    def prepare(self):
        """Prepares for a write.  Ie, opens a file.  This is
        used so that the protocols can try to detect an error before
        transmitting a result."""
        pass

    def write(self, wfile):
        """Writes out the request.  Should be overridden.
        Must always be called before write."""
        pass

