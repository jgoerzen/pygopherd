# pygopherd -- Gopher-based protocol server in Python
# module: base handler code
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from __future__ import annotations

import configparser
import typing
import os
import os.path

from pygopherd import gopherentry

if typing.TYPE_CHECKING:
    from pygopherd.gopherentry import GopherEntry
    from pygopherd.protocols.base import BaseGopherProtocol


rootpath = None


class VFS_Real:
    def __init__(
        self, config: configparser.ConfigParser, chain: typing.Optional[VFS_Real] = None
    ):
        """This implementation does not chain."""
        self.config = config
        self.chain = chain

    def iswritable(self, selector: str) -> bool:
        return True

    def unlink(self, selector: str) -> None:
        os.unlink(self.getfspath(selector))

    def stat(self, selector: str) -> os.stat_result:
        return os.stat(self.getfspath(selector))

    def isdir(self, selector: str) -> bool:
        return os.path.isdir(self.getfspath(selector))

    def isfile(self, selector: str) -> bool:
        return os.path.isfile(self.getfspath(selector))

    def exists(self, selector: str) -> bool:
        return os.path.exists(self.getfspath(selector))

    def open(
        self, selector: str, mode: str, errors: typing.Optional[str] = None
    ) -> typing.IO:
        return open(self.getfspath(selector), mode, errors=errors)

    def listdir(self, selector: str) -> typing.List[str]:
        return os.listdir(self.getfspath(selector))

    def getrootpath(self) -> str:
        global rootpath
        if not rootpath:
            rootpath = self.config.get("pygopherd", "root")
        return rootpath

    def getfspath(self, selector: str) -> str:
        """Gets the filesystem path corresponding to the selector."""

        fspath = self.getrootpath() + selector
        # Strip off trailing slash.
        if fspath[-1] == "/":
            fspath = fspath[0:-1]

        return fspath

    def copyto(self, name: str, fd: typing.IO[bytes]) -> None:
        with self.open(name, "rb") as rfile:
            while 1:
                data = rfile.read(4096)
                if not len(data):
                    break
                fd.write(data)


class BaseHandler:
    """Skeleton handler -- includes commonly-used routines."""

    def __init__(
        self,
        selector: str,
        searchrequest: str,
        protocol: BaseGopherProtocol,
        config: configparser.ConfigParser,
        statresult: os.stat_result,
        vfs: typing.Optional[VFS_Real] = None,
    ):
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
        if not vfs:
            self.vfs = VFS_Real(self.config)
        else:
            self.vfs = vfs

    def isrequestforme(self) -> bool:
        """Called by multiplexers or other handlers.  The default
        implementation is just:

        return self.isrequestsecure() and self.canhandlerequest()
        """
        return self.isrequestsecure() and self.canhandlerequest()

    def isrequestsecure(self) -> bool:
        """An auxiliary to canhandlerequest.  In order for this handler
        to be selected for handling a given request, both the securitycheck
        and the canhandlerequest should be invoked.  The securitycheck is
        intended to be a short, small, quick check -- usually not even
        looking at the filesystem.  Here is a default.  Returns true
        if the request is secure, false if not.  By default, we eliminate
        ./, ../, and //  This is split out from canhandlerequest becase
        it could be too easy to forget about it there."""
        return (
            (self.selector.find("./") == -1)
            and (self.selector.find("..") == -1)
            and (self.selector.find("//") == -1)
            and (self.selector.find(".\\") == -1)
            and (self.selector.find("\\\\") == -1)
            and (self.selector.find("\0") == -1)
        )

    def canhandlerequest(self) -> bool:
        """Decides whether or not a given request is valid for this
        handler.  Should be overridden by all subclasses."""
        return False

    def getentry(self) -> gopherentry.GopherEntry:
        """Returns an entry object for this request."""
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
        return self.entry

    def getfspath(self) -> str:
        if not self.fspath:
            self.fspath = self.vfs.getfspath(self.getselector())
        return self.fspath

    def getselector(self) -> str:
        """Returns the selector we are handling."""
        return self.selector

    def gethandler(self) -> BaseHandler:
        """Returns the handler to use to process this request.  For all
        but special cases (rewriting handleres, for instance), this should
        return self."""
        return self

    ## The next three are the publically-exposed interface -- the ones
    ## called by things other than handlers.

    def prepare(self) -> None:
        """Prepares for a write.  Ie, opens a file.  This is
        used so that the protocols can try to detect an error before
        transmitting a result.  Must always be called before write."""
        pass

    def isdir(self) -> bool:
        """Returns true if this handler is handling a directory; false
        otherwise.  Not valid unless prepare has been called."""

        return False

    def write(self, wfile):
        """Writes out the request if isdir() returns false.  You should
        NOT call write if isdir() returns true!  Should be overridden
        by files."""
        if self.isdir():
            raise Exception("Attempt to use write for a directory")

    def getdirlist(self) -> typing.Iterable[GopherEntry]:
        """Returns a list-like object (list, iterator, tuple, generator, etc)
        that contains as its elements the gopherentry objects corresponding
        to each item in the directory.  Valid only if self.isdir() returns
        true."""
        if not self.isdir():
            raise Exception("Attempt to use getdir for a file.")
        return []
