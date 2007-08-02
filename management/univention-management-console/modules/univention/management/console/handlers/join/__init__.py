#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  module: join into the domain
#
# Copyright (C) 2007 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# Binary versions of this file provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import univention.management.console as umc
import univention.management.console.handlers as umch
import univention.management.console.dialog as umcd
import univention.management.console.tools as umct

import base64
import os
import time

import notifier.popen

import _revamp
import tools

_ = umc.Translation( 'univention.management.console.handlers.join' ).translate

name = 'join'
icon = 'join/module'
short_description = _( 'Domain Join' )
long_description = _( 'Join to a UCS Domain' )
categories = [ 'all', 'system' ]

command_description = {
	'join/status' : umch.command(
		short_description = _( 'Join Status' ),
		method = 'join_status',
		values = {},
		startup = True,
	),
	'join/rejoin' : umch.command(
		short_description = _( 'Rejoin' ),
		method = 'join_rejoin',
		values = { 'account' : umc.String( _( 'Username' ), required = False ),
				   'password' : umc.Password( _( 'Password' ), required = False ) },
	),
	'join/script' : umch.command(
		short_description = _( 'Run Join Script' ),
		method = 'join_script',
		values = { 'script' : umc.String( _( 'Join Script Name' ) ),
				   'account' : umc.String( _( 'Username' ) ),
				   'password' : umc.Password( _( 'Password' ) ) },
	),
}

def _create_tempfile():
	umask = os.umask( 0077 )
	unique = base64.encodestring( os.urandom( 12 ) )[ : -1 ]
	unique = unique.replace( '/', '-' )
	filename = os.path.join( '/tmp', 'umc-%d-%s' % ( os.getpid(), unique ) )
	fd = open( filename, 'w' )
	fd.close()
	os.umask( umask )

	return filename

class handler( umch.simpleHandler, _revamp.Web ):
	def __init__( self ):
		global command_description
		umch.simpleHandler.__init__( self, command_description )

	def join_status( self, object ):
		if not self.permitted( 'join_status', options = object.options ):
			self.finished( object.id(), {},
						   report = _( 'You are not permitted to run this command.' ),
						   success = False )
			return

		self.finished( object.id(), tools.read_status() )


	def join_rejoin( self, object ):
		if object.incomplete:
			self.finished( object.id(), None )
		else:
			pwdfile = _create_tempfile()
			logfile = _create_tempfile()
			fd = open( pwdfile, 'w' )
			fd.writeline( object.options[ 'password' ] )
			fd.close()
			cmd = '/usr/sbin/univention-join -dcaccount %s -dcpwd %s > %s 2>&1' % \
				  ( object.options[ 'account' ], pwdfile, logfile )
			proc = notifier.popen.Shell( cmd )
			proc.signal_connect( 'finished', notifier.Callback( self._join_rejoin, object,
																pwdfile, logfile ) )
			proc.start()

	def _join_rejoin( self, pid, status, result, object, pwdfile, logfile ):
		os.unlink( pwdfile )
		fd = open( logfile, 'r' )
		data = fd.readlines()
		fd.close()
		os.unlink( logfile )
		self.finished( object.id(), ( status == 0, data ) )

	def join_script( self, object ):
		if object.incomplete:
			self.finished( object.id(), None )
		else:
			logfile = _create_tempfile()
			if umc.registry.get( 'server/role', None ) in ( 'domaincontroller_master',
															'domaincontroller_backup' ):
				cmd = '/usr/lib/univention-install/%s > %s 2>&1' % \
					  ( object.options[ 'script' ], logfile )
			else:
				cmd = '/usr/lib/univention-install/%s --binddn %s --bindpwd %s > %s 2>&1' % \
				  ( object.options[ 'script' ], object.options.get( 'account', '' ),
					object.options.get( 'password', '' ), logfile )
			proc = notifier.popen.Shell( cmd )
			proc.signal_connect( 'finished',
								 notifier.Callback( self._join_script, object, logfile ) )
			proc.start()

	def _join_script( self, pid, status, result, object, logfile ):
		fd = open( logfile, 'r' )
		data = fd.readlines()
		fd.close()
		os.unlink( logfile )
		self.finished( object.id(), ( status == 0, data ) )
