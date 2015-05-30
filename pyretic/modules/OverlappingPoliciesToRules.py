from pyretic.lib.corelib import *
from pyretic.lib.std import *
from pyretic.lib.query import *
import ipaddress
import time
def main():
	list_measureSrcIPs = []
	list_measureDstIPs = []
	list_fwdSrcIPs = []
	list_fwdDstIPs = []
	with open('/home/vishlesh/SDN_RuleSetGenerator/matchedMeasurementPolicies.txt','r') as f:
    		for line in f:
        		(srcip,dstip) =line.split(", ",1)
			dstip,temp = dstip.split(", ",1)
			list_measureSrcIPs.append(srcip)
			list_measureDstIPs.append(dstip)
	with open('/home/vishlesh/SDN_RuleSetGenerator/matchedReachabilityPolicies.txt','r') as f:
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
	
	policy = none
	
	
	for fwdSrcip,fwdDstip in zip(list_fwdSrcIPs,list_fwdDstIPs):
		#print("here")
		for each_srcip,each_dstip in zip(list_measureSrcIPs,list_measureDstIPs):
			if(isSourceMatch(fwdSrcip,each_srcip)==True):
				#print("sourceIP matched")
				for each_ip in fwdDstip:
					if(isDestMatch(each_ip,each_dstip)==True):
						policy = policy + (match(srcip = str(fwdSrcip),dstip = str(each_ip)) >> fwd(i))
						i=i+1
	
	## since we have a action: count supported in ovs switch, we will install the drop action instead in accordance to see overlapping in rules
	for srcip,dstip in zip(list_measureSrcIPs,list_measureDstIPs):
		print("srcip:",srcip,"dstip:",dstip)
		policy = policy + (match(srcip = str(srcip),dstip = str(dstip))>>drop)
		i=i+1
		
	print(policy)	
	print(i)
	print("finish")
	return policy

def isSourceMatch(endHost,subnetIPaddr):
	endHost = ipaddress.ip_address(unicode(endHost))
	subnetIPaddr = ipaddress.ip_network(unicode(subnetIPaddr))
        for each_addr in subnetIPaddr:
            if each_addr==endHost:
                return True
        return False

def isDestMatch(subnetAddrBig,subnetAddrSmall):
        set1 =([])
	subnetAddrBig = ipaddress.ip_network(unicode(subnetAddrBig))
	subnetAddrSmall = ipaddress.ip_network(unicode(subnetAddrSmall))	
        prefix = subnetAddrBig._prefixlen
##	print(subnetAddrBig,subnetAddrSmall)
        subnetList = []
        while(prefix<=31):
            prefix = prefix+1
            subnetList = subnetAddrBig.subnets(new_prefix=prefix)
        set1 = set(subnetList)

        if subnetAddrSmall in set1:
            return True
        else:
            return False

