"""unittests for the server module"""

import os
import unittest

import server

class TestDefaultSubprocess(unittest.TestCase):
    """Test the subprocess based server."""

    def setUp(self):
        """The fixture is just the default subprocess object"""
        # constantly killing nethack messes up the locks
        os.system(b'rm ~/nh/install/games/lib/nethackdir/*lock* 2> /dev/null')
        # tests shouldn't use a savefile
        os.system(b'rm ~/nh/install/games/lib/nethackdir/save/* 2> /dev/null')
        self.server = server.default_subprocess()

    def tearDown(self):
        """Terminate after each test"""
        self.server.terminate()

    def test_startup(self):
        """Simple test, see if the subprocess will start and produce some output."""
        data = self.server.read()
        self.assertTrue(data)

    def test_input(self):
        """Test basic input/output flow. Read data until no more available. Then
           input a space and verify that more output is produced in response."""
        data = self.server.read()
        while data:
            data = self.server.read()
        self.server.write(b' ')
        data = self.server.read()
        #print(data)
        self.assertTrue(data)

if __name__ == '__main__':
    unittest.main()
