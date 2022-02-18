#!/usr/bin/python

# Copyright: (c) 2022, Robert Kraemer robert.kraemer@musicological.de>
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native
import os
import re
import copy
from collections import OrderedDict


def _processing(anstring):
    alist = anstring.split("\n")
    return alist[1], alist[2], alist[3], alist[4:]


def _process_minimal_output(anstring):
    adate, afunction, aval, rest = _processing(anstring)
    retdict = dict([
        ("date", adate),
        ("function", afunction),
        ("sapstatus", aval)])
    if rest != [""]:
        retdict["additional"] = rest
    return retdict


def _process_lp_output(anstring):
    retlist = list()
    alist = anstring.split("\n")
    adate = alist[1]
    afunction = alist[2]
    aval = alist[3]
    headers = [i.strip() for i in alist[4].split(",")]
    for i in alist[5:]:
        _dict = dict()
        _list = i.split(",")
        if len(_list) == len(headers):
            for el in range(len(_list)):
                _dict[headers[el]] = _list[el]
            retlist.append(_dict)
    return dict([
        ("date", adate),
        ("function", afunction),
        ("sapstatus", aval),
        ("output", retlist)])



class ExtSapCommand:
    def __init__(self, sapfunctionname=str(), instancenumber=str(), addelements = list()):
        self.sapfunctionname = sapfunctionname
        self.instancenumber = instancenumber
        self.addelements = addelements
        self.command = list()
        
    def set_command(self):
        self.command = ["-nr", self.instancenumber, "-function", self.sapfunctionname] + self.addelements
    
    def __setattr__(self, name, value):
        if name == "sapfunctionname":
            self.__dict__["sapfunctionname"] = value
            if hasattr(self, "instancenumber") and hasattr(self, "addelements"):
                self.set_command()
        elif name == "instancenumber":
            self.__dict__["instancenumber"] = value
            if hasattr(self, "sapfunctionname") and hasattr(self, "addelements"):            
                self.set_command()
        elif name == "addelements":
            if not isinstance(value, list):
                raise TypeError()
            for i in value:
                if not isinstance(i, str):
                    raise TypeError()
            self.__dict__["addelements"] = value
            if hasattr(self, "sapfunctionname") and hasattr(self, "instancenumber"): 
                self.set_command()
        elif name == "command":
            self.__dict__["command"] = value
        else:
            raise AttributeError()


class UserInput:
    def __init__(self, module):
        self._sapfunctions = {"GetProcessList":(False,), "Start":(True,), "Stop":(True,)}
        self.module = module
        self.sapfunction = module.params["function"]
        
        if self.sapfunction not in self._sapfunctions.keys():
            raise IndexError
        
        self.changing = self._sapfunctions[self.sapfunction][0]

        self.instancenumber = str(module.params["instancenumber"])
        self.instancenumbers = [str(i) for i in module.params["instancenumbers"]]
        
        if self.instancenumbers is None:
            self.instancenumbers = [self.instancenumber]
        
        self.command = [module.get_bin_path('/usr/sap/hostctrl/exe/sapcontrol', required=True)]
        self._command = [module.get_bin_path('/usr/sap/hostctrl/exe/sapcontrol', required=True)]
        
        self.ext = ExtSapCommand()
        self.ext.sapfunctionname = self.sapfunction
        #Don't forget about addelements

    def update_instancenumber(self, instancenumber):
        self.ext.instancenumber = instancenumber

    def run_command(self):
        return self.module.run_command(self.command)
    
    def extend_command(self):
        self.command.extend(self.ext.command) 

    def get_result(self):
        return [{"instancenumber": self.instancenumber, "instancenumbers": self.instancenumbers, "self.iterate": self.iterate}]
    
    def reset_command(self):
        self.command = copy.deepcopy(self._command)


class Result:
    def __init__(self, userinput):
        self.userinput = userinput
        self.result = list()
        # If any of the instances fails, the whole task is being named as failed
        self.failed = bool()
        # If any of the instances changes the whole task is being named as changed
        self.changed = bool()
        self.failmsg = str()
        self.rc = int()
        self.failed_instances = list()
        self.suceeded_instances = list()
        self._process()

    
    
    def _process(self):            
        for i in self.userinput.instancenumbers:
            self.userinput.update_instancenumber(i)
            self.userinput.extend_command()
            _commandoutput = self.userinput.run_command()
            if _commandoutput[0] != 1:
                _retval = _process_lp_output(_commandoutput[1])
                _retval['rc'] = _commandoutput[0]
                self.result.append(_retval)
                self.suceeded_instances.append((i, _retval))
                self.changed = self.userinput.changing
            else:
                _retval = _process_minimal_output(_commandoutput[1])
                _retval['rc'] = _commandoutput[0]
                self.failed = True
                self.failmsg = _retval['sapstatus']
                self.failed_instances.append((i, self.failmsg, dict(changed=False)))
                self.result.append(_retval)
            self.userinput.reset_command()


def run_module():
    module_args = dict(
        instancenumber=dict(type='int', required=False),
        instancenumbers=dict(type='list', required=False),
        function=dict(type='str', required=True),
        timeout=dict(type='int', required=False),
        delay=dict(type='int', required=False),
        softtimeout=dict(type='int', required=False)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        required_if=[('function', 'StartWait', ['timeout', 'delay']),
                     ('function', 'StopWait', ['timeout', 'delay'])],
        required_one_of=[('instancenumber', 'instancenumbers')],
        supports_check_mode=True
    )

    a = UserInput(module)
    b = Result(a)
    theresult = b.result
    myresult = dict(
        changed=b.changed,
        sap=b.result 
    )
    if not b.failed:
        module.exit_json(**myresult)
    elif b.failed:
        myresult["failure"] = b.failed_instances
        myresult["success"] = b.suceeded_instances
        module.fail_json(msg=b.failmsg,**myresult)
    else:
        AttributeError()

    


def main():
    run_module()


if __name__ == '__main__':
    main()
