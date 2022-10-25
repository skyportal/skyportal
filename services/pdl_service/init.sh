#!/usr/bin/env bash

##################################################################################################
## USER CONFIGURATION

# working directory
WORKDIR=`dirname $0` # default is same as init script

# name displayed by init script, does not affect command
NAME="Product Distribution"

JAVA="java"

# command managed by init script, this must be unique on the system because this script uses PS.
COMMAND="$JAVA -jar ProductClient.jar --configFile=config.ini --receive"


##
##################################################################################################
## EDIT BELOW THIS LINE AT YOUR OWN RISK



#
# Based on generic_init.sh
# A SystemV init style script that can be used for any command.
#
# This simplifies init scripts for RHEL, BSD, and Solaris, but is not perfect!
# Assumptions:
#   - command is always started with the same arguments
#   - you only want to run a single instance of this command
#   - you can find the command in ps output by grep ing for command with arguments
#
# Jeremy Fee <jmfee@usgs.gov>
# Version 0.4 2010/04/12
#

if [ $# -lt 0 ]; then
	echo "Usage: $0 {start|stop|restart|reload|status}"
	echo
	exit 1
fi



ACTION=$1

# set the umask for any started programs
umask 022


#exit status is global and defaults to success
# any start/stop failure will adjust status
# and is never reset to 0.
EXIT_STATUS=0


PS_COMMAND="ps"
PS_FLAGS="aux"
PS_GREP_SEARCH="$COMMAND"


#bsd workaround
#ps does not output beyond 80 columns, by default, which prevents ps from matching most commands
export COLUMNS=1024

#solaris workarounds
OS_NAME=`uname`
if [ "$OS_NAME" == "SunOS" ]; then
	if [ -x "/bin/ps" ]; then
		# Solaris ps truncates command output at 80 characters.
		# Commands *MUST* be unique within the first 80 characters.
		PS_COMMAND="/bin/ps"
		PS_FLAGS="-ef"
		if [ ${#PS_GREP_SEARCH} -gt 79 ]; then
			PS_GREP_SEARCH=${PS_GREP_SEARCH:0:79}
		fi
	fi
fi


start() {
	local pid=`get_pid $COMMAND`
	if [ ! -z "$pid" ]; then
		echo "$NAME already running (pid=$pid)"
	else
		echo -n "Starting $NAME - "

		##run command
		pushd $WORKDIR > /dev/null
		nohup $COMMAND > /dev/null 2>&1 &
		popd > /dev/null

		##wait a second and see if is running
		sleep 1
		pid=`get_pid $COMMAND`
		if [ ! -z "$pid" ]; then
			#running
			echo "OK (pid=$pid)"
		else
			#not running
			echo "ERROR, unable to start $NAME using command:"
			echo "	$COMMAND"
			EXIT_STATUS=2
		fi
	fi
}

stop() {
	local pid=`get_pid $COMMAND`
	if [ -z "$pid" ]; then
		echo "$NAME not running"
	else
		echo -n "Stopping $NAME (pid=$pid) - "
		echo "$pid" | xargs kill

		##wait up to 15 seconds for stop
		pid=`get_pid $COMMAND`
		seconds_waited=0
		while [ ! -z "$pid" ] && [ $seconds_waited -lt 15 ]; do
			sleep 1
			echo -n "."
			let seconds_waited=seconds_waited+1
			pid=`get_pid $COMMAND`
		done

		if [ -z "$pid" ]; then
			#not running
			echo " OK"
		else
			#still running
			echo " ERROR (pid=$pid)"
			EXIT_STATUS=3
		fi
	fi
}

get_pid() {
	## Find PID
	## ps aux appears consisent for both BSD and LINUX
	##     output pid in column 2 (for awk)
	##     and include the command (for greps)
	#
	# list processes
	#     ps aux
	# remove this init script process (has command in arguments)
	#     grep -v 'generic_init'
	# keep processes that match $command
	#     grep $command
	# remove grep processes
	#     grep -v grep"
	# output PID, from column 2
	#     awk '{print $2}'

	local pid=`${PS_COMMAND} ${PS_FLAGS} | grep -v 'generic_init' | grep "${PS_GREP_SEARCH}" | grep -v grep | awk '{print \$2}'`
	if [ ! -z "$pid" ]; then
		echo "$pid"
	else
		echo ""
	fi
}



#init logic
case "$ACTION" in
	start)
		start
		;;

	stop)
		stop
		;;

	restart|reload|condrestart)
		stop
		start
		;;

	status)
		pid=`get_pid`
		if [ -z "$pid" ]; then
			echo "$NAME not running"
			EXIT_STATUS=1
		else
			echo "$NAME running (pid=$pid)"
		fi
		;;

	*)
		echo "Usage: $0 {start|stop|restart|reload|condrestart|status}"
		exit 1
		;;
esac



exit $EXIT_STATUS
