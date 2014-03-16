import time
import os
import sys
import csv

def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()

def write_file(content, filename):
    with open(filename, 'w') as f:
        return f.write(content)

def append_line_file(content, filename):
    with open(filename, 'a') as f:
        return f.write(content+'\n')

def file_age(filename, now=None):
    """returns age of file, in hours"""
    if now == None:
        now = time.time()

    try:
        fileChanged = os.path.getmtime(filename)
    except OSError:
        return sys.maxint # hack, really old

    return now - fileChanged

def read_csv(filename):
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            yield row
