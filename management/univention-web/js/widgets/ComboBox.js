/*
 * Copyright 2011-2019 Univention GmbH
 *
 * http://www.univention.de/
 *
 * All rights reserved.
 *
 * The source code of this program is made available
 * under the terms of the GNU Affero General Public License version 3
 * (GNU AGPL V3) as published by the Free Software Foundation.
 *
 * Binary versions of this program provided by Univention to you as
 * well as other copyrighted, protected or trademarked materials like
 * Logos, graphics, fonts, specific documentations and configurations,
 * cryptographic keys etc. are subject to a license agreement between
 * you and Univention and not subject to the GNU AGPL V3.
 *
 * In the case you use this program under the terms of the GNU AGPL V3,
 * the program is provided in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License with the Debian GNU/Linux or Univention distribution in file
 * /usr/share/common-licenses/AGPL-3; if not, see
 * <http://www.gnu.org/licenses/>.
 */
/*global define */

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/aspect",
	"dojo/on",
	"dojo/when",
	"dojo/Deferred",
	"dijit/form/FilteringSelect",
	"umc/widgets/_SelectMixin",
	"umc/widgets/_FormWidgetMixin"
], function(declare, lang, aspect, on, when, Deferred, FilteringSelect, _SelectMixin, _FormWidgetMixin) {
	return declare("umc.widgets.ComboBox", [ FilteringSelect , _SelectMixin, _FormWidgetMixin ], {
		// search for the substring when typing
		queryExpr: '*${0}*',

		// no auto completion, otherwise this gets weired in combination with the '*${0}*' search
		autoComplete: false,

		// autoHide: Boolean
		//		If true, the ComboBox will only be visible if there it lists more than
		//		one element.
		autoHide: false,

		_firstClick: true,

		allowOtherValues: false,

		postMixInProperties: function() {
			this.inherited(arguments);

			if (this.autoHide) {
				// autoHide ist set, by default the widget will be hidden
				this.visible = false;
			}
		},

		_updateVisibility: function() {
			if (this.autoHide) {
				// show the widget in case there are more than 1 values
				var values = this.getAllItems();
				this.set('visible', values.length > 1);
			}
		},

		postCreate: function() {
			this.inherited(arguments);
			this.on('valuesLoaded', lang.hitch(this, '_updateVisibility'));
		},

		_isValidSubset: function() {
			return this.inherited(arguments) || this.allowOtherValues;
		},

		_callbackSetLabel: function(result, query, options, priorityChange) {
			if (this.allowOtherValues && query && !result.length) {
				this.store.newItem({
					id: query[this.searchAttr],
					label: query[this.searchAttr],
					$dontShowInResultList: true
				});
				this.store.save();
				this.store.get(query[this.searchAttr]).then(lang.hitch(this, function(item) {
					this.inherited('_callbackSetLabel', arguments, [[item], query, options, priorityChange]);
				}));
			} else {
				this.inherited(arguments);
			}
		},

		_openResultList: function(results, query, options) {
			results = results.filter(function(i) {
				return !i.$dontShowInResultList;
			});
			this.inherited(arguments, [results, query, options]);
		}
	});
});

