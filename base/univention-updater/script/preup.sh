#!/bin/sh

UPDATER_LOG="/var/log/univention/updater.log"
UPDATE_LAST_VERSION="$1"
UPDATE_NEXT_VERSION="$2"

echo "Running preup.sh script" >> "$UPDATER_LOG"
date >>"$UPDATER_LOG" 2>&1

eval $(univention-config-registry shell) >>"$UPDATER_LOG" 2>&1

# Bug #16454: Workaround to remove source.list on failed upgrades
function cleanup() {
	rm -f /etc/apt/sources.list.d/00_ucs_temporary_installation.list
	killall univention-updater

	# remove statoverride for UMC and apache in case of error during preup script
	if [ -e /usr/sbin/univention-management-console-server ]; then
		dpkg-statoverride --remove /usr/sbin/univention-management-console-server >/dev/null 2>&1
		chmod +x /usr/sbin/univention-management-console-server 2>> "$UPDATER_LOG"  >> "$UPDATER_LOG"
	fi
	if [ -e /usr/sbin/apache2 ]; then
		dpkg-statoverride --remove /usr/sbin/apache2 >/dev/null 2>&1
		chmod +x /usr/sbin/apache2 2>> "$UPDATER_LOG"  >> "$UPDATER_LOG"
	fi
}
trap cleanup EXIT

# check if user is logged in using ssh
if [ -n "$SSH_CLIENT" ]; then
	if [ "$update23_ignoressh" != "yes" ]; then
		echo "WARNING: You are logged in using SSH -- this may interrupt the update and result in an inconsistent system!"
		echo "Please log in under the console or set the Univention Configuration Registry variable \"update23/ignoressh\" to \"yes\" to ignore it."
		exit 1
	fi
fi

if [ "$TERM" = "xterm" ]; then
	if [ "$update23_ignoreterm" != "yes" ]; then
		echo "WARNING: You are logged in under X11 -- this may interrupt the update and result in an inconsistent system!"
		echo "Please log in under the console or set the Univention Configuration Registry variable \"update23/ignoreterm\" to \"yes\" to ignore it."
		exit 1
	fi
fi

check_cyrus21 ()
{
	pkg=$1
	if dpkg -l $pkg 2>> "$UPDATER_LOG" | grep ^ii  >>"$UPDATER_LOG" ; then
		if [ "$update23_cyrus21" != "yes" ]; then
			echo "ERROR: You have installed the Cyrus21 package \"$pkg\"."
			echo "At the moment this package is not available for UCS 2.3.  You have the following"
			echo "options to continue: "
			echo " 1. Migrate to Cyrus 2.2 as described here: "
			echo "    http://www.univention.de/fileadmin/download/cyrus-migration_091120.pdf"
			echo " 2. Uninstall the package if it is no longer used:"
			echo "    mv /etc/default/saslauthd.debian.dpkg-new /etc/default/saslauthd.debian"
			echo "    apt-get remove $pkg"
			echo " 3. Set the Univention Configuration Registry variable \"update23/cyrus21\" to"
			echo "    \"yes\" and ignore this warning. In this case the update may fail."
			echo " 4. Contact Univention by email <feedback@univention.de>"
			exit 1
		else
			echo "WARNING: update23/cyrus21 is set to yes and $pkg is installed." >>"$UPDATER_LOG"
		fi
		
	fi
}

check_cyrus21 cyrus21-common
check_cyrus21 cyrus21-admin
check_cyrus21 cyrus21-clients

# call custom preup script if configured
if [ ! -z "$update_custom_preup" ]; then
	if [ -f "$update_custom_preup" ]; then
		if [ -x "$update_custom_preup" ]; then
			echo "Running custom preupdate script $update_custom_preup"
			"$update_custom_preup" "$UPDATE_LAST_VERSION" "$UPDATE_NEXT_VERSION" >>"$UPDATER_LOG" 2>&1
			echo "Custom preupdate script $update_custom_preup exited with exitcode: $?" >>"$UPDATER_LOG" 2>&1
		else
			echo "Custom preupdate script $update_custom_preup is not executable" >>"$UPDATER_LOG" 2>&1
		fi
	else
		echo "Custom preupdate script $update_custom_preup not found" >>"$UPDATER_LOG" 2>&1
	fi
fi

check_space(){
	partition=$1
	size=$2
	usersize=$3
	if [ `df -P $partition|tail -n1 | awk '{print $4}'` -gt "$size" ]
		then
		echo -e "Space on $partition:\t OK"
	else
		echo "ERROR:   Not enough space in $partition, need at least $usersize."
        echo "         This may interrupt the update and result in an inconsistent system!"
    	echo "         If neccessary you can skip this check by setting the value of the"
		echo "         baseconfig variable update23/checkfilesystems to \"no\"."
		echo "         But be aware that this is not recommended!"
		echo ""
		# kill the running univention-updater process
		exit 1
	fi
}

# move old initrd files in /boot
initrd_backup=/var/backups/univention-initrd.bak/
if [ ! -d $initrd_backup ]; then
	mkdir $initrd_backup
fi
mv /boot/*.bak /var/backups/univention-initrd.bak/ &>/dev/null

# check space on filesystems
if [ ! "$update23_checkfilesystems" = "no" ]
then

	check_space "/var/cache/apt/archives" "250000" "250 MB"
	# UCS 2.3-1 does not include a new kernel
	# check_space "/boot" "40000" "40 MB"
	check_space "/" "500000" "500 MB"

else
    echo "WARNING: skipped disk-usage-test as requested"
fi


echo "Checking for the package status"
dpkg -l 2>&1 | grep "^[a-zA-Z][A-Z] " >>"$UPDATER_LOG" 2>&1
if [ $? = 0 ]; then
	echo "ERROR: The package state on this system is inconsistent."
	echo "       Please run 'dpkg --configure -a' manually"
	exit 1
fi

# ensure that UMC is not restarted during the update process
if [ -e /usr/sbin/univention-management-console-server ]; then
	dpkg-statoverride --add root root 0644 /usr/sbin/univention-management-console-server >/dev/null 2>&1
	chmod -x /usr/sbin/univention-management-console-server
fi

if [ -e /usr/sbin/apache2 ]; then
	dpkg-statoverride --add root root 0644 /usr/sbin/apache2 >/dev/null 2>&1
	chmod -x /usr/sbin/apache2
fi

# Disable usplash during update (Bug #16363)
if dpkg -l lilo 2>> "$UPDATER_LOG" >> "$UPDATER_LOG" ; then
	dpkg-divert --rename --divert /usr/share/initramfs-tools/bootsplash.debian --add /usr/share/initramfs-tools/hooks/bootsplash 2>> "$UPDATER_LOG" >> "$UPDATER_LOG"
fi

# remove old packages that causes conflicts
olddebs="python2.4-dns alsa-headers"
for deb in $olddebs; do
	if dpkg -l $deb >>"$UPDATER_LOG" 2>&1; then
		dpkg -P $deb >>"$UPDATER_LOG" 2>&1
	fi
done

# Update package lists
apt-get update >>"$UPDATER_LOG" 2>&1
#
for pkg in univention-ssl univention-thin-client-basesystem univention-thin-client-x-base ; do
	# pre-update $pkg to avoid pre-dependency-problems
	if dpkg -l $pkg 2>> "$UPDATER_LOG" | grep ^ii  >>"$UPDATER_LOG" ; then
	    echo -n "Starting preupdate of $pkg..."
	    $update_commands_install $pkg >>"$UPDATER_LOG" 2>> "$UPDATER_LOG"
	    if [ ! $? = 0 ]; then
			echo "failed."
	        echo "ERROR: pre-update of $pkg failed!"
	        echo "       Please run 'dpkg --configure -a' manually."
	        exit 1
	    fi
	    dpkg -l 2>&1  | grep "  " | grep -v "^|" | grep "^[a-z]*[A-Z]" >>"$UPDATER_LOG" 2>&1
	    if [ $? = 0 ]; then
			echo "failed."
	        echo "ERROR: pre-update of $pkg failed!"
	        echo "       Inconsistent package state detected. Please run 'dpkg --configure -a' manually."
	        exit 1
	    fi
		echo "done."
	fi
done

if [ "$update23_keep_avahi" != "yes" ]; then
	# remove ucs_2.0-0 packages that cause conflicts
	olddebs="libnss-mdns avahi-daemon libavahi-core4"	# libavahi-common3 left for evolution etc.
	for deb in $olddebs; do
		if dpkg -l $deb >>"$UPDATER_LOG" 2>&1; then
			dpkg -P $deb >>"$UPDATER_LOG" 2>&1
		fi
	done
fi

echo "Starting update process, this may take a while."
echo "Check /var/log/univention/updater.log for more information."
date >> "$UPDATER_LOG"
trap - EXIT

exit 0
