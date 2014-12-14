#!/usr/bin/python

import urllib
import urllib2
import json
import sys
import getpass
import os
from shutil import copytree
from time import sleep

nagios_var = '/usr/local/nagios/var'
opsview_url = 'ENTER_OPSVIEW_ADDRESS_HERE'
cemetery_gid = 'ENTER_CEMETERY_GROUP_ID_HERE'

def authenticate():
# Encode credentials, create request and send it, parse the response to get the token
	global username
	username = raw_input("Enter username:")
	credentials = {'username' : username,'password' : (getpass.getpass("Enter password:")) }
	
	url = opsview_url+'/rest/login'
	data = urllib.urlencode(credentials)
	request = urllib2.Request(url, data)
	response = urllib2.urlopen(request)
	token = response.read()
	tokenjson = json.loads(token)

	if response.getcode() == 200:
		print "Authentication successful"
	else:
		print "Error: authentication returned a status of"+response.getcode()
	global token_headers
	token_headers = {'X-Opsview-Username': username,
					 'X-Opsview-Token': tokenjson['token']}
	return tokenjson

def reload_config():
# Reload configurations of OPSView
	url = opsview_url+'/rest/reload'
	req = urllib2.Request(url, "", token_headers)
	print "Reloading, be patient ..."
	response = urllib2.urlopen(req)
	sleep(15)
	if response.getcode() == 200:
		print "Configurations reloaded successfully"
	else:
		print "Error: reloading configurations returned a status of"+response.getcode()

def dump_hosts(hosts):
# Export hosts' configs to json files
	for host in hosts:
		print "Exporting configurations for "+host[1]+" ...",
		url = opsview_url+'/rest/config/host/'+str(host[0])
		token_headers['Content-Type'] = 'application/json'
		req = urllib2.Request(url, None, token_headers)
		response = urllib2.urlopen(req)
		response = response.read()
		hostdata = json.loads(response)
		with open(nagios_var+'/cemeteryops/'+host[1]+'.json', 'w') as outfile:
		 	json.dump(hostdata, outfile)
		print "Done"
	# Now copy the RRD directories
	for host in hosts:
		print "Exporting RRD data for "+host[1]+" ...",
		host[1] = host[1].replace('-','%2D')
		host[1] = host[1].replace('.','%2E')
		if os.path.isdir(nagios_var+'/rrd/'+host[1]) and not os.path.isdir(nagios_var+'/cemeteryops/rrd/'+host[1]):
			copytree(nagios_var+'/rrd/'+host[1],nagios_var+'/cemeteryops/rrd/'+host[1])
			print "Done"
		elif os.path.isdir(nagios_var+'/cemeteryops/rrd/'+host[1]):
			print '/cemeteryops/rrd/'+host[1]+' already exists!'
		elif not os.path.isdir(nagios_var+'/rrd/'+host[1]):
			print "No RRD data for "+host[1]


def create_host(new_host_json):
# Create a host from a json file
	newhost = json.load(open(new_host_json, 'r'))
	#Change the id field to blank
	newhost['object']['id']=""
	url = opsview_url+'/rest/config/host'
	token_headers['Content-Type'] = 'application/json'
	req = urllib2.Request(url, json.dumps(newhost), token_headers)
	response = urllib2.urlopen(req)

	if response.getcode() == 200:
		print "Host \""+newhost['object']['name']+"\" added successfully"
	else:
		print "Error: Adding host \""+newhost['object']['name']+"\" returned a status of"+response.getcode()
	response = response.read()
	hostdata = json.loads(response)
	reload_config()
	return hostdata

def list_hosts_ingroup(id):
# Get the hosts in a group
	url = opsview_url+'/rest/config/hostgroup/'+str(id)
	token_headers['Content-Type'] = 'application/json'
	req = urllib2.Request(url, None, token_headers)
	response = urllib2.urlopen(req)
	response = response.read()
	groupdata = json.loads(response)
	return groupdata

def parse_hosts(hostsjson):
# Create a list of host names from a JSON output of a group list
	hosts = []
	for i in range(1,len(hostsjson['object']['hosts']),1):
		id = hostsjson['object']['hosts'][i]['ref']
		id = int(id.split('/')[4])
		hname = str(hostsjson['object']['hosts'][i]['name'])
		hosts.append([id, hname])
	return hosts

def ack_host(hostdata):
# Acknowledge all host problems
	url = opsview_url+'/rest/acknowledge'
	ackparams = {'hst.hostname': hostdata['object']['name'],
				 'comment': "Automatically acknowledged by CemeteryOps", 
				 'notify': "0", 
				 'sticky': "1"}
	data = urllib.urlencode(ackparams)
	token_headers['Content-Type'] = 'application/x-www-form-urlencoded'
	req = urllib2.Request(url, data, token_headers)
	response = urllib2.urlopen(req)
	if response.getcode() == 200:
		print "Host \""+hostdata['object']['name']+"\" acknowledged successfully"
		#print "Host \"\" acknowledgement successful"
	else:
		print "Error: Acknowledging \""+hostdata['object']['name']+"\" returned a status of"+response.getcode()
	response = response.read()
	return response
	
def get_filelist():
# Get a list of the JSON file in the Cemetery archive	
	ilist = []
	for ifile in os.listdir(nagios_var+'/cemeteryopts/'):
		ilist.append(os.path.join(nagios_var+'/cemeteryopts/', ifile))
	filelist = filter(os.path.isfile, ilist)
	return filelist

def search_archive(partial):
# Find .json filenames matching *partial*
	ifilelist = get_filelist()
	ifilelist = [ifile.replace('.json','') for ifile in ifilelist] 
	ifilelist = [ifile.split('/')[6] for ifile in ifilelist]
	return [name for name in ifilelist if partial.lower() in name.lower()]

def export_all():
# Export all the hosts in the Cemetery group
	# Get the hosts in the Cemetery group, its id is cemetery_gid
	cemeterygroup = list_hosts_ingroup(cemetery_gid)
	# Parse Cemetery hosts data (id,name)
	hosts = parse_hosts(cemeterygroup)
	# Save retrieved hosts data (json + rrd data)
	dump_hosts(hosts)

def import_host(host_name):
# Revive an archived host to Cemetery for analysis
	# Create NewHost
	host_namex = host_name.replace('-','%2D')
	host_namex = host_namex.replace('.','%2E')\
	# Copy RRD directory
	copytree(nagios_var+'/cemeteryops/rrd/'+host_namex,nagios_var+'/rrd/'+host_namex)
	hostdata = create_host(nagios_var+'/cemeteryops/'+host_name+'.json')
	print "Opsview doesn't allow acknowledging hosts right after their creation, please wait ..."
	sleep(120)
	ackdata = ack_host(hostdata)

# Begin here
if len(sys.argv) > 1 and str(sys.argv[1]) == 'import':
	if len(sys.argv) > 2:
		if nagios_var+'/cemeteryops/'+sys.argv[2] in get_filelist():
			authenticate()
			import_host(sys.argv[2])
		else:
			print 'Could not find host \"'+sys.argv[2]+'\"'
	else:
		hit = []
		while len(hit) == 0:
			partial = raw_input("\nSearch archive:")
			hit = search_archive(partial)
		print "\n"
		for i in range(1,len(hit),1):
			print str(i)+'. '+str(hit[i])
		input_host = int(raw_input("\nEnter host number:"))
		print "\n"
		authenticate()
		import_host(hit[input_host])
elif len(sys.argv) > 1 and str(sys.argv[1]) == 'exportall':
	authenticate()
	export_all()
elif str(sys.argv[1]) == 'help':
	print	 "	\n"+"usage: cemeteryops.py (import [host] | exportall | help)\n"+\
			 "	\n"+\
		     "options:\n"+\
		     "	\n"+\
		     "	import [host]	Imports [host] back into the Cemetery, if [host] is not entered,\n"+\
		     "			a search prompt will be displayed.\n"+\
		     "	\n"+\
		     "	exportall	Exports all the hosts from the Cemetery group (JSON+RRD)\n"+\
		     "	\n"+\
		     "	help		This."
else:
	print "	\n"+"usage: cemeteryops.py (import [host] | exportall | help)\n"