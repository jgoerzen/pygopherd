#!/usr/bin/python2.2

# Python-based gopher server
# Module: test utilities
# COPYRIGHT #
# Copyright (C) 2002 John Goerzen
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# END OF COPYRIGHT #


from pygopherd import initialization, logger
from StringIO import StringIO
import os

def getconfig():
    config = initialization.initconffile('conf/pygopherd.conf')
    config.set("pygopherd", "root", os.path.abspath('./testdata'))
    return config

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

