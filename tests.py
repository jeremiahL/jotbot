
import unittest

import os
import time
import server

class TestDefaultSubprocess(unittest.TestCase):

    def setUp(self):
        # constantly killing nethack messes up the locks
        os.system(b'rm ~/nh/install/games/lib/nethackdir/*lock* 2> /dev/null')
        # tests shouldn't use a savefile
        os.system(b'rm ~/nh/install/games/lib/nethackdir/save/* 2> /dev/null')
        self.nh = server.default_subprocess()

    def tearDown(self):
        self.nh.terminate()

    def test_startup(self):
        data = self.nh.read()
        self.assertTrue(data, msg="Some output from nethack")

    def test_input(self):
        data = self.nh.read()
        while data:
            data = self.nh.read()
        self.nh.write(b' ')
        data = self.nh.read()
        print(data)
        self.assertTrue(data, msg="Input didn't create more output")

if __name__ == '__main__':
    unittest.main() 
