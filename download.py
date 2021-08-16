import os
import queue
from URLGetter import BGPDownloader
from DownloadThread import DownloadThread
from parser_thread import parse
import argparse

def download(urls, destfolder, numthreads=30):
    try:
        os.stat(destfolder)
    except:
        os.mkdir(destfolder)
        os.mkdir(destfolder+"/result")
    q = queue.Queue()
    for url in urls:
        q.put(url)
    for i in range(numthreads):
        t = DownloadThread(q, destfolder)
        t.start()
    q.join()

def parse_args():
    p = argparse.ArgumentParser(
        description='This script download bgp data.')
    p.add_argument(
        '-c', dest='collector', required=True, type=str,
        help='选择需要的收集器')
    p.add_argument(
        '-d', dest='datatype', required=True, type=str,
        help='选择数据类型:updates或ribs')
    p.add_argument(
        '-s', dest='start_time', required=True, type=str,
        help='数据的开始时间:xxxx-xx-xx-xx:xx')
    p.add_argument(
        '-e', dest='end_time', required=True, type=str,
        help='数据的结束时间:xxxx-xx-xx-xx:xx')
    return p.parse_args()

if __name__=='__main__':
    args = parse_args()
    collector=args.collector
    datatype=args.datatype
    start_time=args.start_time
    end_time=args.end_time
    bgp=BGPDownloader()
    bgp.set_collector(collector)
    bgp.set_datatype(datatype)
    bgp.set_time(start_time,end_time)
    urls=bgp.getUrl()
    folder_name=str(start_time+"->"+end_time+"||"+collector+"("+datatype+")")  
    download(urls,folder_name)
    parse(folder_name)
  
    
#route-views.eqix ribs 2021-07-12-06:00 2021-06-19-10:00
#route-views.eqix,rrc15 updates 2015-04-01-14:00 2015-04-01-14:20
#all ribs 2021-07-12-01:00 2021-07-12-12:00
# rrc03 ribs 2021-07-12-12:00 2021-07-12-18:00

#W withdrawl
#A announce
#STATE state message
#B RIB
#TODO
#1.Command parser