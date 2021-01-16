import os.path
import re
import stat
import typing
from mailbox import Maildir, Message, mbox

from pygopherd import gopherentry
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.virtual import Virtual


class FolderHandler(Virtual):

    mbox: typing.Union[mbox, Maildir]
    entries: typing.List[gopherentry.GopherEntry]

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

        for index, message in enumerate(self.mbox, start=1):
            handler = MessageHandler(
                self.genargsselector(self.getargflag() + str(index)),
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

    message_num: int
    message: Message

    def canhandlerequest(self):
        """We put MBOX-MESSAGE in here so we don't have to re-check
        the first line of the mbox file before returning a true or false
        result."""
        if not self.selectorargs:
            return False

        pattern = "^" + self.getargflag() + r"(\d+)$"
        match = re.search(pattern, self.selectorargs)
        if match is None:
            return False

        message_num = int(match.groups()[0])
        if message_num < 1:
            return False

        self.message_num = message_num
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

    def getmessage(self) -> Message:
        if hasattr(self, "message"):
            return self.message

        mailbox = iter(self.openmailbox())
        message = None
        for _ in range(self.message_num):
            message = next(mailbox)

        self.message = message
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
        super().prepare()

    def getargflag(self):
        return "/MAILDIR-MESSAGE/"


class MaildirMessageHandler(MessageHandler):
    def getargflag(self):
        return "/MAILDIR-MESSAGE/"

    def openmailbox(self):
        return Maildir(self.getfspath(), create=False)
