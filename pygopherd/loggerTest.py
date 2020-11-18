import unittest
from pygopherd import logger, testutil


class LoggerTestCase(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
