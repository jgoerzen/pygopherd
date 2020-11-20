import unittest
from pygopherd import testutil


class LoggerTestCase(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
