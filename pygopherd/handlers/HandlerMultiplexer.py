# pygopherd -- Gopher-based protocol server in Python
# module: find the right handler for a request
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

from pygopherd import handlers, GopherExceptions, logger
from pygopherd.handlers import *
import os, re

handlers = None
rootpath = None

def getHandler(selector, searchrequest, protocol, config):
    global handlers, rootpath

    if not handlers:
        handlers = eval(config.get("handlers.HandlerMultiplexer", "handlers"))
        rootpath = config.get("pygopherd", "root")

    # SECURITY: assert that our absolute path is within the absolute
    # path of the site root.

    if not os.path.abspath(rootpath + '/' + selector). \
       startswith(os.path.abspath(rootpath)):
        raise GopherExceptions.FileNotFound, \
              [selector, "Requested document is outside the server root",
               protocol]

    for handler in handlers:
        statresult = None
        try:
            statresult = os.stat(rootpath + '/' + selector)
        except OSError:
            pass
        htry = handler(selector, searchrequest, protocol, config, statresult)
        if htry.canhandlerequest():
            return htry
    
    raise GopherExceptions.FileNotFound, \
          [selector, "no handler found", protocol]
