'''
This file is made to wrap pytest within the klayout GSI
and then launch pytest upon fake_test_python.py
'''
import pytest
pytest.main(['fake_test_python.py'])