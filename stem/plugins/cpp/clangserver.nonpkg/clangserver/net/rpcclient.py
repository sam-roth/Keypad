
import xmlrpclib
import sys
import pickle
from pprint import pprint

def main():
    rc = xmlrpclib.ServerProxy('http://127.0.0.1:38474')
    if sys.argv[1].startswith('en'):
        rc.enroll_compilation_database(sys.argv[2])
    elif sys.argv[1].startswith('co'):
        pprint(rc.completions(sys.argv[2], int(sys.argv[3]), int(sys.argv[4])))

