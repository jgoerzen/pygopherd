from pygopherd import initialization, logger
from StringIO import StringIO

def getconfig():
    return initialization.initconffile('conf/pygopherd.conf')

def getstringlogger():
    config = getconfig()
    config.set('logger', 'logmethod', 'file')
    logger.init(config)
    stringfile = StringIO()
    logger.setlogfile(stringfile)
    return stringfile

def gettestingserver(config = getconfig()):
    config.set('pygopherd', 'port', '64777')
    s = initialization.getserverobject(config)
    s.server_close()
    return s

def gettestinghandler(rfile, wfile, config = getconfig()):
    """Creates a testing handler with input from rfile.  Fills in
    other stuff with fake values."""

    # Kludge to pass to the handler init.
    
    class request:
        def __init__(self, rfile, wfile):
            self.rfile = rfile
            self.wfile = wfile
        def makefile(self, mode, bufsize):
            if mode[0] == 'r':
                return self.rfile
            return self.wfile

    s = gettestingserver(config)
    rhandler = initialization.GopherRequestHandler(request(rfile, wfile),
                                                   ('10.77.77.77', '7777'),
                                                   s)
    return rhandler

