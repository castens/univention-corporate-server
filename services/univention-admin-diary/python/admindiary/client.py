#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Copyright 2019 Univention GmbH
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

import logging
from logging.handlers import SysLogHandler
from univention.admindiary import DiaryEntry, get_logger
import uuid
from getpass import getuser
from functools import partial, wraps

get_logger = partial(get_logger, 'client')


def safe(f):
	@wraps(f)
	def wrapper(*args, **kwds):
		try:
			return f(*args, **kwds)
		except Exception as exc:
			get_logger().error('%s failed! %s' % (f.__name__, exc))
			return None
	return wrapper


class RsyslogEmitter(object):
	def __init__(self):
		self.logger = logging.getLogger('diary-rsyslogger')
		self.logger.setLevel(logging.DEBUG)
		handler = SysLogHandler(address='/dev/log', facility='user')
		self.logger.addHandler(handler)

	def emit(self, entry):
		self.logger.info('ADMINDIARY: ' + str(entry))

emitter = RsyslogEmitter()

@safe
def write_event(event, args=None, username=None, diary_id=None):
	args = args or []
	if not isinstance(args, (list, tuple)):
		raise TypeError('"args" must be a list')
	if len(args) != len(event.args):
		raise ValueError('Writing "%s" needs %d argument(s) (%s). %d given' % (event.message, len(event.args), ', '.join(event.args), len(args)))
	return write(event.message, args, None, event.tags, diary_id, event.name)


@safe
def write(message, args=None, username=None, tags=None, diary_id=None, event_name=None):
	if username is None:
		username = getuser()
	if args is None:
		args = []
	if tags is None:
		tags = []
	if diary_id is None:
		diary_id = str(uuid.uuid4())
	if event_name is None:
		event_name = 'CUSTOM'
	entry = DiaryEntry(username, message, args, tags, diary_id, event_name)
	return write_entry(entry)


@safe
def write_entry(entry):
	body = entry.to_json()
	emitter.emit(body)
	get_logger().info('Successfully wrote %s. (%s)' % (entry.diary_id, entry.event_name))
	return entry.diary_id
