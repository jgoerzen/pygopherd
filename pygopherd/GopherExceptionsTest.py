import unittest
from StringIO import StringIO
from pygopherd import logger, initialization, GopherExceptions

class GopherExceptionsTestCase(unittest.TestCase):
    def setUp(self):
        self.stringfile = StringIO()
        self.config = initialization.initconffile('conf/pygopherd.conf')
        self.config.set('logger', 'logmethod', 'file')
        logger.init(self.config)
        logger.setlogfile(self.stringfile)
        GopherExceptions.tracebacks = 0

    def testlog_basic(self):
        try:
            raise IOError, "foo"
        except IOError, e:
            GopherExceptions.log(e)
        self.assertEqual(self.stringfile.getvalue(),
                         "unknown-address [None/None] IOError: foo\n")

        
