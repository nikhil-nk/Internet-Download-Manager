import os
import time

# Default Values
max_threads = 5
max_retry = 5
default_path = os.path.join(os.environ["HOME"], 'Downloads', 'OpenIDM')


class File(object):
    """docstring for File
        A calss handles the information about the desired file"""

    def __init__(self, url=None, location=default_path, name=None):
        pass


class Download(object):
    """docstring for Download
        A Class handles Downloading and ensure the file"""
    time_start = time.time()

    def __init__(self, file, threads=max_threads, path=default_path, retries=max_retry, split=True):
        pass
