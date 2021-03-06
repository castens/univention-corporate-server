#!/usr/bin/make -f
#
# UCS Virtual Machine Manager
#  makefile
#
# Copyright 2010-2019 Univention GmbH
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

UVMM := univention-virtual-machine-manager

PO_FILES := $(shell find src -name '*.po')
MO_FILES := $(foreach po,$(PO_FILES),src/i18n/$(notdir $(po:.po=))/LC_MESSAGES/$(UVMM).mo)

.PHONY: all
all:: $(MO_FILES)

define build_mo
src/i18n/$(1)/LC_MESSAGES/$(UVMM).mo: src/$(1).po
	mkdir -p $$(dir $$@)
	msgfmt --check --output-file $$@ $$<
endef

$(foreach po,$(PO_FILES),$(eval $(call build_mo,$(notdir $(po:.po=)))))

.PHONY: clean
clean::
	find -name \*.pyc -exec $(RM) {} +
	$(RM) src/virtual-machine-manager-daemon.log
	$(RM) $(MO_FILES)
	$(RM) tags
	$(RM) src/messages.pot

ifeq ($(M),1)
LANGUAGES := de
VERSION := $(shell dpkg-parsechangelog | sed -ne 's/^Version: //p')

.PHONY: maintainer-locales
maintainer-locales: $(foreach d,$(DIRS),$(d)/messages.pot)
maintainer-locales: $(foreach d,$(DIRS),$(foreach l,$(LANGUAGES),$(d)/$(l).po))

define I18N_template
 %/$(1).po: %/messages.pot
	msgmerge --update --sort-output $$@ $$<
endef
$(foreach lang,$(LANGUAGES),$(eval $(call I18N_template,$(lang))))

src/messages.pot: src/univention-virtual-machine-manager
src/messages.pot: src/univention-virtual-machine-manager-daemon
src/messages.pot: $(shell find src/univention/uvmm -name \*.py)

%/messages.pot:
	xgettext --output=$(@) \
		--language=Python \
		--keyword=N_:1 \
		--sort-output \
		--package-name=$(UVMM) \
		--package-version=$(VERSION) \
		--msgid-bugs-address="packages@univention.de" \
		--copyright-holder="Univention GmbH" \
		$^

endif

tags: $(shell find src umc -name \*.py)
	ctags-exuberant -o $@ $^

.PHONY: check
check:
	if which jshint >/dev/null; then find umc/js -name \*.js -type f -exec jshint {} +; fi
