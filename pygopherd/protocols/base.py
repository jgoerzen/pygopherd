import SocketServer
import re
import os, stat, os.path, mimetypes, handlers

class BaseGopherProtocol:
    """Skeleton protocl -- includes commonly-used routines."""
    def __init__(self, requestlist, server, rfile, wfile, config):
        """Parameters are:
        requestlist -- a list of the tab-separated params.
        requestlist[0] is the selector.

        server -- a SocketServer object.

        rfile -- input file.  The first line will already have been read.

        wfile -- output file.  Where the output should be sent.

        config -- a ConfigParser object."""
        
        self.requestlist = requestlist
        self.rfile = rfile
        self.wfile = wfile
        self.config = config
        self.selector = requestlist[0]
        self.server = server

    def canhandlerequest(self):
        """Decides whether or not a given request is valid for this
        protocol.  Should be overridden by all subclasses."""
        return 0

    def handle(self):
        """Handles the request."""
        handler = self.gethandler()
        self.entry = handler.getobj()
        entry.write(self, self.wfile)
        pass

    def renderobjinfo(self, entry):
        """Renders an object's info according to the protocol.  Returns
        a string.  A gopher0 server, for instance, would return a dir line."""
        pass

    def gethandler(self):
        """Gets the handler for this object's selector."""
        handlers.HandlerMultiplexer.getHandler(self.selector, self.config)
