#!/usr/bin/env python3
import sys
import tracemalloc
import unittest

if __name__ == "__main__":
    tracemalloc.start()

    suite = unittest.defaultTestLoader.discover(start_dir="tests/")
    runner = unittest.TextTestRunner(verbosity=2)
    sys.exit(not runner.run(suite).wasSuccessful())
