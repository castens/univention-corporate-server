#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
#
# Univention Configuration Registry
#  main configuration registry classes
#
# Copyright (C) 2004-2009 Univention GmbH
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

import os, sys, re, string, cPickle, types, copy, subprocess
import fcntl
import pwd, grp

variable_pattern = re.compile('@%@([^@]+)@%@')
variable_token = re.compile('@%@')
execute_token = re.compile('@!@')
warning_pattern = re.compile('(UCRWARNING|BCWARNING|UCRWARNING_ASCII)=(.+)')
file_dir = '/etc/univention/templates/files'
script_dir = '/etc/univention/templates/scripts'
module_dir = '/etc/univention/templates/modules'
info_dir = '/etc/univention/templates/info'
cache_file = '/var/cache/univention-config/cache'
cache_version = 1
cache_version_min = 0
cache_version_max = 1
cache_version_text = 'univention-config cache, version'
cache_version_notice = '%s %s\n' % (cache_version_text, cache_version)
cache_version_re = re.compile('^%s (P<version>[0-9]+)$' % cache_version_text)

invalid_key_chars = re.compile ('[\\r\\n\!\"\§\$\%\&\(\)\[\]\{\}\=\?\`\+\#\'\,\;\<\>\\\]')
invalid_value_chars = '\r\n'
shell_valid_key_chars = string.ascii_letters + string.digits + '_'

warning_text='''Warning: This file is auto-generated and might be overwritten by
         univention-config-registry.
         Please edit the following file(s) instead:
Warnung: Diese Datei wurde automatisch generiert und kann durch
         univention-config-registry überschrieben werden.
         Bitte bearbeiten Sie an Stelle dessen die folgende(n) Datei(en):'''

sys.path.insert(0, '')

def warning_string(prefix='# ', width=80, srcfiles=[], enforce_ascii=False):
	res = []

	for line in warning_text.split('\n'):
		if enforce_ascii:
			line = replaceUmlaut(line).encode ('ascii', 'replace')
		res.append(prefix+line)
	res.append(prefix)

	for srcfile in srcfiles:
		if enforce_ascii:
			srcfile = srcfile.encode ('ascii', 'replace')
		res.append(prefix+'\t%s' % srcfile)
	res.append(prefix)

	return "\n".join(res)

def filesort(x,y):
	return cmp(os.path.basename(x), os.path.basename(y))

class ConfigRegistry( dict ):
	NORMAL, LDAP, SCHEDULE, FORCED, CUSTOM = range( 5 )
	PREFIX = '/etc/univention'
	BASES = { NORMAL : 'base.conf', LDAP : 'base-ldap.conf', SCHEDULE : 'base-schedule.conf', FORCED : 'base-forced.conf' }

	def __init__( self, filename = None, write_registry = NORMAL ):
		if os.getenv( 'UNIVENTION_BASECONF' ):
			self.file = os.getenv( 'UNIVENTION_BASECONF' )
		elif filename:
			self.file = filename
		else:
			self.file = None
		if self.file:
			self._write_registry = ConfigRegistry.CUSTOM
		else:
			self._write_registry = write_registry
		self._registry = {}
		if not self.file:
			self._registry[ ConfigRegistry.NORMAL ] = self._create_registry( ConfigRegistry.NORMAL )
			self._registry[ ConfigRegistry.LDAP ] = self._create_registry( ConfigRegistry.LDAP )
			self._registry[ ConfigRegistry.SCHEDULE ] = self._create_registry( ConfigRegistry.SCHEDULE )
			self._registry[ ConfigRegistry.FORCED ] = self._create_registry( ConfigRegistry.FORCED )
			self._registry[ ConfigRegistry.CUSTOM ] = {}
		else:
			self._registry[ ConfigRegistry.NORMAL ] = {}
			self._registry[ ConfigRegistry.LDAP ] = {}
			self._registry[ ConfigRegistry.SCHEDULE ] = {}
			self._registry[ ConfigRegistry.FORCED ] = {}
			self._registry[ ConfigRegistry.CUSTOM ] = self._create_registry( ConfigRegistry.CUSTOM )

	def _create_registry( self, reg ):
		if reg == ConfigRegistry.CUSTOM:
			return _ConfigRegistry( file = self.file )
		else:
			return _ConfigRegistry( file = os.path.join( ConfigRegistry.PREFIX, ConfigRegistry.BASES[ reg ] ) )
	def load( self ):
		for reg in self._registry.values():
			if isinstance( reg, _ConfigRegistry ):
				reg.load()

	def save( self ):
		self._registry[ self._write_registry ].save()

	def lock( self ):
		self._registry[ self._write_registry ].lock()

	def unlock( self ):
		self._registry[ self._write_registry ].unlock()

	def __delitem__( self, key ):
		if self._registry[ self._write_registry ].has_key( key ):
			del self._registry[ self._write_registry ][ key ]

	def __getitem__( self, key ):
		return self.get( key )

	def __setitem__( self, key, value ):
		self._registry[ self._write_registry ][ key ] = value

	def __contains__( self, key ):
		for reg in ( ConfigRegistry.FORCED, ConfigRegistry.SCHEDULE, ConfigRegistry.LDAP,
					 ConfigRegistry.NORMAL, ConfigRegistry.CUSTOM ):
			if key in self._registry[ reg ]:
				return True
		return False

	def iterkeys ( self ):
		merge = self._merge()
		for key in merge:
			yield key

	__iter__ = iterkeys

	def get( self, key, default = None ):
		for reg in ( ConfigRegistry.FORCED, ConfigRegistry.SCHEDULE, ConfigRegistry.LDAP, ConfigRegistry.NORMAL ):
			if self._registry[ reg ].has_key( key ):
				return self._registry[ reg ][ key ]
		
		return self._registry[ ConfigRegistry.CUSTOM ].get( key, default )

	def has_key( self, key, write_registry_only = False ):
		if write_registry_only:
			return self._registry[ self._write_registry ].has_key( key )
		else:
			return self.get( key, None ) != None

	def _merge( self ):
		merge = {}
		for reg in ( ConfigRegistry.FORCED, ConfigRegistry.SCHEDULE, ConfigRegistry.LDAP, ConfigRegistry.NORMAL,
					 ConfigRegistry.CUSTOM ):
			if not isinstance( self._registry[ reg ], _ConfigRegistry ):
				continue
			for key in self._registry[ reg ].keys():
				if not merge.has_key( key ):
					merge[ key ] = self._registry[ reg ][ key ]
		return merge

	def items( self ):
		merge = self._merge()
		return merge.items()

	def keys( self ):
		merge = self._merge()
		return merge.keys()

	def values( self ):
		merge = self._merge()
		return merge.values()

	def __str__( self ):
		merge = self._merge()
		return '\n'.join( [ '%s: %s' % ( key, val ) for key, val in merge.items() ] )

class _ConfigRegistry( dict ):
	def __init__(self, file = None):
		dict.__init__( self )
		if file:
			self.file = file
		else:
			self.file = '/etc/univention/base.conf'
		self.__create_base_conf()
		self.backup_file = self.file + '.bak'
		self.lock_filename = self.file + '.lock'

	def load(self):
		self.clear()
		import_failed = 0
		try:
			fp = open(self.file, 'r')
		except:
			import_failed = 1

		if import_failed or len(fp.readlines()) < 3: # only comment or nothing
			import_failed = 1 # not set if file is to short
			try:
				fp = open(self.backup_file, 'r')
			except IOError:
				return

		fp.seek(0)
		for line in fp.readlines():
			comment = line.find('#')
			if comment != -1:
				line = line[:comment]
			if line == '':
				continue
			if line.find(': ') == -1:
				continue

			key, value = line.split(': ', 1)
			value = value.strip()
			if len(value) == 0: #if variable was set without an value
				value = ''

			self[key] = value
		fp.close()

		if import_failed:
			self.__save_file(self.file)

	def __create_base_conf( self ):
		if not os.path.exists( self.file ):
			try:
				fd = os.open( self.file, os.O_CREAT | os.O_RDONLY, 0644 )
				os.close( fd )
			except OSError:
				print "error: the configuration file '%s' does not exist und could not be created" % self.file
				exception_occured()

	def __save_file(self, filename):
		try:
			# open temporary file for writing
			fp = open(filename, 'w')
			# write data to file
			fp.write('# univention_ base.conf\n\n')
			fp.write(self.__str__())
			# flush (meta)data
			fp.flush()
			os.fsync(fp.fileno())
			# close fd
			fp.close()
		except IOError, (errno, strerror):
			# errno 13: Permission denied
			#
			# suppress certain errors
			if not errno in [ 13 ]:
				raise

	def save(self):
		for filename in (self.backup_file, self.file):
			self.__save_file(filename)

	def lock(self):
		self.lock_file = open(self.lock_filename, "a+")
		fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX)

	def unlock(self):
		self.lock_file.close()

	def __getitem__(self, key):
		try:
			return dict.__getitem__( self, key )
		except KeyError:
			return ''

	def removeInvalidChars (self, seq):
		for letter in invalid_value_chars:
			seq = seq.replace(letter,'')
		return seq

	def __str__(self):
		return '\n'.join(['%s: %s' % (key, self.removeInvalidChars (val)) for key, val in self.items()])

# old class name
baseConfig = ConfigRegistry

def directoryFiles(dir):
	all = []
	def _walk(all, dirname, files):
		for file in files:
			f = os.path.join(dirname, file)
			if os.path.isfile(f):
				all.append(f)
	os.path.walk(dir, _walk, all)
	return all

def filter(template, dir, srcfiles=[], opts = {}):

	while 1:
		i = variable_token.finditer(template)
		try:
			start = i.next()
			end = i.next()
			name = template[start.end():end.start()]

			if dir.has_key(name):
				value = dir[name]
			else:
				match = warning_pattern.match(name)
				if match:
					mode = match.group(1)
					prefix = match.group(2)
					if mode == "UCRWARNING_ASCII":
						value = warning_string(match.group(2), srcfiles=srcfiles, enforce_ascii=True)
					else:
						value = warning_string(match.group(2), srcfiles=srcfiles)
				else:
					value = ''

			if type(value) == types.ListType or type(value) == types.TupleType:
				value = value[0]
			template = template[:start.start()]+value+template[end.end():]
		except StopIteration:
			break

	while 1:
		i = execute_token.finditer(template)
		try:
			start = i.next()
			end = i.next()

			p = subprocess.Popen('/usr/bin/python2.4', shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
			child_stdin, child_stdout = p.stdin, p.stdout
			if opts.get( 'encode-utf8', False ):
				child_stdin.write('# -*- coding: utf-8 -*-\n')
			child_stdin.write('import univention.config_registry\n')
			child_stdin.write('configRegistry = univention.config_registry.ConfigRegistry()\n')
			child_stdin.write('configRegistry.load()\n')
			# for compatibility
			child_stdin.write('baseConfig = configRegistry\n')
			child_stdin.write(template[start.end():end.start()])
			child_stdin.close()
			value=child_stdout.read()
			child_stdout.close()
			template = template[:start.start()]+value+template[end.end():]

		except StopIteration:
			break

	return template

def runScript(script, arg, changes):

	s = ''
	for key, value in changes.items():
		if value and len(value) > 1 and value[0] and value[1]:
			s += '%s@%%@%s@%%@%s\n' % (key, value[0], value[1])

	p = subprocess.Popen(script+" "+arg, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
	p_out, p_in = p.stdin, p.stdout
	p_out.write(s)
	p_out.close()
	p_in.close()

def runModule(modpath, arg, bc, changes):
	arg2meth = { 'generate': lambda obj: getattr(obj, 'handler'),
		     'preinst':  lambda obj: getattr(obj, 'preinst'),
		     'postinst': lambda obj: getattr(obj, 'postinst') }
	try:
		module = __import__(os.path.join(module_dir, os.path.splitext(modpath)[0]))
		arg2meth[arg](module)(bc, changes)
	except (AttributeError, ImportError), err:
		print err

class configHandler:
	variables = []

class configHandlerMultifile(configHandler):

	def __init__(self, dummy_from_file, to_file):
		self.variables = []
		self.from_files = []
		self.dummy_from_file = dummy_from_file
		self.to_file = to_file
		self.user = None
		self.group = None
		self.mode = None
		self.encode_utf8 = False

	def addSubfiles(self, subfiles):
		for from_file, variables in subfiles:
			if not from_file in self.from_files:
				self.from_files.append(from_file)
			for variable in variables:
				if not variable in self.variables:
					self.variables.append(variable)

	def __call__(self, args):
		bc, changed = args
		self.from_files.sort(filesort)
		print 'Multifile: %s' % self.to_file

		to_dir = os.path.dirname(self.to_file)
		if not os.path.isdir(to_dir):
			os.makedirs(to_dir, 0755)

		if os.path.isfile(self.dummy_from_file):
			st = os.stat(self.dummy_from_file)
		else:
			st = None
		to_fp = open(self.to_file, 'w')

		filter_opts = {}
		if self.encode_utf8:
			filter_opts['encode-utf8'] = True

		for from_file in self.from_files:
			try:
				from_fp = open(from_file)
			except IOError:
				continue
			to_fp.write(filter(from_fp.read(), bc, srcfiles = self.from_files, opts = filter_opts))

		if self.user or self.group or self.mode:
			if self.mode:
				os.chmod(self.to_file, self.mode)
			if self.user and self.group:
				os.chown(self.to_file, self.user, self.group)
			elif self.user:
				os.chown(self.to_file, self.user, 0)
			elif self.group:
				os.chown(self.to_file, 0, self.group)
		elif st:
			os.chmod(self.to_file, st[0])

class configHandlerFile(configHandler):

	def __init__(self, from_file, to_file):
		self.from_file = from_file
		self.to_file = to_file
		self.preinst = None
		self.postinst = None
		self.user = None
		self.group = None
		self.mode = None
		self.encode_utf8 = False

	def __call__(self, args):
		bc, changed = args

		if hasattr( self, 'preinst') and self.preinst:
			runModule(self.preinst, 'preinst', bc, changed)

		print 'File: %s' % self.to_file

		to_dir = os.path.dirname(self.to_file)
		if not os.path.isdir(to_dir):
			os.makedirs(to_dir, 0755)

		try:
			st = os.stat(self.from_file)
		except OSError:
			print "The referenced template file does not exist"
			return None
		from_fp = open(self.from_file)
		to_fp = open(self.to_file, 'w')

		filter_opts = {}
		if self.encode_utf8:
			filter_opts['encode-utf8'] = True

		to_fp.write(filter(from_fp.read(), bc, srcfiles = [self.from_file], opts = filter_opts))

		if self.user or self.group or self.mode:
			if self.mode:
				os.chmod(self.to_file, self.mode)
			if self.user and self.group:
				os.chown(self.to_file, self.user, self.group)
			elif self.user:
				os.chown(self.to_file, self.user, 0)
			elif self.group:
				os.chown(self.to_file, 0, self.group)
		else:
			os.chmod(self.to_file, st[0])
		from_fp.close()
		to_fp.close()

		if hasattr( self, 'postinst' ) and self.postinst:
			runModule(self.postinst, 'postinst', bc, changed)

		script_file = self.from_file.replace(file_dir, script_dir)
		if os.path.isfile(script_file):
			runScript(script_file, 'postinst', changed)

class configHandlerScript(configHandler):

	def __init__(self, script):
		self.script = script

	def __call__(self, args):
		bc, changed = args
		print 'Script: '+self.script
		if os.path.isfile(self.script):
			runScript(self.script, 'generate', changed)

class configHandlerModule(configHandler):

	def __init__(self, module):
		self.module = module

	def __call__(self, args):
		bc, changed = args
		print 'Module: '+self.module
		runModule(self.module, 'generate', bc, changed)

def parseRfc822(f):
	res = []
	entries = f.split('\n\n')
	for entry in entries:
		ent = {}
		lines = entry.split('\n')
		for line in lines:
			if line.find(': ') == -1:
				continue
			key, value = line.split(': ', 1)
			if not ent.has_key(key):
				ent[key] = []
			ent[key].append(value)
		res.append(ent)
	return res

def grepVariables(f):
	return variable_pattern.findall(f)

class configHandlers:

	_handlers = {}
	_files = {}
	_multifiles = {}
	_subfiles = {}

	def _check_cache_version(self, fp):
		version = 0
		line = fp.readline()	# IOError is propagated
		match = cache_version_re.match(line)
		if match:
			version = int(match.group('version'))
		# "Old style" cache (version 0) doesn't contain version notice
		else:
			fp.seek(0)
		return cache_version_min <= version <= cache_version_max

	def load(self):
		try:
			fp = open(cache_file, 'r')
			if not self._check_cache_version(fp):
				print "Invalid cache file version, exiting."
				fp.close()
				self.update()
				return
		except (IOError, ValueError):
			self.update()
			return
		p = cPickle.Unpickler(fp)
		try:
			self._handlers = p.load()
			self._files = p.load()
			self._subfiles = p.load()
			self._multifiles = p.load()
		except (cPickle.UnpicklingError, EOFError, AttributeError):
			fp.close()
			self.update()
			return
		fp.close()

	def stripBasepath(self, path, basepath):
		return path.replace(basepath, '')

	def getHandler(self, entry):

		if not entry.has_key('Type'):
			object = None
		elif entry['Type'][0] == 'file':
			from_path = os.path.join(file_dir, entry['File'][0])
			to_path = os.path.join('/', entry['File'][0])
			if not entry.has_key('File') or not os.path.exists(from_path):
				return None
			object = configHandlerFile(from_path, to_path)
			if not object:
				return None
			object.variables = grepVariables(open(from_path).read())
			if entry.has_key('Preinst'):
				object.preinst = entry['Preinst'][0]
			if entry.has_key('Postinst'):
				object.postinst = entry['Postinst'][0]
			if entry.has_key('Variables'):
				object.variables += entry['Variables']
			if entry.has_key('User'):
				try:
					object.user = pwd.getpwnam(entry['User'][0]).pw_uid
				except:
					print 'Warning: failed to convert the username %s to the uid' % entry['User'][0]
			if entry.has_key('Group'):
				try:
					object.group = grp.getgrnam(entry['Group'][0]).gr_gid
				except:
					print 'Warning: failed to convert the groupname %s to the gid' % entry['Group'][0]
			if entry.has_key('Mode'):
				object.mode = int(entry['Mode'][0], 8)
			if entry.has_key('Encode-utf8') and entry['Encode-utf8'][0].lower() in ['true', 'yes'] :
				object.encode_utf8 = True
		elif entry['Type'][0] == 'script':
			if not entry.has_key('Variables') or not entry.has_key('Script'):
				return None
			object = configHandlerScript(os.path.join(script_dir, entry['Script'][0]))
			object.variables = entry['Variables']
		elif entry['Type'][0] == 'module':
			if not entry.has_key('Variables') or not entry.has_key('Module'):
				return None
			object = configHandlerModule(os.path.splitext(entry['Module'][0])[0])
			object.variables = entry['Variables']
		elif entry['Type'][0] == 'multifile':
			if not entry.has_key('Multifile'):
				return None
			if self._multifiles.has_key(entry['Multifile'][0]):
				object = self._multifiles[entry['Multifile'][0]]
			else:
				object = configHandlerMultifile(os.path.join(file_dir, entry['Multifile'][0]), os.path.join('/', entry['Multifile'][0]))
			if entry.has_key('Variables'):
				object.variables += entry['Variables']
			if entry.has_key('User'):
				try:
					object.user = pwd.getpwnam(entry['User'][0]).pw_uid
				except:
					print 'Warning: failed to convert the username %s to the uid' % entry['User'][0]
			if entry.has_key('Group'):
				try:
					object.group = grp.getgrnam(entry['Group'][0]).gr_gid
				except:
					print 'Warning: failed to convert the groupname %s to the gid' % entry['Group'][0]
			if entry.has_key('Mode'):
				object.mode = int(entry['Mode'][0])
			if entry.has_key('Encode-utf8') and entry['Encode-utf8'][0].lower() in ['true', 'yes'] :
				object.encode_utf8 = True
			self._multifiles[entry['Multifile'][0]] = object
			if self._subfiles.has_key(entry['Multifile'][0]):
				object.addSubfiles(self._subfiles[entry['Multifile'][0]])
				del(self._subfiles[entry['Multifile'][0]])
		elif entry['Type'][0] == 'subfile':
			if not entry.has_key('Multifile') or not entry.has_key('Subfile'):
				return None
			mfile = entry['Multifile'][0]
			try:
				qentry = (os.path.join(file_dir, entry['Subfile'][0]), grepVariables(open(os.path.join(file_dir, entry['Subfile'][0])).read()))
			except IOError:
				print "The following Subfile doesnt exist: \n%s \nunivention-config-registry commit aborted" %(os.path.join(file_dir, entry['Subfile'][0]))
				sys.exit(1)
			# if multifile object does not exist jet, queue subfiles
			if self._multifiles.has_key(mfile):
				self._multifiles[mfile].addSubfiles([qentry])
				return self._multifiles[mfile]
			elif not self._subfiles.has_key(mfile):
				self._subfiles[mfile]=[]
			self._subfiles[mfile].append(qentry)
			object = None
		else:
			object = None
		return object

	def update(self):

		self._handlers.clear()
		self._files.clear()
		self._multifiles.clear()
		self._subfiles.clear()

		objects = []
		for file in directoryFiles(info_dir):
			if not file.endswith('.info'):
				continue
			for s in parseRfc822(open(file).read()):
				if not s.has_key('Type'):
					continue
				object = self.getHandler(s)
				if object:
					objects.append(object)
		for object in objects:
			for v in object.variables:
				if not self._handlers.has_key(v):
					self._handlers[v] = []
				self._handlers[v].append(object)

		fp = open(cache_file, 'w')
		fp.write(cache_version_notice)
		p = cPickle.Pickler(fp)
		p.dump(self._handlers)
		p.dump(self._files)
		p.dump(self._subfiles)
		p.dump(self._multifiles)
		fp.close()

	def register(self, package, bc):

		objects = []
		file = os.path.join(info_dir, package+'.info')
		for s in parseRfc822(open(file).read()):
			object = self.getHandler(s)
			if object and not object in objects:
				objects.append(object)

		for object in objects:
			d = {}
			for v in object.variables:
				d[v] = bc[v]
			object((bc, d))

	def unregister(self, package, bc):

		file = os.path.join(info_dir, package+'.info')
		for s in parseRfc822(open(file).read()):
			object = self.getHandler(s)
			if s.has_key('File'):
				for f in s['File']:
					if f[0] != '/':
						f = '/'+f
					if os.path.exists(f):
						os.unlink(f)

	def __call__(self, variables, arg):
		handlers = []

		for v in variables:
			for k in self._handlers.keys():
				_re=re.compile(k)
				if _re.match(v):
					for h in self._handlers[k]:
						if not h in handlers:
							handlers.append(h)
		for h in handlers:
			h(arg)

	def commit(self, bc, filelist=[]):

		_filelist = []
		if filelist:
			cwd = os.getcwd()
			for _f in filelist:
				_f = os.path.normpath(os.path.expandvars(os.path.expanduser(os.path.normpath(_f))))
				if _f.startswith('/'):
					_filelist.append(_f)
				else:
					_filelist.append(os.path.normpath(os.path.join(cwd, _f)))
		objects = []
		for file in directoryFiles(info_dir):
			for s in parseRfc822(open(file).read()):
				if not s.has_key('Type'):
					continue
				object = None
				if _filelist:
					if s.has_key('File'):
						object = None
						for f in s['File']:
							if f[0] != '/':
								f = '/'+f
							if f in _filelist:
								object = self.getHandler(s)
								break
						if not object:
							continue
					elif s.has_key('Multifile'):
						object = None
						for f in s['Multifile']:
							if f[0] != '/':
								f = '/'+f
							if f in _filelist:
								object = self.getHandler(s)
								break
						if not object:
							continue
				else:
					object = self.getHandler(s)
				if object and not object in objects:
					objects.append(object)
		for object in objects:
			d = {}
			for v in object.variables:
                                if v in self._handlers.keys():
					if ".*" in v:
						for i in range(0,4):
							val=v.replace(".*","%s"%i)
							regex = re.compile('(%s)'%v)
							match = regex.search("%s"%self._handlers.keys())
							d[val] = bc[val]
							i+=1
					else:
						d[v] = bc[v]
			object((bc, d))


def randpw():
	valid = [ 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
		'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v',
		'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
		'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
		'U', 'V', 'W', 'X', 'Y', 'Z', '0', '1', '2', '3', '4', '5',
		'6', '7', '8', '9' ]
	pw = ''
	fp = open('/dev/urandom')
	for i in range(0,8):
		o = fp.read(1)
		pw += valid[(ord(o) % len(valid))]
	fp.close()
	return pw

def handler_set( args, opts = {}, quiet = False ):
	c = configHandlers()
	c.load()

	reg = None
	if opts.get( 'ldap-policy', False ):
		reg = ConfigRegistry( write_registry = ConfigRegistry.LDAP )
	elif opts.get( 'force', False ):
		reg = ConfigRegistry( write_registry = ConfigRegistry.FORCED )
	elif opts.get( 'schedule', False ):
		reg = ConfigRegistry( write_registry = ConfigRegistry.SCHEDULE )
	else:
		reg = ConfigRegistry()

	reg.lock()
	try:
		reg.load()

		changed = {}
		for arg in args:
			sep_set = arg.find('=') # set
			sep_def = arg.find('?') # set if not already set
			if sep_set == -1 and sep_def == -1:
				continue
			else:
				if sep_set > 0 and sep_def == -1:
					sep = sep_set
				elif sep_def > 0 and sep_set == -1:
					sep = sep_def
				else:
					sep = min(sep_set, sep_def)
			key = arg[0:sep]
			value = arg[sep+1:]
			old = reg[key]
			if (reg[key] == None or sep == sep_set) and validateKey(key):
				if not quiet:
					if reg.has_key( key, write_registry_only = True ):
						print 'Setting '+key
					else:
						print 'Create '+key
				reg[key] = value
				changed[key] = (old, value)
			else:
				if not quiet:
					if old != None:
						print 'Not updating '+key
					else:
						print 'Not setting '+key

		reg.save()
	finally:
		reg.unlock()

	c( changed.keys(), ( reg, changed ) )

def handler_unset( args, opts = {} ):
	reg = None
	if opts.get( 'ldap-policy', False ):
		reg = ConfigRegistry( write_registry = ConfigRegistry.LDAP )
	elif opts.get( 'force', False ):
		reg = ConfigRegistry( write_registry = ConfigRegistry.FORCED )
	elif opts.get( 'schedule', False ):
		reg = ConfigRegistry( write_registry = ConfigRegistry.SCHEDULE )
	else:
		reg = ConfigRegistry()
	reg.lock()
	try:
		reg.load()

		c = configHandlers()
		c.load()

		changed = {}
		for arg in args:
			if reg.has_key( arg, write_registry_only = True ):
				oldvalue = reg[arg]
				print 'Unsetting '+arg
				del reg[arg]
				changed[arg] = ( oldvalue, '' )
			else:
				print "Warning: The config registry variable '%s' does not exist" % arg
		reg.save()
	finally:
		reg.unlock()
	c( changed.keys(), ( reg, changed ) )

def handler_dump( args, opts = {} ):
	b = ConfigRegistry()
	b.load()
	for line in str ( b ).split ( '\n' ):
		print line

def handler_update( args, opts = {} ):
	c = configHandlers()
	c.update()

def handler_commit( args, opts = {} ):
	b = ConfigRegistry()
	b.load()

	c = configHandlers()
	c.load()
	c.commit(b, args)

def handler_register( args, opts = {} ):
	b = ConfigRegistry()
	b.load()

	c = configHandlers()
	c.update()
	c.load()
	c.register(args[0], b)
	#c.commit((b, {}))

def handler_unregister( args, opts = {} ):
	b = ConfigRegistry()
	b.load()

	c = configHandlers()
	c.update()
	c.load()
	c.unregister(args[0], b)

def handler_randpw( args, opts = {} ):
	print randpw()

def replaceDict(line, dict):
	result = line
	for key in dict:
		result = result.replace(key, dict[key])
	return result

def replaceUmlaut(line):
	umlauts = { 'Ä': 'Ae',
		    'ä': 'ae',
		    'Ö': 'Oe',
		    'ö': 'oe',
		    'Ü': 'Ue',
		    'ü': 'ue',
		    'ß': 'ss', }
	return replaceDict(line, umlauts)

def keyShellEscape(line):
	if not line:
		raise Exception ('got empty line')
	new_line = []
	if line[0] in string.digits:
		new_line.append ('_')
	for letter in line:
		if letter in shell_valid_key_chars:
			new_line.append (letter)
		else:
			new_line.append ('_')
	return ''.join (new_line)

def valueShellEscape(line):
	escapes = { '*':'"*"',
		    '?':'"?"',
		    #'"': '"""',
		    '"': '\\\"', }
	return replaceDict(line, escapes)

def validateKey(k):
	old = k
	k = replaceUmlaut(k)

	if old != k:
		sys.stderr.write('Please fix invalid umlaut in config variables key "%s" to %s \n' % (old, k))
		return 0

	if len(k) > 0:
		match = invalid_key_chars.search(k);

		if not match:
			return 1
		else:
			sys.stderr.write('Please fix invalid char "%s" in config registry key "%s"\n'% (match.group(), k));
	return 0

def handler_filter( args, opts = {} ):
	b = ConfigRegistry()
	b.load()
	sys.stdout.write(filter(sys.stdin.read(), b, opts = opts))

def handler_search( args, opts = {} ):
	category = opts.get ( 'category', None )
	non_empty = opts.get ( 'non-empty', False )
	brief = opts.get ( 'brief', False )
	search_keys = opts.get ( 'key', False )
	search_values = opts.get ( 'value', False )
	search_all = opts.get ( 'all', False )
	if (search_keys and search_values) or (search_values and search_all) or (search_keys and search_all):
		sys.stderr.write( 'E: at most one out of [--key|--value|--all] may be set\n' )
		sys.exit( 1 )
	if not search_keys and not search_values and not search_all:
		search_keys = True

	regex = []
	if not args:
		regex = [ re.compile ('') ]
	else:
		for arg in args:
			try:
				regex.append ( re.compile ( arg ) )
			except re.error:
				sys.stderr.write ( 'E: invalid regular expression: %s\n' % arg )
				sys.exit ( 1 )

	#Import located here, because on module level, a circular import would be created
	import config_registry_info as cri
	cri.set_language ( 'en' )
	info = cri.ConfigRegistryInfo ( install_mode = False )

	if category and not info.get_category ( category ):
		sys.stderr.write ( 'E: unknown category: "%s"\n' % category )
		sys.exit ( 1 )

	b = ConfigRegistry()
	b.load()

	if not brief and b.get ('ucr/output/brief', 'no') in ['yes','true','1']:
		brief = True

	all_vars = {}
	for key, var in info.get_variables (category).items ():
		all_vars [ key ] = ( None, var )
	for key, value in b.items():
		var_tuple = all_vars.get ( key )
		if var_tuple:
			all_vars [ key ] = ( value, var_tuple[1] )
		elif not category:
			all_vars [ key ] = ( value, None )

	for key, var_tuple in all_vars.items():
		for reg in regex:
			if \
				( search_keys and reg.search ( key ) ) or \
				( search_values and var_tuple[0] and reg.search ( var_tuple[0] ) ) or \
				( search_all and ( \
				  ( reg.search ( key ) ) or \
				  ( var_tuple[0] and reg.search ( var_tuple[0] ) ) or \
				  ( var_tuple[1] and reg.search ( var_tuple[1].get ( 'description', '' ) ) ) ) \
				):
				print_variable_info_string ( key, var_tuple[0], var_tuple[1], brief, non_empty )
				break

def handler_get( args, opts = {} ):
	b = ConfigRegistry()
	b.load()

	print b.get( args[ 0 ], '' )

class UnknownKeyException ( Exception ):
	def __init__ (self, value):
		self.value = value
	def __str__ (self):
		return repr (self.value)

def print_variable_info_string( key, value, variable_info, brief=False, non_empty=False ):
	value_string = None
	if value == None and not variable_info:
		raise UnknownKeyException ( 'W: unknown key: "%s"' % key )
	elif value == None and non_empty:
		return
	elif value == None:
		value_string = '<empty>'
	else:
		value_string = '%s' % value

	key_value = '%s: %s' % (key, value_string)

	info_string = None
	if brief or not variable_info:
		info_string = key_value
	else:
		info = [ key_value ]
#		info.append ( ' ' + variable_info.get ( 'description', 'no description available' ) )
# https://forge.univention.org/bugzilla/show_bug.cgi?id=15556
# Workaround:
		description = variable_info.get ( 'description' )
		if not description or not description.strip ():
			description = 'no description available'
		info.append ( ' ' + description )

		info.append ( ' Categories: ' + variable_info.get ( 'categories', 'none' ) )
		info_string = '\n'.join (info)

	if brief:
		print info_string
	else:
		print info_string + '\n'

def handler_info( args, opts = {} ):
	reg = ConfigRegistry ()
	reg.load ()
	#Import located here, because on module level, a circular import would be created
	import config_registry_info as cri
	cri.set_language ( 'en' )
	info = cri.ConfigRegistryInfo ( install_mode = False )

	for arg in args:
		try:
			print_variable_info_string (arg, reg.get (arg, None), info.get_variable (arg))
		except UnknownKeyException, e:
			sys.stderr.write ( e.value + '\n' )

def handler_help( args, opts = {} ):
	print '''
univention-config-registry: base configuration for UCS
copyright (c) 2001-@%@copyright_lastyear@%@ Univention GmbH, Germany

Syntax:
  univention-config-registry [options] <action> [options] [parameters]

Options:

  -h | --help | -?:
	print this usage message and exit program

  --version | -v:
	print version information and exit program

  --shell (valid actions: dump, search):
	convert key/value pair into shell compatible format, e.g.
	`version/version: 1.0` => `version_version="1.0"`

  --keys-only (valid actions: dump, search):
	print only the keys

Actions:
  set [--force|--schedule|--ldap-policy] <key>=<value> [... <key>=<value>]:
	set one or more keys to specified values; if a key is non-existent
	in the configuration registry it will be created

  get <key>:
	retrieve the value of the specified key from the configuration
	database

  unset [--force|--schedule|--ldap-policy] <key> [... <key>]:
	remove one or more keys (and its associated values) from
	configuration database

  dump:
	display all key/value pairs which are stored in the
	configuration database

  search [--key|--value|--all] [--category <category>] [--brief] [--non-empty] [... <regex>]:
	displays all key/value pairs and their descriptions that match at
	least one of the given regular expressions
	--key: only search the keys (default)
	--value: only search the values
	--all: search keys, values and descriptions
	--category: limit search to variables of <category>
	--brief: don\'t print descriptions (can be enabled by default via ucr/output/brief)
	--non-empty: only search in non-empty variables
	no <regex> given: display all variables

  info <key> [... <key>]:
	display verbose information for the specified variable(s)

  shell [key]:
	convert key/value pair into shell compatible format, e.g.
	`version/version: 1.0` => `version_version="1.0"`
	(deprecated: use --shell dump instead)

  commit [file1 ...]:
	rebuild configuration file from univention template; if
	no file is specified ALL configuration files are rebuilt

  filter [--encode-utf8] [file]:
	evaluate a template file, optionaly expect python
	inline code in UTF8 (default: US-ASCII)

Description:
  univention-config-registry is a tool to handle the basic configuration for UCS

Known-Bugs:
  -None-
'''
	sys.exit(0)

def handler_version( args, opts = {} ):
	print 'univention-config-registry @%@package_version@%@'
	sys.exit(0);

def missing_parameter(action):
	print 'error: too few arguments for command [%s]' % action
	print 'try `univention-config-registry --help` for more information'
	sys.exit(1);

def exception_occured():
	print 'error: your request could not be fulfilled'
	print 'try `univention-config-registry --help` for more information'
	sys.exit(1);

def filter_shell( args, text ):
	out = []
	for line in text:
		try:
			var, value = line.split( ': ', 1 )
		except ValueError:
			var = line
			value = ''
		out.append( '%s="%s"' % ( keyShellEscape( var ), valueShellEscape( value ) ) )
	return out

def filter_keys_only( args, text ):
	out = []
	for line in text:
		out.append( line.split( ': ', 1 )[ 0 ] )
	return out

def filter_sort( args, text ):
	text.sort()
	return text

class Output:
	def __init__(self):
		self.text=[]
	def write(self, line):
		if line and line.strip ():
			self.text.append (line)

	def writelines(self, lines):
		for l in lines:
			self.text.append(l)

def main(args):
	try:
		handlers = {
			'set': (handler_set, 1),
			'unset': (handler_unset, 1),
			'dump': (handler_dump, 0),
			'update': (handler_update, 0),
			'commit': (handler_commit, 0),
			'register': (handler_register, 1),
			'unregister': (handler_unregister, 1),
			'randpw': (handler_randpw, 0),
			'shell': (None, 0),	# for compatibility only
			'filter': (handler_filter, 0),
			'search': (handler_search, 0),
			'get': (handler_get, 1),
			'info': (handler_info, 1),
			}
		# action options: each of these options perform an action
		opt_actions = {
			# name : ( function, state, ( alias list ) )
			'help' : [ handler_help, False, ( '-h', '-?' ) ],
			'version' : [ handler_version, False, ( '-v', ) ],
			}
		# filter options: these options define filter for the output
		opt_filters = {
			# id : ( name, function, state, ( valid actions ) )
			0  : [ 'keys-only', filter_keys_only, False, ( 'dump', 'search' ) ],
			10 : [ 'sort', filter_sort, False, ( 'dump', 'search', 'info' ) ],
			99 : [ 'shell', filter_shell, False, ( 'dump', 'search', 'shell' ) ],
			}
		BOOL, STRING = range ( 2 )
		opt_commands = {
			'set' : { 'force' : (BOOL, False), 'ldap-policy' : (BOOL, False), 'schedule' : (BOOL, False) },
			'unset' : { 'force' : (BOOL, False), 'ldap-policy' : (BOOL, False), 'schedule' : (BOOL, False) },
			'search' : { 'key' : (BOOL, False), 'value' : (BOOL, False), 'all' : (BOOL, False), \
						 'brief' : (BOOL, False), 'category' : (STRING, None), 'non-empty' : (BOOL, False) },
			'filter' : { 'encode-utf8' : (BOOL, False) }
			}
		# close your eyes ...
		if not args: args.append( '--help' )
		# search for options in command line arguments
		for arg in copy.copy( args ):
			if not arg[ 0 ] == '-': break

			# is action option?
			for key, opt in opt_actions.items():
				if arg[ 2 : ] == key or arg in opt[ 2 ]:
					opt_actions[ key ][ 1 ] = True
					break
			else:
				# not an action option; is a filter option?
				for id, opt in opt_filters.items():
					if arg[ 2 : ] == opt[ 0 ]:
						opt[ 2 ] = True
						break
				else:
					print 'E: unknown option %s' % arg
					opt_actions[ 'help' ][ 1 ] = True
					break

			# remove option from command line arguments
			args.pop( 0 )

		# is action already defined by global option?
		for k in opt_actions:
			if opt_actions[ k ][ 1 ]:
				opt_actions[ k ][ 0 ](args)

		# find action
		action = args[ 0 ]
		args.pop( 0 )
		# COMPAT: the 'shell' command is now an option and equivalent to --shell search
		if action == 'shell':
			action = 'search'
			# activate shell option
			opt_filters[ 99 ][ 2 ] = True
			# switch to old, brief output
			opt_commands[ 'search' ][ 'brief' ] = (BOOL, True)
			# only include non-empty variables
			opt_commands[ 'search' ][ 'non-empty' ] = (BOOL, True)
			# modify arguments: each argument must be a complete key and not just part of it
			tmp = []
			if not args:
				tmp.append( '' )
			else:
				for arg in args:
					tmp.append( '^%s$' % arg )
			args = tmp

		# set 'sort' option by default for dump and search
		if action in [ 'dump', 'search', 'info' ]:
			opt_filters[ 10 ][ 2 ] = True

		# set brief option when generating shell output
		if opt_filters[ 99 ][ 2 ] == True:
			opt_commands[ 'search' ][ 'brief' ] = (BOOL, True)

		# if a filter option is set: verify that a valid command is given
		filter = False
		for id, opt in opt_filters.items():
			if opt[ 2 ]:
				if not action in opt[ 3 ]:
					print 'invalid option --%s for command %s' % ( opt[ 0 ], action )
					sys.exit( 1 )
				else:
					filter = True

		# check command options
		cmd_opts = opt_commands.get( action, {} )
		skip_next_arg = False
		for arg in copy.copy( args ):
			if skip_next_arg:
				skip_next_arg = False
				args.pop( 0 )
				continue
			if not arg.startswith( '--' ): break
			cmd_opt = arg[ 2: ]
			if cmd_opt in cmd_opts.keys():
				cmd_opt_tuple = cmd_opts[ cmd_opt ]
				if cmd_opt_tuple[0] == BOOL:
					cmd_opts[ cmd_opt ] = (BOOL, True)
				else: #STRING
					if len (args) < 2:
						sys.stderr.write ( 'E: Option %s for command %s expects an argument\n' % (arg, action) )
						sys.exit ( 1 )
					cmd_opts[ cmd_opt ] = (STRING, args[ 1 ])
					skip_next_arg = True
			else:
				opt_actions[ 'help' ][ 1 ] = True
				print 'invalid option %s for command %s' % ( arg, action )
				sys.exit( 1 )
			args.pop( 0 )

		for cmd_opt, opt_tuple in copy.copy ( cmd_opts ).items ():
			cmd_opts[ cmd_opt ] = opt_tuple[ 1 ]

		# action!
		if action in handlers.keys():
			# enough arguments?
			if len( args ) < handlers[ action ][ 1 ]:
				missing_parameter( action )
			# if any filter option is set
			if filter:
				old_stdout = sys.stdout
				sys.stdout = Output()
			handlers[ action ][ 0 ]( args, cmd_opts )
			# let the filter options do their job
			if filter:
				out = sys.stdout
				text = out.text
				sys.stdout = old_stdout
				for id, opt in opt_filters.items():
					if opt[ 2 ]:
						text = opt[ 1 ]( args, text )
				for line in text:
					print line
		else:
			print 'E: unknown action: %s' % action
			opt_actions[ 'help' ][ 0 ]( args )
			sys.exit( 1 )

	except IOError, TypeError:
		exception_occured();

if __name__ == '__main__':
	main(sys.argv[1:])
