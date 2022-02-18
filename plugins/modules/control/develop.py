a="\n04.02.2022 14:02:52\nGetProcessList\nOK\nname, description, dispstatus, textstatus, starttime, elapsedtime, pid\nhdbdaemon, HDB Daemon, GREEN, Running, 2022 02 01 10:23:50, 75:39:02, 121439\nhdbcompileserver, HDB Compileserver, GREEN, Running, 2022 02 01 10:23:58, 75:38:54, 121649\nhdbdiserver, HDB Deployment Infrastructure Server-HDB, GREEN, Running, 2022 02 01 10:24:36, 75:38:16, 124048\nhdbdocstore, HDB DocStore-HDB, GREEN, Running, 2022 02 01 10:23:59, 75:38:53, 121733\nhdbdpserver, HDB DPserver-HDB, GREEN, Running, 2022 02 01 10:23:59, 75:38:53, 121737\nhdbindexserver, HDB Indexserver-HDB, GREEN, Running, 2022 02 01 10:23:59, 75:38:53, 121740\nhdbnameserver, HDB Nameserver, GREEN, Running, 2022 02 01 10:23:51, 75:39:01, 121458\nhdbpreprocessor, HDB Preprocessor, GREEN, Running, 2022 02 01 10:23:58, 75:38:54, 121652\nhdbwebdispatcher, HDB Web Dispatcher, GREEN, Running, 2022 02 01 10:24:36, 75:38:16, 124051\nhdbxsengine, HDB XSEngine-HDB, GREEN, Running, 2022 02 01 10:23:59, 75:38:53, 121743\n"
from datetime import datetime


def _process_lp_output(anstring):
    retlist = list()
    alist = anstring.split("\n")
    #adate = datetime.strptime(alist[1], '%d.%m.%Y %H:%M:%S')
    adate = alist[1]
    afunction = alist[2]
    aval = alist[3]
    headers = [i.strip() for i in alist[4].split(",")]
    print(adate,afunction,aval,headers)
    tmpdict = dict()
    _counter = 0
    for i in alist[5:]:
        _dict = dict()
        _list = i.split(",")
        if len(_list)==len(headers):
            for el in range(len(_list)):
                _dict[headers[el]]= _list[el]
            retlist.append(_dict)

            




_process_lp_output(a)

