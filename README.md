cemeteryops.py
==============

OPSView host archive script.

This script is used locally on any master OPSView server to archive hosts' configurations and OPSView performance graphs data (rrd files). The exported files will be archived on the server under /usr/local/nagios/var/cemeteryops/.

cemetryops.py also allows the admin to import a specific host from the archive for analysis. The host is imported into the cemetery hostgroup and is automatically acknowledged.


Usage
=====

Create a hostgroup for to be used with cemeteryops.py (let's call it cemetery), then move the hosts to be archive dto that hostgroup. Set *_opsview_url_* and *_cemetery_gid_* and you're ready.

	 cemeteryops.py (import [host] | exportall | help)
	 
options:

    import [host]	  Imports [host] back into the Cemetery, if [host] is not entered,a search 
                      prompt will be displayed.
                      
    exportall	      Exports all the hosts from the cemetery group (JSON+RRD).
    
    help		      Shows command usage and options.
