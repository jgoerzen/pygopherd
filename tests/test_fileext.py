#!/usr/bin/python
import unittest

from pygopherd import fileext, initialization, testutil


class FileExtTestCase(unittest.TestCase):
    def setUp(self):
        config = testutil.getconfig()
        initialization.initlogger(config, "TESTING")
        initialization.initmimetypes(config)

    def testinit(self):
        # Was already inited in the initmimetypes, so just do a sanity
        # check.
        self.assertTrue(".txt" in fileext.typemap["text/plain"])
        self.assertTrue(".txt.gz" in fileext.typemap["text/plain"])
        self.assertTrue(not (".html" in fileext.typemap["text/plain"]))
