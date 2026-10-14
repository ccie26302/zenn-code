import os, sys
sys.path.insert(0, "/tasks")
from cjudge import main
main(os.path.dirname(os.path.abspath(__file__)), sys.argv[1])
