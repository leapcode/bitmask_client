#
# Regular cron jobs for the python-leap-client package
#
0 4	* * *	root	[ -x /usr/bin/python-leap-client_maintenance ] && /usr/bin/python-leap-client_maintenance
