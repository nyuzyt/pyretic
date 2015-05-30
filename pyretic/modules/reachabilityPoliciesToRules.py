
from pyretic.lib.corelib import *
from pyretic.lib.std import *
from pyretic.lib.query import *
import ipaddress
import time

def main():
	list_fwdSrcIPs = []
	list_fwdDstIPs = []
	with open('/home/vishlesh/SDN_RuleSetGenerator/ReachabilityPolicies.txt','r') as f:
		for line in f:
			(srcip,dstip_temp) = line.split(", ",1)
			dstip_temp = dstip_temp.split("(")
			DstIp = []
			for each_ip in dstip_temp:
				if not each_ip.find('.')==-1:
					each_ip = each_ip.split("'")	
					ip = each_ip[1]				
					DstIp.append(ip)
			list_fwdSrcIPs.append(srcip)
			list_fwdDstIPs.append(DstIp)
	i=1
	##j=1 ##give some time to pyretic to install rules
	forward = flood()
	print(len(list_fwdSrcIPs))
	print(len(list_fwdDstIPs))

	for fwdSrcip,fwdDstip in zip(list_fwdSrcIPs,list_fwdDstIPs):
		for each_ip in fwdDstip:
			forward = forward + (match(srcip = str(fwdSrcip),dstip = str(each_ip)) >> fwd(i))		
			i=i+1
	print(i)
	print("finish")
	return forward

