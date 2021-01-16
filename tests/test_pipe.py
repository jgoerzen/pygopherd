import os
import subprocess
import tempfile
import unittest

from pygopherd import testutil


class PipeTestCase(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
        self.root = self.config.get("pygopherd", "root")
        self.testdata = self.root + "/pygopherd/pipetestdata"
        self.testprog = self.root + "/pygopherd/pipetest.sh"

    def testWorkingPipe(self):
        with tempfile.TemporaryFile(mode="w+") as outputfd:
            with open(self.testdata, "r") as inputfd:
                retval = subprocess.run(
                    [self.testprog],
                    stdin=inputfd,
                    stdout=outputfd,
                    errors="surrogateescape",
                )
                outputfd.seek(0)

                self.assertEqual(
                    outputfd.read(),
                    "Starting\nGot [Word1]\nGot [Word2]\nGot [Word3]\nEnding\n",
                )

            self.assertTrue(os.WIFEXITED(retval.returncode), "WIFEXITED was not true")
            self.assertEqual(os.WEXITSTATUS(retval.returncode), 0)
            self.assertEqual(retval.returncode, 0)

    def testFailingPipe(self):
        pass
