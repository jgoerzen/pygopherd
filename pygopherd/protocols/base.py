from __future__ import annotations

import configparser
import io
import typing

from pygopherd import GopherExceptions, gopherentry, logger
from pygopherd.handlers import HandlerMultiplexer

if typing.TYPE_CHECKING:
    from pygopherd.gopherentry import GopherEntry
    from pygopherd.handlers.base import BaseHandler
    from pygopherd.initialization import GopherRequestHandler
    from pygopherd.server import BaseServer


class BaseGopherProtocol:
    """Skeleton protocol -- includes commonly-used routines."""

    def __init__(
        self,
        request: str,
        server: BaseServer,
        requesthandler: GopherRequestHandler,
        rfile: io.BufferedIOBase,
        wfile: io.BufferedIOBase,
        config: configparser.ConfigParser,
    ):
        """Parameters are:
        request -- the raw request string.

        server -- a SocketServer object.

        rfile -- input file.  The first line will already have been read.

        wfile -- output file.  Where the output should be sent.

        config -- a ConfigParser object."""

        self.request = request
        requestparts = [arg.strip() for arg in request.split("\t")]
        self.rfile = rfile
        self.wfile = wfile
        self.config = config
        self.server = server
        self.requesthandler = requesthandler
        self.requestlist = requestparts
        self.searchrequest = None
        self.handler = None

        selector = requestparts[0]
        selector = self.slashnormalize(selector)

        self.selector = selector

    def slashnormalize(self, selector: str) -> str:
        """Normalize slashes in the selector.  Make sure it starts
        with a slash and does not end with one.  If it is a root directory
        request, make sure it is exactly '/'.  Returns result."""
        if len(selector) and selector[-1] == "/":
            selector = selector[0:-1]
        if len(selector) == 0 or selector[0] != "/":
            selector = "/" + selector
        return selector

    def canhandlerequest(self) -> bool:
        """Decides whether or not a given request is valid for this
        protocol.  Should be overridden by all subclasses."""
        return False

    def log(self, handler: BaseHandler) -> None:
        """Log a handled request."""
        logger.log(
            "%s [%s/%s]: %s"
            % (
                self.requesthandler.client_address[0],
                type(self).__name__,
                type(handler).__name__,
                self.selector,
            )
        )

    def handle(self) -> None:
        """Handles the request."""
        try:
            handler = self.gethandler()
            self.log(handler)
            self.entry = handler.getentry()
            handler.prepare()
            if handler.isdir():
                self.writedir(self.entry, handler.getdirlist())
            else:
                handler.write(self.wfile)
        except GopherExceptions.FileNotFound as e:
            self.filenotfound(str(e))
        except IOError as e:
            GopherExceptions.log(e, self, None)
            self.filenotfound(e.strerror)

    def filenotfound(self, msg: str):
        self.wfile.write(
            f"3{msg}\t\terror.host\t1\r\n".encode(errors="surrogateescape")
        )

    def gethandler(self) -> BaseHandler:
        """Gets the handler for this object's selector."""
        if not self.handler:
            self.handler = HandlerMultiplexer.getHandler(
                self.selector, self.searchrequest, self, self.config
            )
        return self.handler

    def writedir(
        self, entry: GopherEntry, dirlist: typing.Iterable[GopherEntry]
    ) -> None:
        """Called to render a directory.  Generally called by self.handle()"""

        startstr = self.renderdirstart(entry)
        if startstr is not None:
            self.wfile.write(startstr.encode(errors="surrogateescape"))

        abstractopt = self.config.get("pygopherd", "abstract_entries")
        doabstracts = abstractopt == "always" or (
            abstractopt == "unsupported" and not self.groksabstract()
        )

        if self.config.getboolean("pygopherd", "abstract_headers"):
            self.wfile.write(
                self.renderabstract(entry.getea("ABSTRACT", "")).encode(
                    errors="surrogateescape"
                )
            )

        for direntry in dirlist:
            self.wfile.write(
                self.renderobjinfo(direntry).encode(errors="surrogateescape")
            )
            if doabstracts:
                abstract = self.renderabstract(direntry.getea("ABSTRACT"))
                if abstract:
                    self.wfile.write(abstract.encode(errors="surrogateescape"))

        endstr = self.renderdirend(entry)
        if endstr is not None:
            self.wfile.write(endstr.encode(errors="surrogateescape"))

    def renderabstract(self, abstractstring: str) -> str:
        if not abstractstring:
            return ""
        retval = ""
        for line in abstractstring.splitlines():
            absentry = gopherentry.getinfoentry(line, self.config)
            retval += self.renderobjinfo(absentry)
        return retval

    def renderdirstart(self, entry: GopherEntry) -> typing.Optional[str]:
        """Renders the start of a directory.  Most protocols will not need
        this.  Exception might be HTML.  Returns None if not needed.
        Argument should be the entry corresponding to the dir itself."""
        return None

    def renderdirend(self, entry: GopherEntry) -> typing.Optional[str]:
        """Likewise for the end of a directory."""
        return None

    def renderobjinfo(self, entry: GopherEntry) -> typing.Optional[str]:
        """Renders an object's info according to the protocol.  Returns
        a string.  A gopher0 server, for instance, would return a dir line.
        MUST BE OVERRIDDEN."""
        return None

    def groksabstract(self) -> bool:
        """Returns true if this protocol understands abstracts natively;
        false otherwise."""
        return False
