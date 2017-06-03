/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojox/html/entities",
	"umc/tools",
	"umc/widgets/Form",
	"umc/widgets/Text",
	"umc/widgets/TextBox",
	"umc/widgets/Uploader",
	"umc/widgets/PasswordBox",
	"umc/widgets/CheckBox",
	"umc/widgets/ComboBox",
	"umc/widgets/ContainerWidget",
	"umc/widgets/TitlePane",
	"umc/modules/appcenter/AppSettingsFileUploader",
	"umc/i18n!umc/modules/appcenter"
], function(declare, lang, array, entities, tools, Form, Text, TextBox, Uploader, PasswordBox, CheckBox, ComboBox, ContainerWidget, TitlePane, AppSettingsFileUploader, _) {
	return {
		getWidgets: function(app, values, phase) {
			var ret = [];
			var staticValues;
			array.forEach(app.settings, function(variable) {
				if ((variable.write || []).indexOf(phase) === -1 && (variable.read || []).indexOf(phase) === -1) {
					return;
				}
				var value = values[variable.name] || null;
				var params = {
					name: variable.name,
					_groupName: variable.group || _('Settings'),
					required: variable.required,
					label: variable.description,
					disabled: (variable.read || []).indexOf(phase) !== -1,
					value: value
				};
				if (variable.type == 'String') {
					ret.push(lang.mixin(params, {
						type: TextBox
					}));
				} else if (variable.type == 'Bool') {
					ret.push(lang.mixin(params, {
						type: CheckBox,
						value: tools.isTrue(params.value)
					}));
				} else if (variable.type == 'List') {
					staticValues = array.map(variable.values, function(val, i) {
						var label = variable.labels[i] || val;
						return {
							id: val,
							label: label
						};
					});
					ret.push(lang.mixin(params, {
						type: ComboBox,
						staticValues: staticValues
					}));
				} else if (variable.type == 'UDMList') {
					staticValues = array.map(variable.values, function(val, i) {
						var label = variable.labels[i] || val;
						return {
							id: val,
							label: label
						};
					});
					ret.push(lang.mixin(params, {
						type: ComboBox,
						staticValues: staticValues
					}));
				} else if (variable.type == 'Password') {
					ret.push(lang.mixin(params, {
						type: PasswordBox
					}));
				} else if (variable.type == 'File') {
					if (params.value) {
						params.value = btoa(params.value);
						params.data = {content: params.value};
					}
					ret.push(lang.mixin(params, {
						type: AppSettingsFileUploader,
					}));
				} else if (variable.type == 'PasswordFile') {
					ret.push(lang.mixin(params, {
						type: PasswordBox
					}));
				} else if (variable.type == 'Status') {
					if (value) {
						ret.push(lang.mixin(params, {
							type: Text,
							content: value,
							_groupName: params._groupName
						}));
					}
				}
			});
			return ret;
		},

		getForm: function(app, values, phase) {
			var widgets = this.getWidgets(app, values, phase);
			if (widgets.length === 0) {
				return;
			}
			var groups = this.getGroups(app, widgets);
			var layout = [];
			array.forEach(groups, function(group, i) {
				var groupName = '_group' + i;
				widgets.push({
					type: Text,
					name: groupName,
					content: '<h2>' + group.label + '</h2>'
				});
				layout.push(groupName);
				layout = layout.concat(array.map(group.widgets, function(w) { return w.name; }));
			});
			return new Form({
				widgets: widgets,
				layout: layout
			});
		},

		getGroups: function(app, widgets) {
			var groups = [];
			array.forEach(app.settings, function(setting) {
				var groupName = setting.group || _('Settings');
				if (groups.indexOf(groupName) === -1) {
					groups.push(groupName);
				}
			});
			groups = array.map(groups, function(group) {
				var _widgets = array.filter(widgets, function(widget) {
					return group === widget._groupName;
				});
				var groupDef = {label: group, widgets: _widgets};
				return groupDef;
			});
			return groups;
		}
	};
});
