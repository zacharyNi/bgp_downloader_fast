import os
from mrtparse import Reader,MRT_T
from dump_form import BgpDump
import time
from multiprocessing import Process

def parse_handle(folder_name,name):
    path_to_file = str(folder_name) + "/" + str(name)
    path_to_write= str(folder_name) + "/" + str("result/") + str(name) + str(".txt")
    r = Reader(path_to_file)   
    count = 0
    start_time=time.time()
    b = BgpDump(path_to_write)
    for m in r:
        if m.err:
            continue
        if m.data['type'][0] == MRT_T['TABLE_DUMP']:
            b.td(m.data, count)
        elif m.data['type'][0] == MRT_T['TABLE_DUMP_V2']:
            b.td_v2(m.data)
        elif m.data['type'][0] == MRT_T['BGP4MP']:
            b.bgp4mp(m.data, count)
        b.clear()
        count += 1
    b.close()
    end_time=time.time()
    print(end_time-start_time)
    pass

def parse(folder_name):
    p_list = []
    parsed_data=[]
    try:
        os.stat(folder_name+"/result")
    except:
        os.mkdir(folder_name+"/result")
    else:
        parsed_data=os.listdir(folder_name+"/result")
    dirlist=os.listdir(folder_name)
    i = 0
    dirlen=len(dirlist)
    for name in dirlist:
        if name=="result":
            continue
        elif name+".txt" in parsed_data:
            dirlen-=1
            continue
        p = Process(target=parse_handle, args=(folder_name,name, ))
        p_list.append(p)
        p.start()
        print("finish %d / %d"%(i+1,len(dirlist)-1))
        i += 1
    for p in p_list:
        p.join()
