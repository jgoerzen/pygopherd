#!/usr/bin/python

# Python-based gopher server
# Module: test of gopherentry
# COPYRIGHT #
# Copyright (C) 2002 John Goerzen
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
# END OF COPYRIGHT #

import unittest, os, re
from pygopherd import testutil
from pygopherd.gopherentry import GopherEntry

fields = [
    "selector",
    "config",
    "fspath",
    "type",
    "name",
    "host",
    "port",
    "mimetype",
    "encodedmimetype",
    "size",
    "encoding",
    "populated",
    "language",
    "ctime",
    "mtime",
    "num",
    "gopherpsupport",
]


class GopherEntryTestCase(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
        self.root = self.config.get("pygopherd", "root")

    def assertEntryMatches(self, conditions, entry, testname):
        for field, value in list(conditions.items()):
            self.assertEqual(
                value,
                getattr(entry, field),
                "%s: Field '%s' expected '%s' but was '%s'"
                % (testname, field, value, getattr(entry, field)),
            )

    def testinit(self):
        entry = GopherEntry("/NONEXISTANT", self.config)
        conditions = {
            "selector": "/NONEXISTANT",
            "config": self.config,
            "populated": 0,
            "gopherpsupport": 0,
        }
        for x in [
            "fspath",
            "type",
            "name",
            "host",
            "port",
            "mimetype",
            "encodedmimetype",
            "size",
            "encoding",
            "language",
            "ctime",
            "mtime",
        ]:
            conditions[x] = None
        self.assertEntryMatches(conditions, entry, "testinit")

    def testpopulate_basic(self):
        fspath = "/testfile.txt"
        statval = os.stat(self.root + fspath)
        conditions = {
            "selector": "/testfile.txt",
            "config": self.config,
            "fspath": fspath,
            "type": "0",
            "name": "testfile.txt",
            "host": None,
            "port": None,
            "mimetype": "text/plain",
            "encodedmimetype": None,
            "encoding": None,
            "populated": 1,
            "language": None,
            "gopherpsupport": 1,
            "ctime": statval[9],
            "mtime": statval[8],
            "size": 5,
            "num": 0,
        }

        entry = GopherEntry("/testfile.txt", self.config)
        entry.populatefromfs(fspath)
        self.assertEntryMatches(conditions, entry, "testpopulate_basic")

        # Also try it with passed statval.

        entry = GopherEntry("/testfile.txt", self.config)
        entry.populatefromfs(fspath, statval)
        self.assertEntryMatches(
            conditions, entry, "testpopulate_basic with cached stat"
        )

        # Make sure it's a no-op if it's already populated.

        entry = GopherEntry("/NONEXISTANT", self.config)
        entry.populated = 1
        entry.populatefromfs(fspath)

        assert entry.gettype() is None

    def testpopulate_encoded(self):
        fspath = "/testfile.txt.gz"
        entry = GopherEntry("/testfile.txt.gz", self.config)
        entry.populatefromfs(fspath)

        self.assertEqual(entry.gettype(), "9")
        self.assertEqual(entry.getmimetype(), "application/octet-stream")
        self.assertEqual(entry.getencoding(), "gzip")
        self.assertEqual(entry.getencodedmimetype(), "text/plain")
        self.assertEqual(
            entry.geteadict(),
            {"ABSTRACT": b"This is the abstract\nfor testfile.txt.gz"},
        )

    def testpopulate_dir(self):
        fspath = self.root + "/"
        entry = GopherEntry("/", self.config)
        entry.populatefromfs("/")

        conditions = {
            "selector": "/",
            "config": self.config,
            "fspath": "/",
            "type": "1",
            "name": "",
            "host": None,
            "port": None,
            "mimetype": "application/gopher-menu",
            "encodedmimetype": None,
            "encoding": None,
            "populated": 1,
            "language": None,
            "gopherpsupport": 1,
        }

        self.assertEntryMatches(conditions, entry, "testpopulate_dir")
        self.assertEqual(
            entry.geteadict(),
            {"ABSTRACT": b"This is the abstract for the testdata directory."},
        )

    def testpopulate_remote(self):
        """Asserts that population is not done on remote objects."""
        selector = "/testfile.txt"
        fspath = self.root + selector
        entry = GopherEntry(selector, self.config)
        entry.host = "gopher.nowhere"
        entry.populatefromfs(fspath)
        assert entry.gettype() is None

        entry.populated = 0
        entry.host = None
        entry.port = 70
        entry.populatefromfs(fspath)
        assert entry.gettype() is None

        entry.populated = 0
        entry.host = "gopher.nowhere"
        entry.populatefromfs(fspath)
        assert entry.gettype() is None

    def testpopulate_untouched(self):
        """Asserts that populatefromfs does not touch data that has already
        been set."""

        selector = "/testfile.txt"
        fspath = selector

        entry = GopherEntry(selector, self.config)
        entry.name = "FAKE NAME"
        entry.ctime = 1
        entry.mtime = 2
        entry.populatefromfs(fspath)
        self.assertEntryMatches(
            {"name": "FAKE NAME", "ctime": 1, "mtime": 2},
            entry,
            "testpopulate_untouched",
        )

        # Reset for the next batch.
        entry = GopherEntry("/", self.config)

        # Test type for a dir.
        entry.type = "2"
        entry.mimetype = "FAKEMIMETYPE"
        entry.populatefromfs(self.root)
        self.assertEqual(entry.gettype(), "2")
        self.assertEqual(entry.getmimetype(), "FAKEMIMETYPE")

        # Test mime type handling.  First, regular file.

        entry = GopherEntry(selector, self.config)
        entry.mimetype = "fakemimetype"
        entry.populatefromfs(fspath)
        self.assertEqual(entry.getmimetype(), "fakemimetype")
        # The guesstype will not find fakemimetype and so it'll set it to 0
        self.assertEqual(entry.gettype(), "0")

        # Now, an encoded file.

        entry = GopherEntry(selector + ".gz", self.config)
        entry.mimetype = "fakemime"
        entry.populatefromfs(fspath + ".gz")
        self.assertEqual(entry.getmimetype(), "fakemime")
        self.assertEqual(entry.getencoding(), "gzip")
        self.assertEqual(entry.getencodedmimetype(), "text/plain")
        self.assertEqual(entry.gettype(), "0")  # again from fakemime

        # More details.

        selector = "/testarchive.tgz"
        fspath = selector
        entry = GopherEntry(selector, self.config)
        entry.mimetype = "foo1234"
        entry.encoding = "bar"
        entry.populatefromfs(fspath)
        self.assertEqual(entry.getmimetype(), "foo1234")
        self.assertEqual(entry.getencoding(), "bar")
        self.assertEqual(entry.getencodedmimetype(), "application/x-tar")
        self.assertEqual(entry.gettype(), "0")

        # And overriding only the encoding.

        entry = GopherEntry(selector, self.config)
        entry.encoding = "fakeencoding"
        entry.populatefromfs(fspath)
        self.assertEqual(entry.getencoding(), "fakeencoding")
        self.assertEqual(entry.gettype(), "9")
        self.assertEqual(entry.getmimetype(), "application/octet-stream")

        # And finally -- overriding the encoded mime type.

        entry = GopherEntry(selector, self.config)
        entry.encodedmimetype = "fakeencoded"
        entry.populatefromfs(fspath)
        self.assertEqual(entry.getencodedmimetype(), "fakeencoded")
        self.assertEqual(entry.getmimetype(), "application/octet-stream")

    def test_guesstype(self):
        entry = GopherEntry("/NONEXISTANT", self.config)
        expected = {
            "text/plain": "0",
            "application/gopher-menu": "1",
            "application/gopher+-menu": "1",
            "text/html": "h",
            "image/gif": "g",
            "image/jpeg": "I",
            "application/pdf": "9",
            "application/msword": "9",
            "audio/aiff": "s",
        }

        for mimetype, type in list(expected.items()):
            entry.mimetype = mimetype
            self.assertEqual(
                entry.guesstype(),
                type,
                "Failure for %s: got %s, expected %s"
                % (mimetype, entry.guesstype(), type),
            )

    def test_gets_sets(self):
        """Tests a bunch of gets that operate on values that are None
        to start with, and take a default."""

        entry = GopherEntry("/NONEXISTANT", self.config)
        # Initialize the rest of them to None.
        entry.selector = None
        entry.config = None
        entry.populated = None
        entry.num = None
        entry.gopherpsupport = None

        for field in fields:
            getfunc = getattr(entry, "get" + field)
            setfunc = getattr(entry, "set" + field)
            self.assertEqual(getfunc(), None)
            self.assertEqual(getfunc("DEFAULT" + field), "DEFAULT" + field)
            setfunc("NewValue" + field)
            self.assertEqual(getfunc(), "NewValue" + field)
            self.assertEqual(getfunc("DEFAULT"), "NewValue" + field)

    def testgeturl(self):
        expected = {
            "/URL:http://www.complete.org/%20/": "http://www.complete.org/%20/",
            "URL:telnet://foo.com/%20&foo=bar": "telnet://foo.com/%20&foo=bar",
            "/foo": "gopher://MISSINGHOST:70/0/foo",
            "/About Me.txt": "gopher://MISSINGHOST:70/0/About%20Me.txt",
            "/": "gopher://MISSINGHOST:70/0/",
        }
        for selector, url in list(expected.items()):
            entry = GopherEntry(selector, self.config)
            entry.settype("0")
            self.assertEqual(url, entry.geturl())
            self.assertEqual(
                re.sub("MISSINGHOST", "NEWHOST", url), entry.geturl("NEWHOST")
            )
            self.assertEqual(
                re.sub("70", "10101", url), entry.geturl(defaultport=10101)
            )
            entry.sethost("newhost")
            self.assertEqual(re.sub("MISSINGHOST", "newhost", url), entry.geturl())
            entry.setport(80)
            self.assertEqual(
                re.sub("MISSINGHOST:70", "newhost:80", url), entry.geturl()
            )
