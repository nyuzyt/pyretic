from pyretic.lib.corelib import *
from pyretic.lib.std import *
from pyretic.lib.query import *

def printer(pkt):
    print "------packet--------"
   

def dpi():
  q =count_packets(1,['srcip'])
  q.register_callback(printer)
  return q

### Main ###

def main():
    return ((match(srcip = '10.0.0.0/31')) >> dpi())

