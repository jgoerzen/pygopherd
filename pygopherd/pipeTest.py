import os
import tempfile
import unittest

from pygopherd import pipe, testutil


class PipeTestCase(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
        self.root = self.config.get("pygopherd", "root")
        self.testdata = self.root + "/pygopherd/pipetestdata"
        self.testprog = self.root + "/pygopherd/pipetest.sh"

    def testWorkingPipe(self):
        outputfd = tempfile.TemporaryFile()
        inputfd = open(self.testdata, "rt")

        retval = pipe.pipedata(
            self.testprog, [self.testprog], childstdin=inputfd, childstdout=outputfd
        )
        outputfd.seek(0)

        self.assertEqual(
            outputfd.read(), "Starting\nGot [Word1]\nGot [Word2]\nGot [Word3]\nEnding\n"
        )
        self.assertTrue(os.WIFEXITED(retval), "WIFEXITED was not true")
        self.assertEqual(os.WEXITSTATUS(retval), 0)
        self.assertEqual(retval, 0)
        outputfd.close()

    def testFailingPipe(self):
        outputfd = tempfile.TemporaryFile()
