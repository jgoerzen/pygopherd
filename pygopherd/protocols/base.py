import SocketServer
import re
import os, stat, os.path, mimetypes, handlers, GopherExceptions
import handlers.HandlerMultiplexer

class BaseGopherProtocol:
    """Skeleton protocl -- includes commonly-used routines."""
    def __init__(self, request, server, rfile, wfile, config):
        """Parameters are:
        request -- the raw request string.

        server -- a SocketServer object.

        rfile -- input file.  The first line will already have been read.

        wfile -- output file.  Where the output should be sent.

        config -- a ConfigParser object."""

        self.request = request
        requestparts = map(lambda arg: arg.strip(), request.split("\t"))
        self.rfile = rfile
        self.wfile = wfile
        self.config = config
        self.server = server
        self.requestlist = requestparts

        self.requestlist = requestparts
        selector = requestparts[0]

        if re.match('\./', selector):    # Weed out ./ and ../
            # FIXME: THROW ERROR!
            pass
        if re.match('//', selector):     # Weed out //
            # FIXME: THROW ERROR
            pass
        
        if len(selector) and selector[-1] == '/':
                selector = selector[0:-1]
        if len(selector) == 0 or selector[0] != '/':
            selector = '/' + selector

        self.selector = selector

    def canhandlerequest(self):
        """Decides whether or not a given request is valid for this
        protocol.  Should be overridden by all subclasses."""
        return 0

    def handle(self):
        """Handles the request."""
        try:
            handler = self.gethandler()
            self.entry = handler.getentry()
            handler.prepare()
            handler.write(self.wfile)
        except GopherExceptions.FileNotFound, e:
            self.filenotfound(str(e))
        except IOError, e:
            self.filenotfound(e[1])

    def filenotfound(self, msg):
        self.wfile.write("0%s\t\terror.host\t1\r\n" % msg)

    def renderobjinfo(self, entry):
        """Renders an object's info according to the protocol.  Returns
        a string.  A gopher0 server, for instance, would return a dir line."""
        pass

    def gethandler(self):
        """Gets the handler for this object's selector."""
        return handlers.HandlerMultiplexer.getHandler(self.selector,
                                               self, self.config)

    def renderdirstart(self, entry):
        """Renders the start of a directory.  Most protocols will not need
        this.  Exception might be HTML.  Returns None if not needed."""
        return None

    def renderdirend(self, entry):
        """Likewise for the end of a directory."""
        return None
