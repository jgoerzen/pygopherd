import handlers, protocols
from protocols import *

def getProtocol(request, server, rfile, wfile, config):
    p = eval(config.get("protocols.ProtocolMultiplexer", "protocols"))

    for protocol in p:
        ptry = protocol(request, server, rfile, wfile, config)
        if ptry.canhandlerequest():
            return ptry
