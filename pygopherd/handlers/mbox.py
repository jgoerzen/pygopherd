# pygopherd -- Gopher-based protocol server in Python
# module: Present a mbox file as if it were a folder.
# Copyright (C) 2002, 2005 John Goerzen
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

import io
import os.path
import re
import typing
import unittest
import stat
from mailbox import Maildir, Message, mbox

from pygopherd import gopherentry
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.virtual import Virtual

###########################################################################
# Basic mailbox support
###########################################################################


class FolderHandler(Virtual):

    mbox: typing.Union[mbox, Maildir]

    def getentry(self):
        # Return my own entry.
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.getselector(), self.config)
            self.entry.settype("1")
            self.entry.setname(os.path.basename(self.getselector()))
            self.entry.setmimetype("application/gopher-menu")
            self.entry.setgopherpsupport(0)
        return self.entry

    def prepare(self):
        self.entries = []
        for key, message in self.mbox.iteritems():
            handler = MessageHandler(
                self.genargsselector(self.getargflag() + str(key)),
                self.searchrequest,
                self.protocol,
                self.config,
                None,
            )
            self.entries.append(handler.getentry(message))

    def isdir(self):
        return True

    def getdirlist(self):
        return self.entries

    def getargflag(self) -> str:
        raise NotImplementedError


class MessageHandler(Virtual):

    msgnum: int
    message: Message

    def canhandlerequest(self):
        """We put MBOX-MESSAGE in here so we don't have to re-check
        the first line of the mbox file before returning a true or false
        result."""
        if not self.selectorargs:
            return False
        msgnum = re.search("^" + self.getargflag() + r"(\d+)$", self.selectorargs)
        if not msgnum:
            return False
        self.msgnum = int(msgnum.group(1))
        return True

    def getentry(self, message=None):
        """Set the message if called from, eg, the dir handler.  Saves
        having to rescan the file.  If not set, will figure it out."""
        if not message:
            message = self.getmessage()

        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            self.entry.settype("0")
            self.entry.setmimetype("text/plain")
            self.entry.setgopherpsupport(0)

            subject = message.get("Subject", "<no subject>")
            # Sanitize, esp. for continuations.
            subject = re.sub(r"\s+", " ", subject)
            if subject:
                self.entry.setname(subject)
            else:
                self.entry.setname("<no subject>")
        return self.entry

    def getmessage(self):
        if hasattr(self, "message"):
            return self.message

        mbox = self.openmailbox()
        self.message = mbox.get_message(self.msgnum)
        return self.message

    def prepare(self):
        self.canhandlerequest()  # Init the vars

    def write(self, wfile):
        message = self.getmessage()
        wfile.write(message.as_bytes())

    def getargflag(self) -> str:
        raise NotImplementedError

    def openmailbox(self):
        raise NotImplementedError


###########################################################################
# Unix MBOX support
###########################################################################
class MBoxFolderHandler(FolderHandler):
    def canhandlerequest(self):
        """Figure out if this is a handleable request."""
        # Must be a real file
        if (
            not isinstance(self.vfs, VFS_Real)
            or self.selectorargs
            or not self.statresult
            or not stat.S_ISREG(self.statresult[stat.ST_MODE])
        ):
            return False

        try:
            with self.vfs.open(self.getselector(), "rb") as fd:
                startline = fd.readline()
        except IOError:
            return False

        # Python 2 had an old "UnixMailbox" class that had more strict
        # pattern matching on the message "From:" line. This was deprecated
        # as early as python 2.5 and was dropped completely in python 3.
        # Since we are using the first line of the file to determine if the
        # filetype is a mbox or not, it's safer to be stricter with the
        # pattern matching and port over the old UnixMailbox pattern.
        fromlinepattern = (
            rb"From \s*[^\s]+\s+\w\w\w\s+\w\w\w\s+\d?\d\s+"
            rb"\d?\d:\d\d(:\d\d)?(\s+[^\s]+)?\s+\d\d\d\d\s*"
            rb"[^\s]*\s*"
            b"$"
        )
        return re.match(fromlinepattern, startline)

    def prepare(self):
        self.mbox = mbox(self.getfspath(), create=False)
        super().prepare()

    def getargflag(self):
        return "/MBOX-MESSAGE/"


class MBoxMessageHandler(MessageHandler):
    def getargflag(self):
        return "/MBOX-MESSAGE/"

    def openmailbox(self):
        return mbox(self.getfspath(), create=False)


class TestMBoxFolderHandler(unittest.TestCase):
    def setUp(self) -> None:
        from pygopherd import testutil

        self.config = testutil.getconfig()
        self.vfs = VFS_Real(self.config)
        self.selector = "/python-dev.mbox"
        self.protocol = testutil.gettestingprotocol(self.selector, config=self.config)
        self.stat_result = self.vfs.stat(self.selector)

    def test_mbox_folder_handler(self):
        handler = MBoxFolderHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )
        handler.prepare()

        self.assertTrue(handler.canhandlerequest())
        self.assertTrue(handler.isdir())

        entry = handler.getentry()
        self.assertEqual(entry.mimetype, "application/gopher-menu")
        self.assertEqual(entry.type, "1")

        mbox_entries = handler.getdirlist()
        self.assertTrue(len(mbox_entries), 6)
        self.assertEqual(mbox_entries[0].selector, "/python-dev.mbox|/MBOX-MESSAGE/0")
        self.assertEqual(mbox_entries[0].name, "[Python-Dev] Pickling w/ low overhead")

    def test_mbox_mesage_handler(self):
        """
        Load the third message from the mailbox.
        """
        handler = MBoxMessageHandler(
            "/python-dev.mbox|/MBOX-MESSAGE/2",
            "",
            self.protocol,
            self.config,
            self.stat_result,
            self.vfs,
        )
        handler.prepare()

        self.assertTrue(handler.canhandlerequest())
        self.assertFalse(handler.isdir())

        entry = handler.getentry()
        self.assertEqual(entry.mimetype, "text/plain")
        self.assertEqual(entry.name, "Re: [Python-Dev] Buffer interface in abstract.c?")
        self.assertEqual(entry.type, "0")

        wfile = io.BytesIO()
        handler.write(wfile)
        email_text = wfile.getvalue()
        assert email_text.startswith(b"From: Greg Stein <gstein@lyra.org>")


###########################################################################
# Maildir support
###########################################################################


class MaildirFolderHandler(FolderHandler):
    def canhandlerequest(self):
        if not isinstance(self.vfs, VFS_Real):
            return 0
        if self.selectorargs:
            return 0
        if not (self.statresult and stat.S_ISDIR(self.statresult[stat.ST_MODE])):
            return 0
        return self.vfs.isdir(self.getselector() + "/new") and self.vfs.isdir(
            self.getselector() + "/cur"
        )

    def prepare(self):
        self.mbox = Maildir(self.getfspath())
        FolderHandler.prepare(self)

    def getargflag(self):
        return "/MAILDIR-MESSAGE/"


class MaildirMessageHandler(MessageHandler):
    def getargflag(self):
        return "/MAILDIR-MESSAGE/"

    def openmailbox(self):
        return Maildir(self.getfspath())
