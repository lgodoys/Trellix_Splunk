import trellix_splunk_declare

from app_common import *

import os
import sys
import json

import splunktaucclib.modinput_wrapper.base_modinput as modinput_wrapper
from splunklib import modularinput as smi

import input_module_trellix_events as input_module

bin_dir = os.path.basename(__file__)


class ModInputtrellix_events(modinput_wrapper.BaseModInput):

    def __init__(self):
        if 'use_single_instance_mode' in dir(input_module):
            use_single_instance = input_module.use_single_instance_mode()
        else:
            use_single_instance = False
        super(ModInputtrellix_events, self).__init__(
            "trellix_splunk", "trellix_events", use_single_instance)
        self.global_checkbox_fields = None
        set_helper(self)

    def get_scheme(self):
        scheme = super(ModInputtrellix_events, self).get_scheme()
        scheme.title = ("Trellix Events")
        scheme.description = "Get threats/incidents from Trellix MVision EPO API."
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        scheme.add_argument(smi.Argument("global_account", title="Global Account",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "Trellix_Splunk"

    def validate_input(self, definition):
        """validate the input stanza"""
        input_module.validate_input(self, definition)

    def collect_events(self, ew):
        """write out the events"""
        input_module.collect_events(self, ew)

    def get_account_fields(self):
        account_fields = []
        account_fields.append("global_account")
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        return checkbox_fields

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(
                bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error(
                    'Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields


if __name__ == "__main__":
    exitcode = ModInputtrellix_events().run(sys.argv)
    sys.exit(exitcode)
