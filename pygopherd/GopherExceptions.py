# pygopherd -- Gopher-based protocol server in Python
# module: exception declarations
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
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

import types, re
from pygopherd import logger

tracebacks = 0

def log(exception, protocol = None, handler = None):
    """Logs an exception.  It will try to generate a nice-looking string
    based on the arguments passed in."""
    protostr = 'None'
    handlerstr = 'None'
    ipaddr = 'unknown-address'
    exceptionclass = re.search("[^.]+$", str(exception.__class__)).group(0)
    if protocol:
        protostr = re.search("[^.]+$", str(protocol.__class__)).group(0)
        ipaddr = protocol.requesthandler.client_address[0]
    if handler:
        handlerstr = re.search("[^.]+$", str(handler.__class__)).group(0)
    
    logger.log("%s [%s/%s] EXCEPTION %s: %s" % \
               (ipaddr, protostr, handlerstr, exceptionclass,
                str(exception)))

def init(backtraceenabled):
    global tracebacks
    tracebacks = backtraceenabled

class FileNotFound:
    def __init__(self, arg):
        self.selector = arg
        self.comments = ''
        self.protocol = ''

        if type(arg) != types.StringType:
            self.selector = arg[0]
            self.comments = arg[1]
            if len(arg) > 2 and arg[2]:
                self.protocol = arg[2]

        log(self, self.protocol, None)

    def __str__(self):
        retval = "'%s' does not exist" % (self.selector)
        if self.comments:
            retval += " (%s)" % self.comments

        return retval
