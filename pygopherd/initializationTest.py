import unittest, SocketServer, mimetypes
from pygopherd import initialization

from pygopherd import logger, fileext


class initializationConfigTestCase(unittest.TestCase):
    def testinitconffile(self):
        self.assertRaises(Exception, initialization.initconffile,
                          '/foo')
        # Load the standard config file.  It should be OK at least.
        config = initialization.initconffile('conf/pygopherd.conf')
        assert not config.has_option("pygopherd", "servername"), \
               "servername should be disabled by default"
        self.assertEqual(config.getint("pygopherd", "port"), 70,
               "Port should be 70")
        self.assertEqual(config.get("pygopherd", "servertype"),
                         "ForkingTCPServer",
                         "Servertype should be ForkingTCPServer")
        assert config.getboolean("pygopherd", "tracebacks"), \
               "Tracebacks should be enabled."

class initializationGeneralTestCase(unittest.TestCase):
    def setUp(self):
        self.config = initialization.initconffile('conf/pygopherd.conf')

    def testinitlogger(self):
        # FIXME Can't really test this.
        pass

    def testinitmimetypes_except(self):
        self.config.set("pygopherd", "mimetypes", "/foo:/bar")
        self.assertRaises(Exception, initialization.initmimetypes,
                          self.config)

    def testinitmimetypes(self):
        # Logger is required for this test.
        self.config.set("logger", "logmethod", "none")
        initialization.initlogger(self.config, 'TESTING')
        initialization.initmimetypes(self.config)
        self.assertEqual(mimetypes.types_map['.txt'], 'text/plain')
        self.assertEqual(mimetypes.encodings_map['.bz2'], 'bzip2')
        assert '.txt' in fileext.typemap['text/plain']

    def testgetserverobject(self):
        self.config.set("pygopherd", "port", "22270")
        s = initialization.getserverobject(self.config)
        assert isinstance(s, SocketServer.ForkingTCPServer)

    def testinitsecurity(self):
        #FIXME
        pass
    
