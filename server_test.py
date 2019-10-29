"""unittests for the server module"""

import os
import unittest

import parser
import server

class TestDefaultSubprocess(unittest.TestCase):
    """Test the subprocess based server."""

    def setUp(self):
        """The fixture is just the default subprocess object. It assumes
           complete control of an appropriate version of nethack installed
           in the users home directory. Any save data and locks are cleared
           before each test for consistency."""
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

    def test_parser(self):
        """Send some 'canned' output to the server and parse the result. Really
           a test for the parser, but easier to implement here. Just verifying
           the parser can handle some "real" nethack output, even if it's
           unpredictable."""
        parser_ = parser.Parser()
        output = list() # for debugging

        def parse_loop():
            """Read and parse until the read timeout"""
            while True:
                data = self.server.read()
                if not data:
                    break
                #print(data)
                output.append(data) # debugging
                parser_.parse_bytes(data)
            self.assertTrue(parser_.end_of_data)

        parse_loop()
        self.server.write(b'y')
        parse_loop()
        self.server.write(b'y')
        parse_loop()
        self.server.write(b'\n')
        parse_loop()

    def test_num_lines(self):
        """Send some 'canned' output to the server and parse the result. Really
           a test for the parser, but easier to implement here. Just verifying
           the parser can handle some "real" nethack output, even if it's
           unpredictable."""
        parser_ = parser.Parser()
        output = list() # for debugging

        def parse_loop():
            """Read and parse until the read timeout"""
            while True:
                data = self.server.read()
                if not data:
                    break
                #print(data)
                output.append(data) # debugging
                parser_.parse_bytes(data)
            self.assertTrue(parser_.end_of_data)

        parse_loop()
        self.server.write(b'y') # shall I pick your class
        parse_loop()
        self.server.write(b'y') # is this OK?
        parse_loop()
        self.server.write(b' ') # Go bravely!
        parse_loop()
        self.server.write(b' ') # Welcome to nethack
        parse_loop()
        self.server.write(b'?') # Help command
        parse_loop()
        self.server.write(b'i') # list of all commands
        parse_loop()
        #print(output)

if __name__ == '__main__':
    unittest.main()
