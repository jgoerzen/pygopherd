from __future__ import annotations

import typing

from pygopherd import logger

if typing.TYPE_CHECKING:
    from pygopherd.handlers.base import BaseHandler
    from pygopherd.protocols.base import BaseGopherProtocol


tracebacks = 0


def log(
    exception: Exception,
    protocol: typing.Optional[BaseGopherProtocol] = None,
    handler: typing.Optional[BaseHandler] = None,
):
    """Logs an exception.  It will try to generate a nice-looking string
    based on the arguments passed in."""
    protostr = "None"
    handlerstr = "None"
    ipaddr = "unknown-address"
    exceptionclass = type(exception).__name__
    if protocol:
        protostr = type(protocol).__name__
        ipaddr = protocol.requesthandler.client_address[0]
    if handler:
        handlerstr = type(handler).__name__

    logger.log(
        "%s [%s/%s] EXCEPTION %s: %s"
        % (ipaddr, protostr, handlerstr, exceptionclass, str(exception))
    )


def init(backtraceenabled):
    global tracebacks
    tracebacks = backtraceenabled


class FileNotFound(Exception):
    def __init__(
        self,
        selector: str,
        comments: str = "",
        protocol: typing.Optional[BaseGopherProtocol] = None,
    ):
        self.selector = selector
        self.comments = comments
        self.protocol = protocol

        log(self, self.protocol, None)

    def __str__(self):
        retval = "'%s' does not exist" % self.selector
        if self.comments:
            retval += " (%s)" % self.comments

        return retval
