import SocketServer
import re
import os, stat, os.path, mimetypes, protocols, handlers

class BaseHandler:
    """Skeleton handler -- includes commonly-used routines."""
    def __init__(self, selector, config):
        """Parameters are:
        selector -- requested selector.  The selector must always start
        with a slash and never end with a slash UNLESS it is a one-char
        selector that contains only a slash.  This should be handled
        by the default protocol.

        config -- config object."""
        self.selector = selector
        self.config = config
        self.fspath = None

    def canhandlerequest(self):
        """Decides whether or not a given request is valid for this
        handler.  Should be overridden by all subclasses."""
        return 0

    def getentry(self):
        """Returns an entry object for this request."""
        return None

    def getfspath(self):
        """Gets the filesystem path corresponding to the selector."""
        if self.fspath:
            return self.fspath

        self.fspath = self.server.config.get("serving", "root") + \
                      self.selector

        return self.fspath
