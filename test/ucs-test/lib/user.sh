#!/bin/bash
CONTROLMODE=true
. "$TESTLIBPATH/base.sh" || exit 137
. "$TESTLIBPATH/random.sh" || exit 137

user_randomname () { #Generates a random string as username an echoes it. Usage: NAME=$(user_randomname)
	random_string
}

mail_domain_exists () {
	univention-ldapsearch "(&(objectClass=univentionMailDomainname)(cn=$1))" | grep -q "^cn: $1"
	return $?
}

user_create () { #Creates a user named like the first argument, supplied to the function.
	#The Time consumed to create the User is stored in $TIMETOCREATEUSER (in nsecs)
	# Possible Options are:
	# KERBEROS
	# MAIL
	# POSIX
	# PERSON
	# SAMBA
	# PKI
	#
	# The values for this values are "true" or "false", creating a User could look like this:
	#
	# SAMBA="false"
	# MAIL="false"
	# KERBEROS="true"
	# PERSON="true"
	# POSIX="false"
	# PKI="false"
	# USERNAME=$(user_randomname)
	# user_create "$USERNAME"

	local USERNAME=${1:-$NAME}
	if [ -z "$USERNAME" ]
	then
		echo "No username has been supplied."
		echo "You have to supply a username e.g. generated by \$(user_randomname)"
		return 1
	fi
	shift

	declare -a CMD=(udm-test users/user create \
		--position="cn=users,$ldap_base" \
		--set username="$USERNAME" \
		--set firstname=Max \
		--set lastname=Muster \
		--set organisation=firma.de_GmbH \
		--set password=univention)

	if [ -z "${MAILADDR:-}" ]
	then
		if mail_domain_exists "$domainname"; then
			MAILADDR=$(random_mailaddress)
			CMD+=(--set mailPrimaryAddress="$MAILADDR@$domainname")
		fi
	fi

	info "create user $USERNAME"

	[ "${UIDTEST:-}" = true ] && CMD+=(--set uidNumber=1234)
	[ "${KERBEROS:-}" = true ] && CMD+=(--option=kerberos)
	[ "${MAIL:-}" = true ] && CMD+=(--option=mail)
	[ "${PERSON:-}" = true ] && CMD+=(--option=person)
	[ "${POSIX:-}" = true ] && CMD+=(--option=posix)
	[ "${SAMBA:-}" = true ] && CMD+=(--option=samba)
	[ "${PKI:-}" = true ] && CMD+=(--option=pki)

	local err=$(mktemp)
	local STARTTIME=$(date +%s%N)
	"${CMD[@]}" "$@" >"$err" 2>&1
	local rc=$?
	local STOPPTIME=$(date +%s%N)
	TIMETOCREATEUSER=$(($STOPPTIME - $STARTTIME))

	#Catch Tracebacks
	cat "$err"

	MAILADDR=

	if grep -Fq "Traceback (most recent call last):" "$err"
	then
		rm -f "$err"
		return 110
	else
		if grep -Fq "E: Object exists" "$err"
		then
			rm -f "$err"
			return 111
		else
			rm -f "$err"
			return $rc
		fi
	fi
}

user_dn () { #echos the DN of User named $NAME
	local USERNAME=${1:-$NAME}
	udm-test users/user list --filter uid="$USERNAME" | sed -ne 's/^DN: //p'
}

user_remove () { # Remove User named like the first argument, supplied to the function.
	local USERNAME=${1?:missing parameter: name}

	info "remove user $USERNAME"

	if udm-test users/user remove --dn="uid=$USERNAME,cn=users,$ldap_base"
	then
		debug "user $USERNAME removed"
	else
		error "univention-directory-manager return error $USERNAME"
		return 1
	fi

	if "${CONTROLMODE:-false}"
	then
		if user_exists "$USERNAME"
		then
			error "user $USERNAME should not exist, but it does"
			return 1
		fi
	fi
	return 0
}

user_exists () { #returns 0, if user exits or 1 if he doesn't. Example: userexits $NAME
	local USERNAME=${1?:missing parameter: name}
	info "checking whether the user $USERNAME is really removed"

	if udm-test users/user list --filter uid="$USERNAME" | egrep "^DN:"
	then
		debug "user $USERNAME exists"
		return 0
	else
		debug "user $USERNAME does not exist"
		return 1
	fi
}

user_change_pw_next_login () { # Set the Flag for changing the Password on the next login for the user.  #Example: user_change_pw_next_login $NAME
	local USERNAME=${1?:missing parameter: user name}
	info "user $USERNAME must change password on next login"

	udm-test users/user modify \
		--dn="uid=$USERNAME,cn=users,$ldap_base" \
		--set pwdChangeNextLogin=1
}

user_check_pw_expiry () { # Checks if there is an expiry-date for the password of a user returns 0 if user has one, otherwise 1 Usage: user_check_pw_expiry $NAME
	local USERNAME=${1?:missing parameter: name}
	info "check the password expriry of user $USERNAME"

	udm-test users/user list --filter "username=$USERNAME" |
		grep passwordexpiry | cut -c19-26 | grep -qv None
}

user_rename () { # Rename a user # Example: renameuser $NAMEOLD $NAMENEW
	local USERNAMEOLD=${1?:missing parameter: old name}
	local USERNAMENEW=${2?:missing parameter: new name}

	info  "rename user $USERNAMEOLD to $USERNAMENEW"
	udm-test users/user modify \
		--dn="uid=$USERNAMEOLD,cn=users,$ldap_base" \
		--set username="$USERNAMENEW"
}

user_set_attr () {
	local name=${1?:missing parameter: name}
	local attr=${2?:missing parameter: udmAttribute}
	local ldap=${3?:missing parameter: ldapAttribute}
	local value=${4?:missing parameter: value}

	local dn=$(user_dn "$name")

	udm-test users/user modify --dn="$dn" --set "$attr=$value"
	wait_for_replication
	if [ -n "$ldap" ]
	then
		univention-ldapsearch -x "uid=$name" "$ldap" | ldapsearch-wrapper | grep -q "^$ldap"
	fi
}

# vim: set filetype=sh ts=4:
