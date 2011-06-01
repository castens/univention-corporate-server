#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Configuration Registry
#  build UMC module
#
# Copyright 2011 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import os

import json
import polib

import univention.debhelper as dh_ucs

MODULE = 'Module'
PYTHON = 'Python'
DEFINITION = 'Definition'
JAVASCRIPT = 'Javascript'
SYNTAX = 'Syntax'
CATEGORY = 'Category'
ICONS = 'Icons'

LANGUAGES = ( 'de', )

"""Each module definition contains the following entries:

 Module: The internal name of the module
 Python: A directory containing the python module. There must be a subdirectory named like the internal name of the module.
 Definition: The XML definition of the module
 Syntax: The XML definition of new syntax classes
 Javascript: The directory of the javascript code. In this directory must be a a file called <Module>.js
 Category: The XML definition of additional categories
 Icons: A directory containing the icons used by the module. The
   directory structure must follow the following pattern
   <weight>x<height>/<icon>.(png|gif)

The entries Syntax and Category are optional.

Example:
 Module: ucr
 Python: umc/module
 Definition: umc/ucr.xml
 Syntax: umc/syntax/ucr.xml
 Javascript: umc/js
 Category: umc/categories/ucr.xml
 Icons: umc/icons
"""

class UMC_Module( dict ):
	def __init__( self, *args ):
		dict.__init__( self, *args )
		for key in ( MODULE, PYTHON, JAVASCRIPT, DEFINITION, CATEGORY, SYNTAX, ICONS ):
			if key in self and self[ key ]:
				self[ key ] = self[ key ][ 0 ]

	@property
	def python_path( self ):
		return '%(Python)s/%(Module)s/' % self

	@property
	def js_path( self ):
		return '%(Javascript)s/' % self

	@property
	def js_filename( self ):
		return '%(Javascript)s/%(Module)s.js' % self

	@property
	def module_name( self ):
		return self.__getitem__( MODULE )

	@property
	def xml_definition( self ):
		return self.get( DEFINITION )

	@property
	def xml_syntax( self ):
		if SYNTAX in self:
			return self.get( SYNTAX, '' )

	@property
	def xml_categories( self ):
		if CATEGORY in self:
			return self.get( CATEGORY, '' )

	@property
	def python_files( self ):
		for filename in os.listdir( self.python_path ):
			if not filename.endswith( '.py' ):
				continue
			yield os.path.join( self.python_path, filename )

	@property
	def python_po_files( self ):
		path = '%(Python)s/%(Module)s/' % self
		for lang in LANGUAGES:
			yield os.path.join( path, '%s.po' % lang )

	@property
	def js_po_files( self ):
		for lang in LANGUAGES:
			yield os.path.join( self.__getitem__( JAVASCRIPT ), '%s.po' % lang )

	@property
	def icons( self ):
		return self.get( ICONS )

def read_modules( package ):
	modules = []

	file_umc_module = os.path.join( 'debian/', package + '.umc-modules' )

	if not os.path.isfile( file_umc_module ):
		return modules

	f_umc_module = open( file_umc_module, 'r' )

	for item in dh_ucs.parseRfc822( f_umc_module.read() ):
		# required fields
		for required in ( MODULE, PYTHON, DEFINITION, JAVASCRIPT ):
			if not required in item or not item[ required ]:
				raise AttributeError( 'UMC module definition incomplete. key %s missing' % required )

		# single values
		item[ 'package' ] = package

		modules.append( UMC_Module( item ) )

	return modules

def create_po_file( po_file, package, files, language = 'python' ):
	"""Create a PO file for a defined set of files"""
	message_po = '%s/messages.po' % os.path.dirname( po_file )

	if os.path.isfile( message_po ):
		os.unlink( message_po )
	if isinstance( files, basestring ):
		files = [ files ]
	dh_ucs.doIt( 'xgettext', '--force-po', '--from-code=UTF-8', '--sort-output', '--package-name=%s' % package, '--msgid-bugs-address=packages@univention.de', '--copyright-holder=Univention GmbH', '--language', language, '-o', message_po, *files )
	if os.path.isfile( po_file ):
		dh_ucs.doIt( 'msgmerge', '--update', '--sort-output', po_file, message_po )
		if os.path.isfile( message_po ):
			os.unlink( message_po )
	else:
		dh_ucs.doIt( 'mv', message_po, po_file )

def create_mo_file( po_file ):
	dh_ucs.doIt( 'msgfmt', '--check', '--output-file', po_file.replace( '.po', '.mo' ), po_file )

def create_json_file( po_file ):
	json_file = po_file.replace( '.po', '.json' )
	json_fd = open( json_file, 'w' )
	pofile = polib.pofile( po_file )
	data = {}
	for entry in pofile:
		data[ entry.msgid ] = entry.msgstr

	json_fd.write( json.dumps( data ) )
	json_fd.close()

