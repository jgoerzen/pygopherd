# pygopherd -- Gopher-based protocol server in Python
# module: base handler code
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

import SocketServer
import re
import os, stat, os.path, mimetypes
from pygopherd import protocols, handlers, gopherentry

rootpath = None

class BaseHandler:
    """Skeleton handler -- includes commonly-used routines."""
    def __init__(self, selector, searchrequest, protocol, config, statresult):
        """Parameters are:
        selector -- requested selector.  The selector must always start
        with a slash and never end with a slash UNLESS it is a one-char
        selector that contains only a slash.  This should be handled
        by the default protocol.

        config -- config object."""
        self.selector = selector
        self.searchrequest = searchrequest
        self.protocol = protocol
        self.config = config
        self.statresult = statresult
        self.fspath = None
        self.entry = None
        self.searchrequest = searchrequest

    def isrequestforme(self):
        """Called by multiplexers or other handlers.  The default
        implementation is just:

        return self.isrequestsecure() and self.canhandlerequest()
        """
        return self.isrequestsecure() and self.canhandlerequest()

    def isrequestsecure(self):
        """An auxiliary to canhandlerequest.  In order for this handler
        to be selected for handling a given request, both the securitycheck
        and the canhandlerequest should be invoked.  The securitycheck is
        intended to be a short, small, quick check -- usually not even
        looking at the filesystem.  Here is a default.  Returns true
        if the request is secure, false if not.  By default, we eliminate
        ./, ../, and //"""
        print "isrequestsecure on", self.selector
        print "First test result", self.selector.find("./")
        return (self.selector.find("./") == -1) and \
               (self.selector.find("..") == -1) and \
               (self.selector.find("//") == -1) and \
               (self.selector.find(".\\") == -1) and \
               (self.selector.find("\\\\") == -1) and \
               (self.selector.find("\0") == -1)
        

    def canhandlerequest(self):
        """Decides whether or not a given request is valid for this
        handler.  Should be overridden by all subclasses."""
        return 0

    def getentry(self):
        """Returns an entry object for this request."""
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
        return self.entry

    def getrootpath(self):
        """Gets the root path."""
        global rootpath
        if not rootpath:
            rootpath = self.config.get("pygopherd", "root")
        return rootpath

    def getfspath(self):
        """Gets the filesystem path corresponding to the selector."""
        if self.fspath:
            return self.fspath

        self.fspath = self.getrootpath() + self.getselector()
        # Strip off trailing slash.
        if self.fspath[-1] == '/':
            self.fspath = self.fspath[0:-1]

        return self.fspath

    def prepare(self):
        """Prepares for a write.  Ie, opens a file.  This is
        used so that the protocols can try to detect an error before
        transmitting a result.  Must always be called before write."""
        pass

    def write(self, wfile):
        """Writes out the request.  Should be overridden."""
        pass

    def getselector(self):
        return self.selector

