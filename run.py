#!/usr/bin/env python3.3

import os.path
import sys
import runpy

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import keypad.__main__
keypad.__main__.main()



