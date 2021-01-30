# Running eval() when loading the configuration requires all of the protocols to
# be in the module namespace
from pygopherd.protocols.base import BaseGopherProtocol
from pygopherd.protocols import *  # noqa


def getProtocol(
    request, server, requesthandler, rfile, wfile, config
) -> BaseGopherProtocol:
    p = eval(config.get("protocols.ProtocolMultiplexer", "protocols"))

    for protocol in p:
        ptry = protocol(request, server, requesthandler, rfile, wfile, config)
        if ptry.canhandlerequest():
            return ptry
