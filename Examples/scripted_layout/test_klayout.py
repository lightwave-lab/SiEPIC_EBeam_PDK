'''
This file runs with regular pytest::

    pytest test_klayout.py

It doesn't interact with the header API, just through shell and filesystem
'''
import os
import subprocess

import lytest
from lytest import contained_script, difftest_it

makefile_dir = os.path.dirname(__file__)
lytest.utest_buds.test_root = makefile_dir

@contained_script
def ComplexLayout():
    subprocess.check_call(['make', 'from_klayout'], cwd=makefile_dir)
    return 'example_mask.gds'

def test_ComplexLayout(): difftest_it(ComplexLayout)()
