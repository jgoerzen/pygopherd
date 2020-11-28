# pygopherd -- Gopher-based protocol server in Python
# module: Script execution
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

import os
import stat
import subprocess
import tempfile
import unittest

from pygopherd import gopherentry
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.virtual import Virtual


class ExecHandler(Virtual):
    def canhandlerequest(self):
        # We ONLY handle requests from the real filesystem.
        return (
            isinstance(self.vfs, VFS_Real)
            and self.statresult
            and stat.S_ISREG(self.statresult[stat.ST_MODE])
            and (stat.S_IMODE(self.statresult[stat.ST_MODE]) & stat.S_IXOTH)
        )

    def getentry(self):
        entry = gopherentry.GopherEntry(self.getselector(), self.config)
        entry.settype("0")
        entry.setname(os.path.basename(self.getselector()))
        entry.setmimetype("text/plain")
        entry.setgopherpsupport(0)
        return entry

    def write(self, wfile):
        newenv = os.environ.copy()
        newenv["SERVER_NAME"] = self.protocol.server.server_name
        newenv["SERVER_PORT"] = str(self.protocol.server.server_port)
        newenv["REMOTE_ADDR"] = self.protocol.requesthandler.client_address[0]
        newenv["REMOTE_PORT"] = str(self.protocol.requesthandler.client_address[1])
        newenv["REMOTE_HOST"] = newenv["REMOTE_ADDR"]
        newenv["SELECTOR"] = self.selector
        newenv["REQUEST"] = self.getselector()
        if self.searchrequest:
            newenv["SEARCHREQUEST"] = self.searchrequest
        wfile.flush()

        args = [self.getfspath()]
        if self.selectorargs:
            args.extend(self.selectorargs.split(" "))

        subprocess.run(args, env=newenv, stdout=wfile, errors="surrogateescape")


class TestExecHandler(unittest.TestCase):
    def setUp(self) -> None:
        from pygopherd import testutil

        self.config = testutil.getconfig()
        self.vfs = VFS_Real(self.config)
        # The "hello" will be sent as an additional script argument. Multiple
        # query arguments can be provided using " " as the separator.
        self.selector = "/pygopherd/cgitest.sh?hello"
        self.protocol = testutil.gettestingprotocol(self.selector, config=self.config)
        self.stat_result = None

    def test_exec_handler(self):
        handler = ExecHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )

        self.assertTrue(handler.isrequestforme())

        entry = handler.getentry()
        self.assertEqual(entry.mimetype, "text/plain")
        self.assertEqual(entry.type, "0")
        self.assertEqual(entry.name, "cgitest.sh")
        self.assertEqual(entry.selector, "/pygopherd/cgitest.sh")

        # The test script will print $REQUEST and exit
        with tempfile.TemporaryFile(mode="w+") as wfile:
            handler.write(wfile)
            wfile.seek(0)
            output = wfile.read()
            self.assertEqual(output, "hello from /pygopherd/cgitest.sh\n")
