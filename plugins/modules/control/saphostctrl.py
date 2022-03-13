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


def _list_sanitize_helper(anstring, delim="\n"):
    _alist = anstring.split(delim)
    return [i.strip() for i in _alist]

def _process_sap_generic_csv(anstring):
    alist = _list_sanitize_helper(anstring)
    f_name = alist[2]
    header_list = _list_sanitize_helper(alist[4], ",")
    retlist = []
    if len(alist)-1 > 4: 
        for i in alist[5:]:
            tmplist = _list_sanitize_helper(i, ",")
            # drop line if it doesnt match exactly count of headers
            if len(tmplist)==len(header_list):
                retlist.append(dict(zip(header_list, tmplist)))
            # if there are more values then headers create additional header "OVERHEAD"
            # this is the case for J2EEGetProcessList
            elif len(tmplist)>len(header_list):
                overhead_count = len(tmplist)-len(header_list)
                overhead_list = ["OVERHEAD"+str(i) for i in range(1,overhead_count+1)]
                retlist.append(dict(zip(header_list+overhead_list,tmplist)))
            # and replace it with null values to account for "\n" 
            else: 
                if len(alist[5:]) == 1:
                    retlist.append(dict(zip(header_list,[None]*len(header_list))))
                
    else:
        retlist.append(dict(zip(header_list,[None]*len(header_list))))
    if len(retlist)==0: raise IndexError(alist)
    return dict([
        ("date", alist[1]),
        ("function", alist[2]),
        ("sapstatus", alist[3]),
        ("output", retlist)])



class ExtSapCommand:
    ''' Class to hold arguments for saphostctrl and to "build" saphostctrl command
    '''
    def __init__(self, sapfunctionname=str(), instancenumber=str(), addelements = list()):
        self.sapfunctionname = sapfunctionname
        self.instancenumber = instancenumber
        # addelements for future use cases
        self.addelements = addelements
        self.command = list()
        
    def set_command(self):
        self.command = ["-nr",self.instancenumber, "-function", self.sapfunctionname] + self.addelements


class UserInput:
    ''' Class to abstract and parse UserInput
    '''
    def __init__(self, module):
        #self._sapfunctions lists functions with no system-changes
        self._sapfunctions = ["GetProcessList"]
        #ICMGetThreadList is malformed CSV
        self._otherfunctions = ["GetInstanceProperties","ICMGetThreadList"]
        #Following functions return csv output and can be parsed accordingly
        self._csvsapfunctions = ["GetProcessList","GetAlertTree","GetAlerts",
        "ListDeveloperTraces","ListLogFiles","ListSnapshots",
        "GetAccessPointList","GetSystemInstanceList","HACheckConfig", "ABAPReadSyslog",
        "ABAPReadRawSyslog","ABAPGetSystemWPTable","J2EEGetProcessList","J2EEGetProcessList2",
        "J2EEGetThreadList", "J2EEGetThreadList2","J2EEGetSessionList","J2EEGetCacheStatistic",
        "J2EEGetApplicationAliasList", "J2EEGetComponentList", "J2EEGetWebSessionList", "J2EEGetWebSessionList2",
        "J2EEGetEJBSessionList","J2EEGetRemoteObjectList","J2EEGetVMGCHistory","J2EEGetVMGCHistory2","J2EEGetVMHeapInfo",
        "J2EEGetSharedTableInfo","J2EEGetSharedTableInfo", "ICMGetConnectionList",
        "ICMGetProxyConnectionList","ICMGetCacheEntries", "EnqGetLockTable"]
        # self.module references AnsibleModule-Class from run_module-funciton
        self.module = module
        # self.sapfunction references saphostctrl function to be called
        self.sapfunction = module.params["function"]
               
        if self.sapfunction in self._csvsapfunctions: 
            self._csv = True
        else: self._csv = False
        #if self.sapfunction not in self._sapfunctions:
        # for now: the csvsapfunctions do not change the systemstatus
        if self.sapfunction not in self._csvsapfunctions:
            self.changing = True
        else:
            self.changing = False 

        self.instancenumber = str(module.params["instancenumber"])
        
        self.command = [module.get_bin_path('/usr/sap/hostctrl/exe/sapcontrol', required=True)]
        
        self.ext = ExtSapCommand(sapfunctionname=self.sapfunction, instancenumber=self.instancenumber)
        self.ext.set_command()

    def run_command(self):
        return self.module.run_command(self.command+self.ext.command)
  
  
class Result:
    ''' Class to structure results from saphostctrl execution 
    '''
    def __init__(self, userinput):
        self.userinput = userinput
        self.result = list()
        self.failed = bool()
        self.changed = bool()
        self.failmsg = str()
        self.rc = int()
        self._process()
   
    
    def _process(self):
        _commandoutput = self.userinput.run_command()
        if _commandoutput[0] != 1:
            if self.userinput._csv:
            #_retval = _process_lp_output(_commandoutput[1])
                _retval = _process_sap_generic_csv(_commandoutput[1])
                _retval['rc'] = _commandoutput[0]
                self.result.append(_retval)
                self.changed = self.userinput.changing
            else:
                raise IndexError(self.userinput.sapfunction)
        else:
            _retval = _process_minimal_output(_commandoutput[1])
            _retval['rc'] = _commandoutput[0]
            self.failed = True
            self.failmsg = self.userinput.instancenumber #_retval['sapstatus']
            self.result.append(_retval)


def run_module():
    module_args = dict(
        instancenumber=dict(type='int', required=True),
        function=dict(type='str', required=True),
        timeout=dict(type='int', required=False),
        delay=dict(type='int', required=False),
        softtimeout=dict(type='int', required=False),
        checkstate=dict(type='bool', default=False)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        required_if=[('function', 'StartWait', ['timeout', 'delay']),
                     ('function', 'StopWait', ['timeout', 'delay'])],
        supports_check_mode=True
    )

    a = UserInput(module)
    b = Result(a)
    theresult = b.result
    myresult = dict(
        changed = b.changed,
        sap = b.result 
    )
    if not b.failed:
        module.exit_json(**myresult)
    elif b.failed:
        myresult["failure"] = b.result
        module.fail_json(msg=b.failmsg,**myresult)
    else:
        AttributeError()


def main():
    run_module()


if __name__ == '__main__':
    main()
