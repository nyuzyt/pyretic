from pyretic.lib.corelib import *
from pyretic.lib.std import *
from pyretic.lib.query import *
#from pyretic.modules.mac_learner import mac_learner as act_like_switch
import time

class act_like_switch(DynamicPolicy):
	def __init__(self):
         # REUSE A SINGLE FLOOD INSTANCE
        	super(act_like_switch,self).__init__()
		self.forward = flood()
        	self.set_initial_state()
	
	def set_network(self,network):
	        self.set_initial_state()
	
	def update_policy(self):
		self.policy = self.policy + self.forward
		print(self.policy)

	def set_initial_state(self):
		list_srcIPs = []
		list_dstIPs = []
		#self.policy = self.forward
		with open('/home/vishlesh/SDN_RuleSetGenerator/SDN_RuleSetGenerator/matchedReachabilityPolicies.txt','r') as f:
			for line in f:
				(srcip,dstip_temp) = line.split(", ",1)
				dstip_temp = dstip_temp.split("(")
				DstIp = []
				for each_ip in dstip_temp:
					if not each_ip.find('.')==-1:
						each_ip = each_ip.split("'")	
						ip = each_ip[1]				
						DstIp.append(ip)
				list_srcIPs.append(srcip)
				list_dstIPs.append(DstIp)
		j=1
		##j=1 ##give some time to pyretic to install rules
		print(len(list_srcIPs))
		print(len(list_dstIPs))
		if(len(list_srcIPs) == len(list_dstIPs)):
			for srcip,dstip in zip(list_srcIPs,list_dstIPs):
				i=1
				for each_ip in dstip:
					if i==1:
						i=i+1
						match1 = match(srcip = str(srcip),dstip = str(each_ip))
					else:
						match1 = match1 | match(srcip = str(srcip),dstip = str(each_ip))
							
				self.forward = match1 >> fwd(j)
				j=j+1
				self.update_policy()
				if(j==31):
					return act_like_switch()
					time.sleep(60)
				else:
					return act_like_switch()
					time.sleep(1)

	##	print(forward)
	##	return forward

def main():
   return act_like_switch()
