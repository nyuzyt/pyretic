
import sys
sys.path.append('/home/vishlesh/pyretic/my_tests')

from pyretic.lib.corelib import *
from pyretic.lib.std import *
from pyretic.lib.query import *

def main():
	
	notallowed = none
	forward = match(srcip = '10.0.0.109/32')>>fwd(1)
	notallowed = match(srcip = '10.0.0.108/32')>>notallowed
        return notallowed+forward
