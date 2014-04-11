#!/usr/bin/env python3.3

import os.path
import sys
import runpy

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import stem.__main__
stem.__main__.main()



