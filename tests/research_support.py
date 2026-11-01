"""Optional archived evidence stays private; portable tests use synthetic data."""
import functools
import os
from pathlib import Path
import unittest


def require_files(*paths):
    missing = [str(path) for path in paths if not Path(path).is_file()]
    if missing:
        message = 'Optional research evidence missing (not downloaded or published by tests): ' + ', '.join(missing)
        if os.environ.get('ORCHARD_REQUIRE_RESEARCH_FIXTURES') == '1':
            raise FileNotFoundError(message)
        raise unittest.SkipTest(message)


def needs_files(*paths):
    def decorate(function):
        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            require_files(*paths)
            return function(*args, **kwargs)
        return wrapped
    return decorate
