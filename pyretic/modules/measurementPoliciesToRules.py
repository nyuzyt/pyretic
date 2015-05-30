from pyretic.lib.corelib import *
from pyretic.lib.std import *
from pyretic.lib.query import *

def main():
 	list_srcIPs = []
	list_dstIPs = []
	with open('/home/vishlesh/SDN_RuleSetGenerator/matchedMeasurementPolicies.txt','r') as f:
    		for line in f:
        		(srcip,dstip) =line.split(", ",1)
			dstip,temp = dstip.split(", ",1)
			
			list_srcIPs.append(srcip)
			list_dstIPs.append(dstip)
	i=1
	policy = drop
	print(len(list_srcIPs))
	for srcip,dstip in zip(list_srcIPs,list_dstIPs):
		print("srcip:",srcip,"dstip:",dstip)
		policy = policy + (match(srcip = str(srcip),dstip = str(dstip))>>drop)
		
      	return policy
