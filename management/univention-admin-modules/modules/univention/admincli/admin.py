# -*- coding: utf-8 -*-
#
# Univention Admin Modules
#  command line frontend to univention-admin (module)
#
# Copyright (C) 2004, 2005, 2006 Univention GmbH
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


import os, sys, getopt, types, re, codecs, string, time, base64, os

import univention.debug

import univention.admin.uexceptions
import univention.admin.uldap
import univention.admin.modules
import univention.admin.objects
import univention_baseconfig
import univention.admin.ipaddress

# update choices-lists which are defined in LDAP
univention.admin.syntax.update_choices()

# usage information
def usage():
	out=[]
	out.append('univention-admin: command line interface for managing UCS')
	out.append('copyright (c) 2001-@%@copyright_lastyear@%@ Univention GmbH, Germany')
	out.append('')
	out.append('Syntax:')
	out.append('  univention-admin module action [options]')
	out.append('  univention-admin [--help] [--version]')
	out.append('')
	out.append('actions:')
	out.append('  %-32s %s' % ('create:', 'Create a new object'))
	out.append('  %-32s %s' % ('modify:', 'Modify an existing object'))
	out.append('  %-32s %s' % ('remove:', 'Remove an existing object'))
	out.append('  %-32s %s' % ('list:', 'List objects'))
	out.append('  %-32s %s' % ('move:', 'Move object in directory tree'))
	out.append('')
	out.append('  %-32s %s' % ('-h | --help | -?:', 'print this usage message'))
	out.append('  %-32s %s' % ('--version:', 'print version information'))
	out.append('')
	out.append('general options:')
	out.append('  --%-30s %s' % ('logfile', 'path and name of the logfile to be used'))
	out.append('')
	out.append('create options:')
	out.append('  --%-30s %s' % ('binddn', 'bind DN'))
	out.append('  --%-30s %s' % ('bindpwd', 'bind password'))
	out.append('  --%-30s %s' % ('position', 'Set position in tree'))
	out.append('  --%-30s %s' % ('set', 'Set variable to value, e.g. foo=bar'))
	out.append('  --%-30s %s' % ('superordinate', 'Use superordinate module'))
	out.append('  --%-30s %s' % ('option', 'Use only given module options'))
	out.append('  --%-30s %s' % ('customattribute', 'Set custom attribute foo=bar'))
	out.append('  --%-30s %s' % ('policy-reference', 'Reference to policy given by DN'))
	out.append('  --%-30s %s' % ('tls', '0 (no); 1 (try); 2 (must)'))
	out.append('  --%-30s   ' % ('ignore_exists'))
	out.append('')
	out.append('modify options:')
	out.append('  --%-30s %s' % ('binddn', 'bind DN'))
	out.append('  --%-30s %s' % ('bindpwd', 'bind password'))
	out.append('  --%-30s %s' % ('dn', 'Edit object with DN'))
	out.append('  --%-30s %s' % ('arg', 'Edit object with ARG'))
	out.append('  --%-30s %s' % ('set', 'Set variable to value, e.g. foo=bar'))
	out.append('  --%-30s %s' % ('append', 'Append value to variable, e.g. foo=bar'))
	out.append('  --%-30s %s' % ('remove', 'Remove value from variable, e.g. foo=bar'))
	out.append('  --%-30s %s' % ('option', 'Use only given module options'))
	out.append('  --%-30s %s' % ('append-option', 'Append the module options'))
	out.append('  --%-30s %s' % ('customattribute', 'Set custom attribute foo=bar'))
	out.append('  --%-30s %s' % ('customattribute-remove', 'Remove custom attribute'))
	out.append('  --%-30s %s' % ('policy-reference', 'Reference to policy given by DN'))
	out.append('  --%-30s %s' % ('policy-dereference', 'Remove reference to policy given by DN'))
	out.append('  --%-30s %s' % ('tls', '0 (no); 1 (try); 2 (must)'))
	out.append('')
	out.append('remove options:')
	out.append('  --%-30s %s' % ('binddn', 'bind DN'))
	out.append('  --%-30s %s' % ('bindpwd', 'bind password'))
	out.append('  --%-30s %s' % ('dn', 'Remove object with DN'))
	out.append('  --%-30s %s' % ('superordinate', 'Use superordinate module'))
	out.append('  --%-30s %s' % ('arg', 'Remove object with ARG'))
	out.append('  --%-30s %s' % ('filter', 'Lookup filter e.g. foo=bar'))
	out.append('  --%-30s %s' % ('tls', '0 (no); 1 (try); 2 (must)'))
	out.append('  --%-30s %s' % ('remove_referring', 'remove referring objects'))
	out.append('  --%-30s %s' % ('recursive', 'remove objects and their sub-objects'))
	out.append('')
	out.append('list options:')
	out.append('  --%-30s %s' % ('filter', 'Lookup filter e.g. foo=bar'))
	out.append('  --%-30s %s' % ('policies', 'List policy-based settings:'))
	out.append('    %-30s %s' % ('', '0:short, 1:long (with policy-DN)'))
	out.append('')
	out.append('move options:')
	out.append('  --%-30s %s' % ('binddn', 'bind DN'))
	out.append('  --%-30s %s' % ('bindpwd', 'bind password'))
	out.append('  --%-30s %s' % ('dn', 'Move object with DN'))
	out.append('  --%-30s %s' % ('position', 'Move to position in tree'))
	out.append('')
	out.append('Description:')
	out.append('  univention-admin is a tool to handle the configuration for UCS')
	out.append('  on command line level.')
	out.append('  Use "univention-admin modules" for a list of available modules.')
	out.append('')
	out.append('Known-Bugs:')
	out.append('  -None-')
	out.append('')
	return out

def version():
	o=[]
	o.append('univention-admin @%@package_version@%@')
	return o

def module_usage(information, action=''):
	out=[]
	for module, l in information.items():
		properties, options = l

		if options:
			out.append('')
			out.append('%s options:' % module.module)
			for name, option in options.items():
				out.append('  %-32s %s' % (name, option.short_description))

		out.append('')
		out.append('%s variables:' % module.module)

		if not hasattr(module,"layout"):
			continue
		for moduletab in module.layout:
			out.append('  %s:' % (moduletab.short_description))

			for row in moduletab.fields:
				for field in row:
					if type(field) != type([]):
						field=[field]

					for f in field:
						name=f.property
						if name == "filler":
							continue
						property=module.property_descriptions.get(name)
		
						required={}
						required['create']=0
						required['modify']=0
						required['remove']=0
						required['editable']=1
				
						if property.required:
							required['create']=1
						if property.identifies:
							required['modify']=1
							required['remove']=1
						if not property.editable:
							required['modify']=0
							required['remove']=0
							required['editable']=0
		
						flags=''
						if required.has_key(action) and required[action]:
							flags='*'
						elif not required.has_key(action):
							if required['create']:
								flags+='c'
							if required['modify']:
								flags+='m'
							if required['remove']:
								flags+='r'
							if not required['editable']:
								flags+='e'
						if property.options:
							if flags:
								flags+=','
							flags+=string.join(property.options, ',')
						if property.multivalue:
							if flags:
								flags+=','
							flags+='[]'
						if flags:
							flags='('+flags+')'
						
						out.append('    %-40s %s' % (name+' '+flags, property.short_description))
	return out

def module_information(module, identifies_only=0):
	information={module:[{},{}]}
	if 'superordinate' in dir(module) and module.superordinate:
		superordinate=univention.admin.modules.get(module.superordinate)
		information.update(module_information(superordinate, identifies_only=1))
	
	for name, property in module.property_descriptions.items():
		if (identifies_only and property.identifies) or (not identifies_only):
			information[module][0][name]=property
	if not identifies_only:
		if hasattr(module,'options'):
			for name, option in module.options.items():
				information[module][1][name]=option
	
	return information

def object_input(module, object, input, append=None, remove=None):
	out=[]
	if append:
		for key, value in append.items():
			if module.property_descriptions[key].syntax.name == 'file':
				if os.path.exists(value):
					fh = open(value, 'r')
					content=''
					for line in fh.readlines():
						content += line
					object[key] = content
					fh.close()
				else:
					out.append('WARNING: file not found: %s' % value)

			elif module.property_descriptions[key].syntax.type == 'complex':
				for i in range(0,len(value)):
					test_val=value[i].split('"')
					if test_val[0] and test_val[0] == value[i]:
						val=value[i].split(' ')
					else:
						val=[]
						for j in test_val:
							if j and j.rstrip().lstrip():
								val.append(j.rstrip().lstrip())
						
					if not object.has_key(key):
						object[key]=[]
					if val in object[key]:
						out.append('WARNING: can not append %s to %s, value exists'%(val,key))
					elif object[key] == ['']:
						object[key]=[val]
					else:
						object[key].append(val)
			else:
				for val in value:
					if val in object[key]:
						out.append('WARNING: can not append %s to %s, value exists'%(val,key))
					elif object[key] == [''] or object[key] == []:
						object[key]=[val]
					else:
						try:
							tmp = list(object[key])
							tmp.append(val)
							object[key] = list(tmp)
						except univention.admin.uexceptions.valueInvalidSyntax, errmsg:
							out.append('E: Invalid Syntax: %s' % str(errmsg))
	if remove:
		for key, value in remove.items():
			if module.property_descriptions[key].syntax.type == 'complex':
				if value:
					for i in range(0,len(value)):
						test_val=value[i].split('"')
						if test_val[0] and test_val[0] == value[i]:
							val=value[i].split(' ')
						else:
							val=[]
							out.append('test_val=%s' % test_val)
							for j in test_val:
								if j and j.rstrip().lstrip():
									val.append(j.rstrip().lstrip())

							for j in range(0,len(val)):
								val[j]='"%s"' % val[j]
								
						if val and val in object[key]:
							object[key].remove(val)
						else:
							out.append("WARNING: can not remove %s from %s, value does not exist"%(val,key))
				else:
					object[key]=[]

			else:
				for val in value:
					if val in object[key]:
						object[key].remove(val)
					else:
						out.append("WARNING: can not remove %s from %s, value does not exist"%(val,key))
	if input:
		for key, value in input.items():
			if module.property_descriptions[key].syntax.name == 'binaryfile':
				if value == '':
					object[key]=value
				elif os.path.exists(value):
					fh = open(value, 'r')
					content=fh.read()
					if "----BEGIN CERTIFICATE-----" in content:
						content = content.replace('----BEGIN CERTIFICATE-----','')
						content = content.replace('----END CERTIFICATE-----','')
						object[key]=base64.decodestring(content)
					else:
						object[key]= content
					fh.close()
				else:
					out.append('WARNING: file not found: %s' % value)

			elif module.property_descriptions[key].syntax.type == 'complex':
				if type(value) == type([]):
					for i in range(0,len(value)):
						test_val=value[i].split('"')
						if test_val[0] and test_val[0] == value[i]:
							val=value[i].split(' ')
						else:
							val=[]
							for j in test_val:
								if j and j.rstrip().lstrip():
									val.append(j.rstrip().lstrip())
				else:
					val=value.split(' ')
				if module.property_descriptions[key].multivalue:
					object[key]=[val]
				else:
					object[key]=val
			else:
				try:
					object[key]=value
				except univention.admin.uexceptions.ipOverridesNetwork, e:
					out.append('WARNING: %s' % e.message)
				except univention.admin.uexceptions.valueMayNotChange, e:
					raise univention.admin.uexceptions.valueMayNotChange, "%s: %s"%(e.message, key)
	return out

def list_available_modules(o=[]):
	
	o.append("Available Modules are:")
	avail_modules = []
	for mod in sys.modules.keys():
		if mod[:26] == "univention/admin/handlers/":
			avail_modules.append(mod[26:])
	avail_modules.sort()
	for mod in avail_modules:
		o.append("  %s"%mod)
	return o

def doit(arglist):
	
	out=[]
	# parse module and action
	if len(arglist) < 2:
		return usage() + ["OPERATION FAILED"]
	
	module_name=arglist[1]
	if module_name in ['-h', '--help', '-?']:
		return usage()
	
	if module_name == '--version':
		return version()
		
	if module_name == 'modules':
		return list_available_modules()
	
	try:
		module=univention.admin.modules.get(module_name)
	except:
		out.append("failed to get module %s."%module_name)
		out.append("")
		return list_available_modules(out) + ["OPERATION FAILED"]

	if not module:
		out.append("unknown module %s."%module_name)
		out.append("")
		return list_available_modules(out) + ["OPERATION FAILED"]
		
	information=module_information(module)
	
	if len(arglist) == 2:
		out = usage() + module_usage(information)
		return out + ["OPERATION FAILED"]
	
	action=arglist[2]
	
	if len(arglist) == 3 and action != 'list':
		out = usage() + module_usage(information, action)
		return out + ["OPERATION FAILED"]	
	
	remove_referring=0
	recursive=0
	# parse options
	longopts=['position=', 'dn=', 'arg=', 'set=', 'append=', 'remove=', 'superordinate=', 'option=', 'append-option=', 'filter=', 'tls=', 'ignore_exists', 'logfile=', 'policies=', 'binddn=', 'bindpwd=', 'customattribute=', 'customattribute-remove=','policy-reference=','policy-dereference=','remove_referring','recursive']
	try:
		opts, args=getopt.getopt(arglist[3:], '', longopts)
	except getopt.error, msg:
		out.append(str(msg))
		return out + ["OPERATION FAILED"]

	if not args == [] and type(args) == type([]):
		msg = "WARNING: the following arguments are ignored:"
		for argument in args:
			msg = '%s "%s"' % (msg, argument)
		out.append(msg)
	
	position_dn=''
	dn=''
	arg=None
	binddn=None
	bindpwd=None
	policyOptions=None
	logfile='/var/log/univention/admin-cmd.log'
	tls=2
	ignore_exists=0
	superordinate_dn=''
	parsed_append_options=[]
	parsed_options=[]
	filter=''
	input={}
	append={}
	remove={}
	customattribute={}
	customattribute_remove=[]
	policy_reference=[]
	policy_dereference=[]
	for opt, val in opts:
		if opt == '--position':
			position_dn=codecs.latin_1_decode(val)[0]
		elif opt == '--logfile':
			logfile=val
		elif opt == '--policies':
			policyOptions=" -s"
			if val=="1":
				policyOptions=" "
		elif opt == '--binddn':
			binddn=val
		elif opt == '--bindpwd':
			bindpwd=val
		elif opt == '--dn':
			dn=codecs.latin_1_decode(val)[0]
		elif opt == '--arg':
			arg=val
		elif opt == '--tls':
			tls=val
		elif opt == '--ignore_exists':
			ignore_exists=1
		elif opt == '--superordinate':
			superordinate_dn=val
		elif opt == '--option':
			parsed_options.append(val)
		elif opt == '--append-option':
			parsed_append_options.append(val)
		elif opt == '--filter':
			if '=' in val:
				filter=val
			else:
				msg="Filter is not valid"
				out.append(msg)
				return out + usage() + ["OPERATION FAILED"]
		elif opt == '--customattribute':
			pos=val.find('=')
			name=val[:pos]
			value=codecs.latin_1_decode(val[pos+1:])[0]
			if not customattribute.has_key(name):
				customattribute[name]=[]
			customattribute[name].append(value)
		elif opt == '--customattribute-remove':
			pos=val.find('=')
			if pos == -1:
				customattribute_remove.append((val,None))
			else:
				name=val[:pos]
				value=codecs.latin_1_decode(val[pos+1:])[0]
				customattribute_remove.append((name,value))
		elif opt == '--policy-reference':
			policy_reference.append(val)
		elif opt == '--policy-dereference':
			policy_dereference.append(val)
		elif opt == '--set':
			pos=val.find('=')
			name=val[:pos]
			value=codecs.latin_1_decode(val[pos+1:])[0]
			was_set=0
			for mod, (properties,options) in information.items():
				if properties.has_key(name):
					if properties[name].multivalue:
						if not input.has_key(name):
							input[name]=[]
						if value:
							input[name].append(value)
							was_set=1
					else:
						input[name]=value
						was_set=1
						
			if not was_set or name=='name':
				out.append("WARNING: No attribute with name '%s' in this module, value not set."%name)
		elif opt == '--append':
			pos=val.find('=')
			name=val[:pos]
			value=codecs.latin_1_decode(val[pos+1:])[0]
			was_set=0
			for mod, (properties,options) in information.items():
				if properties.has_key(name):
					if properties[name].multivalue:
						if not append.has_key(name):
							append[name]=[]
						if value:
							append[name].append(value)
							was_set=1
					else:
						append[name]=value
						was_set=1
			if not was_set:
				out.append("WARNING: No attribute with name %s in this module, value not appended."%name)
	
		elif opt == '--remove':
			pos=val.find('=')
			if pos == -1:
				name=val
				value=None
			else:
				name=val[:pos]
				value=codecs.latin_1_decode(val[pos+1:])[0]
			was_set=0
			for mod, (properties,options) in information.items():
				if properties.has_key(name):
					if properties[name].multivalue:
						if not remove.has_key(name):
							remove[name]=[]
						if value:
							remove[name].append(value)
							was_set=1
					else:
						remove[name]=value
						was_set=1
			if not was_set:
				out.append("WARNING: No attribute with name %s in this module, value not removed."%name)
		elif opt == '--remove_referring':
			remove_referring=1
		elif opt == '--recursive':
			recursive=1
	
	if logfile:
		univention.debug.init(logfile, 1, 0)
	else:
		out.append("WARNING: no logfile specified")
	
	baseConfig=univention_baseconfig.baseConfig()
	baseConfig.load()
	
	if baseConfig.has_key('ldap/master') and baseConfig['ldap/master']:
		co=univention.admin.config.config(baseConfig['ldap/master'])
	else:
		co=univention.admin.config.config()
	
	baseDN=baseConfig['ldap/base']
	
	if baseConfig.has_key('admin/cmd/debug/level'):
		debug_level=baseConfig['admin/cmd/debug/level']
	else:
		debug_level=0
	
	univention.debug.set_level(univention.debug.LDAP, int(debug_level))
	univention.debug.set_level(univention.debug.ADMIN, int(debug_level))
	
	if binddn and bindpwd:
		univention.debug.debug(univention.debug.ADMIN, univention.debug.INFO, "using %s account" % binddn)
		try:
			lo=univention.admin.uldap.access(host=baseConfig['ldap/master'], base=baseDN, binddn=binddn, start_tls=tls, bindpw=bindpwd)
		except Exception, e:
	   		univention.debug.debug(univention.debug.ADMIN, univention.debug.WARN, 'authentication error: %s' % str(e))
	   		out.append('authentication error: %s' % str(e))
			return out + ["OPERATION FAILED"]
	   		pass
	
	else:
		univention.debug.debug(univention.debug.ADMIN, univention.debug.INFO, "using cn=admin,%s account" % baseDN)
		try:
			secretFile=open('/etc/ldap.secret','r')
		except IOError:
			out.append('E: Permission denied, try --binddn and --bindpw')
			return out + ["OPERATION FAILED"]
		pwdLine=secretFile.readline()
		pwd=re.sub('\n','',pwdLine)
		
		try:
			lo=univention.admin.uldap.access(host=baseConfig['ldap/master'], base=baseDN, binddn='cn=admin,'+baseDN, bindpw=pwd, start_tls=tls)
		except Exception, e:
	   		univention.debug.debug(univention.debug.ADMIN, univention.debug.WARN, 'authentication error: %s' % str(e))
	   		out.append('authentication error: %s' % str(e))
			return out + ["OPERATION FAILED"]
	   		pass

	if superordinate_dn and univention.admin.modules.superordinate(module):
		superordinate=univention.admin.objects.get(univention.admin.modules.superordinate(module), co, lo, '', dn=superordinate_dn)
	else:
		superordinate=None
		
	if not position_dn and superordinate_dn:
		position_dn=superordinate_dn
	elif not position_dn:
		position_dn=baseDN

	try:
		position=univention.admin.uldap.position(baseDN)
		position.setDn(position_dn)
	except univention.admin.uexceptions.noObject:
		out.append('E: Invalid position')
		return out + ["OPERATION FAILED"]
	
	extraOC=[]
	extraAttributes=[]
	univention.admin.modules.init(lo,position,module)
	customattributes_set =[]
	if hasattr(module, 'ldap_extra_objectclasses') and action in ['modify','edit','create','new']:
		for oc, pname, syntax, ldapMapping, deleteValues, deleteObjectClass in module.ldap_extra_objectclasses:
			if customattribute.has_key(module.property_descriptions[pname].short_description):
				customattributes_set.append(module.property_descriptions[pname].short_description)
				extraOC.append(oc);
				# check multivalue
				if module.property_descriptions[pname].multivalue:
					if action in ['create','new'] or not dn or dn == '':
						values_found=[]
					else:
						values_found=lo.search(base=dn, attr=[ldapMapping])
					for i in customattribute[module.property_descriptions[pname].short_description]:
						value_already_set=0
						for tmp,val in values_found:
							if val.has_key(ldapMapping):
								if i in val[ldapMapping]:
									value_already_set=1
						if value_already_set:
							out.append('WARNING: customattribute %s is already set to %s'%(module.property_descriptions[pname].short_description,i))
						else:
							extraAttributes.append((ldapMapping,'',[i]))
				else:
					if len(customattribute[module.property_descriptions[pname].short_description])>1:
						out.append('WARNING: can not set singlevalue customattribute "%s" with more than one entry'%module.property_descriptions[pname].short_description)
					else:
						replaced=0
						if action in ['create','new'] or not dn or dn == '':
							values_found=[]
						else:
							values_found=lo.search(base=dn, attr=[ldapMapping])
						for tmp,val in values_found:
							if val.has_key(ldapMapping):
								extraAttributes.append((ldapMapping,val[ldapMapping][0],[customattribute[module.property_descriptions[pname].short_description][0]]))
								replaced = 1
								if len(val[ldapMapping]) > 1:
									out.append("WARNING: singlevalue customattribute %s has more than one value set, replace first"%customattribute[module.property_descriptions[pname].short_description])
						if not replaced:
							extraAttributes.append((ldapMapping,'',[customattribute[module.property_descriptions[pname].short_description][0]]))
	
	if action in ['modify','edit','create','new']:								
		for i in customattribute.keys():
			if not i in customattributes_set:
				out.append("WARNING: customattribute %s not found, value not set"%i)
	
		if policy_reference:
			for el in policy_reference:
				oc = lo.get(el,['objectClass'])
				if not oc:
					out.append("Object to be referenced does not exist:"+el)
					return out + ["OPERATION FAILED"]
				if not 'univentionPolicy' in oc['objectClass']:
					out.append("Object to be referenced is no valid Policy:"+el)
					return out + ["OPERATION FAILED"]
	

#+++# ACTION CREATE #+++#
	if action == 'create' or action == 'new':
			if hasattr(module,'operations') and module.operations:
				if not 'add' in module.operations:
					out.append('Create %s not allowed' % module_name)
					return out + ["OPERATION FAILED"]
			try:
				object=module.object(co, lo, position=position, superordinate=superordinate)
			except univention.admin.uexceptions.insufficientInformation:
				out.append('E: Insufficient information')
				out.append('Superordinate object is missing')
				return out + ["OPERATION FAILED"]
				
			if parsed_options:
				object.options=parsed_options
			object.open()
			if hasattr(object,'open_warning') and object.open_warning:
				out.append('WARNING:%s'%object.open_warning)
			try:
				out.extend(object_input(module, object, input, append=append))
			except univention.admin.uexceptions.nextFreeIp:
				if not ignore_exists:
					out.append('E: No free IP address found')
					return out + ['OPERATION FAILED']
			except univention.admin.uexceptions.valueInvalidSyntax, err:
				if not ignore_exists:
					out.append('E: Invalid Syntax: %s' % err)
					return out + ["OPERATION FAILED"]
				else:
					exists=1
			exists=0
			try:
				dn=object.create()
			except univention.admin.uexceptions.objectExists:
				if not ignore_exists:
					out.append('E: Object exists')
					return out + ["OPERATION FAILED"]
				else:
					exists=1
			except univention.admin.uexceptions.uidAlreadyUsed:
				if not ignore_exists:
					out.append('E: Object exists')
					return out + ["OPERATION FAILED"]
				else:
					exists=1
			except univention.admin.uexceptions.groupNameAlreadyUsed:
				if not ignore_exists:
					out.append('E: Object exists')
					return out + ["OPERATION FAILED"]
				else:
					exists=1
			except univention.admin.uexceptions.dhcpServerAlreadyUsed:
				if not ignore_exists:
					out.append('E: Object exists')
					return out + ["OPERATION FAILED"]
				else:
					exists=1
			except univention.admin.uexceptions.macAlreadyUsed:
				if not ignore_exists:
					out.append('E: Object exists')
					return out + ["OPERATION FAILED"]
				else:
					exists=1
			except univention.admin.uexceptions.noLock:
				if not ignore_exists:
					out.append('E: Object exists')
					return out + ["OPERATION FAILED"]
				else:
					exists=1
			except univention.admin.uexceptions.invalidDhcpEntry:
				out.append('E: The DHCP entry for this host should contain the zone dn, the ip address and the mac address.')
				return out + ["OPERATION FAILED"]
			except univention.admin.uexceptions.invalidOptions, e:
				if not ignore_exists:
					out.append('E: invalid Options: %s'%e)
					return out + ["OPERATION FAILED"]
			except univention.admin.uexceptions.insufficientInformation:
				out.append('E: Insufficient information')
				out.append('The following parameters are missing:')
				for i in module.property_descriptions:
					property=module.property_descriptions.get(i)
					if property.required:
						if not object.has_key(i) or not object[i]:
							out.append(i)
				return out + ["OPERATION FAILED"]
			except univention.admin.uexceptions.noObject:
				out.append('E: object not found')
				return out + ["OPERATION FAILED"]
					
			if extraOC or extraAttributes:
				if extraOC:
					oc=lo.search(base=dn, scope='base', attr=['objectClass'])
			
					noc=[]
					for i in range(len(oc[0][1]['objectClass'])):
						noc.append(oc[0][1]['objectClass'][i])
		
					for i in range(len(extraOC)):
						if extraOC[i] not in noc:
							noc.append(extraOC[i])
	
					if oc != noc:
						extraAttributes.append(('objectClass',oc,noc))
	
				if extraAttributes:
					lo.modify(dn,extraAttributes)
	
			if policy_reference:
				lo.modify(dn,[('objectClass','','univentionPolicyReference')])
				modlist=[]
				for el in policy_reference:
					modlist.append(('univentionPolicyReference','',el))
				lo.modify(dn,modlist)
	
			if exists == 1:
				out.append('Object exists')
			else:
				if not dn:
					dn=object.dn
				out.append('Object created: %s' % codecs.latin_1_encode(dn)[0])
		
#+++# ACTION MODIFY #+++#
	elif action == 'modify' or action == 'edit' or action == 'move':
	
		object_modified = 0

		if hasattr(module,'operations') and module.operations:
			if not 'edit' in module.operations:
				out.append('Modify %s not allowed' % module_name)
				return out + ["OPERATION FAILED"]

		try:
			object=univention.admin.objects.get(module, co, lo, position='', dn=dn, arg=arg)
		except univention.admin.uexceptions.noObject:
			out.append('E: object not found')
			return out + ["OPERATION FAILED"]
			
		object.open()
		if hasattr(object,'open_warning') and object.open_warning:
			out.append('WARNING:%s'%object.open_warning)

		if action == 'move':
			if hasattr(module,'operations') and module.operations:
				if not 'move' in module.operations:
					out.append('Move %s not allowed' % module_name)
					return out + ["OPERATION FAILED"]
			if not position_dn:
				out.append("need new position for moving object")
			else:
				res = ''
				try: # check if goal-position exists
					res = lo.get(position_dn)
				except:
					pass
				if not res:
					out.append("position does not exsist: %s"%position_dn)
					return out + ["OPERATION FAILED"]
				rdn = dn[:string.find(dn,',')]
				newdn="%s,%s" % (rdn,position_dn)
				try:
					object.move(newdn)
					object_modified+=1
				except univention.admin.uexceptions.noObject:
					out.append('E: object not found')
					return out + ["OPERATION FAILED"]
				except univention.admin.uexceptions.ldapError, msg:
					out.append("ldap Error: %s"%msg)
					return out + ["OPERATION FAILED"]
				except univention.admin.uexceptions.nextFreeIp:
					out.append('E: No free IP address found')
					return out + ['OPERATION FAILED']
				except univention.admin.uexceptions.valueInvalidSyntax, err:
					out.append('E: Invalid Syntax: %s' % err)
					return out + ["OPERATION FAILED"]

		else: # modify


			if (len(input)+len(append)+len(remove)+len(parsed_append_options)+len(parsed_options))>0:
				if parsed_options:
					object.options=parsed_options
				if parsed_append_options:
					for option in parsed_append_options:
						object.options.append(option)
				try:
					out.extend(object_input(module, object, input, append, remove))
				except univention.admin.uexceptions.valueMayNotChange,e:
						out.append(unicode(e[0]))
					return out + ["OPERATION FAILED"]
				if object.hasChanged(input.keys()) or object.hasChanged(append.keys()) or object.hasChanged(remove.keys()) or parsed_append_options or parsed_options:
					try:
						dn=object.modify()
						object_modified+=1
					except univention.admin.uexceptions.noObject:
						out.append('E: object not found')
						return out + ["OPERATION FAILED"]
					except univention.admin.uexceptions.invalidDhcpEntry:
						out.append('E: The DHCP entry for this host should contain the zone dn, the ip address and the mac address.')
						return out + ["OPERATION FAILED"]

			if extraOC or extraAttributes:
				if extraOC:
					oc=lo.search(base=dn, scope='base', attr=['objectClass'])

					noc=[]
					for i in range(len(oc[0][1]['objectClass'])):
						noc.append(oc[0][1]['objectClass'][i])

					for i in range(len(extraOC)):
						if not extraOC[i] in noc:
							noc.append(extraOC[i])

					if noc != oc[0][1]['objectClass']:
						extraAttributes.append(('objectClass',oc[0][1]['objectClass'],noc))
				if extraAttributes:
					try:
						lo.modify(dn,extraAttributes)
						object_modified+=1
					except univention.admin.uexceptions.ldapError, msg:
						out.append("ldap Error: %s"%msg)

			if customattribute_remove:
				extraAttributes=[]
				removed_attributes=[]
				if hasattr(module, 'ldap_extra_objectclasses'):
					for oc, pname, syntax, ldapMapping, deleteValues, deleteObjectClass in module.ldap_extra_objectclasses:
						for index in range(0,len(customattribute_remove)):
							if customattribute_remove[index][0] == module.property_descriptions[pname].short_description:
								for tmp,val in lo.search(base=dn, attr=[ldapMapping]):
									if val.has_key(ldapMapping):
										for i in range(0, len(val[ldapMapping])):
											if (not customattribute_remove[index][1]) or customattribute_remove[index][1] == val[ldapMapping][i]:
												extraAttributes.append((ldapMapping,val[ldapMapping][i],''))
												removed_attributes.append(module.property_descriptions[pname].short_description)
									else:
										out.append("customattribute %s not set"%module.property_descriptions[pname].short_description)
										removed_attributes.append(module.property_descriptions[pname].short_description)

				if extraAttributes:
					lo.modify(dn,extraAttributes)
					object_modified+=1

				for n,v in customattribute_remove:
					if not n in removed_attributes:
						out.append("WARNING: customattribute %s not found"%n)

			if policy_reference:
				if 'univentionPolicyReference' not in lo.get(dn,['objectClass'])['objectClass']:
					lo.modify(dn,[('objectClass','','univentionPolicyReference')])
					object_modified+=1
				modlist=[]
				for el in policy_reference:
					modlist.append(('univentionPolicyReference','',el))
				lo.modify(dn,modlist)
				object_modified+=1

			if policy_dereference:
				modlist=[]
				for el in policy_dereference:
					modlist.append(('univentionPolicyReference',el,''))
				lo.modify(dn,modlist)
				object_modified+=1

		if object_modified > 0:
			out.append('Object modified: %s'% codecs.latin_1_encode(dn)[0])
		else:
			out.append('No modification: %s'% codecs.latin_1_encode(dn)[0])

	elif action == 'remove' or action == 'delete':

		if hasattr(module,'operations') and module.operations:
			if not 'remove' in module.operations:
				out.append('Remove %s not allowed' % module_name)
				return out + ["OPERATION FAILED"]

		try:
			if dn and filter:
				object=univention.admin.modules.lookup(module, co, lo, scope='sub', superordinate=superordinate, base=dn, filter=filter, required=1, unique=1)[0]
			elif dn:
				object=univention.admin.modules.lookup(module, co, lo, scope='base', superordinate=superordinate, base=dn, filter=filter, required=1, unique=1)[0]
			elif filter:
				object=univention.admin.modules.lookup(module, co, lo, scope='sub', superordinate=superordinate, base=position.getDn(), filter=filter, required=1, unique=1)[0]
			else:
				out.append('E: dn or filter needed')
				return out + ["OPERATION FAILED"]
		except univention.admin.uexceptions.noObject:
			out.append('E: object not found')
			return out + ["OPERATION FAILED"]
			
		object.open()
		if hasattr(object,'open_warning') and object.open_warning:
			out.append('WARNING:%s'%object.open_warning)

		if remove_referring and univention.admin.objects.wantsCleanup(object):
				univention.admin.objects.performCleanup(object)

		if recursive:
			try:
				object.remove(recursive)
			except univention.admin.uexceptions.ldapError:
				out.append('E: Operation on non empty Objects is not allowed')
				return out + ["OPERATION FAILED"]
		else:
			try:
				object.remove()
			except univention.admin.uexceptions.primaryGroupUsed:
				out.append('E: object in use')
				return out + ["OPERATION FAILED"]
		out.append('Object removed: %s'% codecs.latin_1_encode(dn)[0])

	elif action == 'list' or action == 'lookup':

		if hasattr(module,'operations') and module.operations:
			if not 'search' in module.operations:
				out.append('Search %s not allowed' % module_name)
				return out + ["OPERATION FAILED"]

		out.append(codecs.latin_1_encode(filter)[0])

		for object in univention.admin.modules.lookup(module, co, lo, scope='sub', superordinate=superordinate, base=position.getDn(), filter=filter):
			out.append('DN: %s' % codecs.latin_1_encode(univention.admin.objects.dn(object))[0])
			out.append('ARG: %s' % univention.admin.objects.arg(object))

			if (hasattr(module,'virtual') and not module.virtual) or not hasattr(module,'virtual'):
				object.open()
				if hasattr(object,'open_warning') and object.open_warning:
					out.append('WARNING: %s'%object.open_warning)
				for key, value in object.items():
					s=module.property_descriptions[key].syntax
					if module.property_descriptions[key].multivalue:
						for v in value:
							if s.tostring(v):
								out.append('  %s: %s' % (codecs.latin_1_encode(key)[0], codecs.latin_1_encode(s.tostring(v))[0]))
							else:
								out.append('  %s: %s' % (codecs.latin_1_encode(key)[0], None))
					else:
						if s.tostring(value):
							out.append('  %s: %s' % (codecs.latin_1_encode(key)[0], codecs.latin_1_encode(s.tostring(value))[0]))
						else:
							out.append('  %s: %s' % (codecs.latin_1_encode(key)[0], None))

				if 'univentionPolicyReference' in lo.get(univention.admin.objects.dn(object),['objectClass'])['objectClass']:
					references = lo.get(codecs.latin_1_encode(univention.admin.objects.dn(object))[0],['univentionPolicyReference'])
					if references:
						for el in references['univentionPolicyReference']:
							out.append('  %s: %s' % ('univentionPolicyReference', codecs.latin_1_encode(s.tostring(el))[0]))
					
			if policyOptions:
				policyResults=os.popen('univention_policy_result %s %s'%(policyOptions,codecs.latin_1_encode(univention.admin.objects.dn(object))[0]))
				out.append("  Policy-based Settings:")
				line = policyResults.readline()
				policy=''
				value=[]
				client={}
				while not line == "":
					if not (line.strip() == "" or line.strip()[:4]=="DN: " or line.strip()[:7]=="POLICY "):
						out.append("    %s"%line.strip())
						if policyOptions==" ":
							clsplit=string.split(line.strip(), ': ')
							if clsplit[0] == 'Policy':
								if policy:
									client[attribute]=[policy, value]
									value=[]
								policy=clsplit[1]
							elif clsplit[0] == 'Attribute':
								attribute=clsplit[1]
							elif clsplit[0] == 'Value':
								value.append(clsplit[1])
						else:
							clsplit=string.split(line.strip(), '=')
							if not client.has_key(clsplit[0]):
								client[clsplit[0]] = []
							client[clsplit[0]].append(clsplit[1])

					line = policyResults.readline()

				if policyOptions==" ":
					client[attribute]=[policy, value]
					value=[]

				out.append('')	

				if module_name == 'dhcp/host':
						subnet_module=univention.admin.modules.get('dhcp/subnet')
						for subnet in univention.admin.modules.lookup(subnet_module, co, lo, scope='sub', superordinate=superordinate, base='', filter=''):

							if univention.admin.ipaddress.ip_is_in_network(subnet['subnet'], subnet['subnetmask'], object['fixedaddress'][0]):
								policyResults=os.popen('univention_policy_result %s %s'%(policyOptions,codecs.latin_1_encode(subnet.dn)[0]))
								out.append("  Subnet-based Settings:")
								line = policyResults.readline()
								ddict={}
								policy=''
								value=[]
								while not line == "":
									if not (line.strip() == "" or line.strip()[:4]=="DN: " or line.strip()[:7]=="POLICY "):
										out.append("    %s"%line.strip())
										if policyOptions==" ":
											subsplit=string.split(line.strip(), ': ')
											if subsplit[0] == 'Policy':
												if policy:
													ddict[attribute]=[policy, value]
													value=[]
												policy=subsplit[1]
											elif subsplit[0] == 'Attribute':
												attribute=subsplit[1]
											elif subsplit[0] == 'Value':
												value.append(subsplit[1])
										else:
											subsplit=string.split(line.strip(), '=')
											if not ddict.has_key(subsplit[0]):
												ddict[subsplit[0]] = []
											ddict[subsplit[0]].append(subsplit[1])

									line = policyResults.readline()

								out.append('')	

								if policyOptions==" ":
									ddict[attribute]=[policy, value]
									value=[]

								out.append("  Merged Settings:")

								for key in ddict.keys():
									if not client.has_key(key):
										client[key]=ddict[key]



								if policyOptions==" ":
									for key in client.keys():
										out.append("    Policy: "+client[key][0])
										out.append("    Attribute: "+key)
										for i in range(0, len(client[key][1])):
											out.append("    Value: "+client[key][1][i])
								else:
									for key in client.keys():
										for i in range(0, len(client[key])):
											out.append("    %s=%s" % (key, client[key][i]))
								out.append('')	

			out.append('')

	else:
		out.append("Unknown or no action defined")
		out.append('')	
		usage()
		return out + ["OPERATION FAILED"]

	return out # nearly the only successfull return
	
