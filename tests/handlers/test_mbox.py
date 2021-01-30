import io
import unittest

from pygopherd import testutil
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.mbox import (
    MaildirFolderHandler,
    MaildirMessageHandler,
    MBoxFolderHandler,
    MBoxMessageHandler,
)


class TestMBoxHandler(unittest.TestCase):
    def setUp(self):
        self.config = testutil.get_config()
        self.vfs = VFS_Real(self.config)
        self.selector = "/python-dev.mbox"
        self.protocol = testutil.get_testing_protocol(self.selector, config=self.config)
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

        messages = handler.getdirlist()
        self.assertTrue(len(messages), 6)
        self.assertEqual(messages[0].selector, "/python-dev.mbox|/MBOX-MESSAGE/1")
        self.assertEqual(messages[0].name, "[Python-Dev] Pickling w/ low overhead")

    def test_mbox_message_handler(self):
        """
        Load the third message from the mbox.
        """
        handler = MBoxMessageHandler(
            "/python-dev.mbox|/MBOX-MESSAGE/3",
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


class TestMaildirHandler(unittest.TestCase):
    """
    The maildir test data was generated from a mailbox file using this script:

    http://batleth.sapienti-sat.org/projects/mb2md/

    Important Note: The python implementation uses os.listdir() under the
    hood to iterate over the mail files in the directory. The order of
    files returned is deterministic but is *not* sorted by filename. This
    means that mail files in the generated gopher directory listing may
    appear out of order from their "true" ordering in the mail archive.
    It also makes writing this test a pain in the ass.
    """

    def setUp(self):
        self.config = testutil.get_config()
        self.vfs = VFS_Real(self.config)
        self.selector = "/python-dev"
        self.protocol = testutil.get_testing_protocol(self.selector, config=self.config)
        self.stat_result = self.vfs.stat(self.selector)

    def test_maildir_folder_handler(self):
        handler = MaildirFolderHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )
        handler.prepare()

        self.assertTrue(handler.canhandlerequest())
        self.assertTrue(handler.isdir())

        entry = handler.getentry()
        self.assertEqual(entry.mimetype, "application/gopher-menu")
        self.assertEqual(entry.type, "1")

        messages = handler.getdirlist()
        self.assertTrue(len(messages), 6)
        self.assertEqual(messages[0].selector, "/python-dev|/MAILDIR-MESSAGE/1")
        self.assertIn("[Python-Dev]", messages[0].name)

    def test_maildir_message_handler(self):
        """
        Load the third message from the maildir.
        """
        handler = MaildirMessageHandler(
            "/python-dev|/MAILDIR-MESSAGE/3",
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
        self.assertEqual(entry.type, "0")

        wfile = io.BytesIO()
        handler.write(wfile)
        email_text = wfile.getvalue()
        assert email_text.startswith(b"From:")
