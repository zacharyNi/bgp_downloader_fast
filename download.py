import os
import queue
from URLGetter import BGPDownloader
from DownloadThread import DownloadThread
from parser_thread import parse
import argparse

def download(urls, destfolder, numthreads=30):
    downloaded_data=[]
    try:
        os.stat(destfolder)
    except:
        os.mkdir(destfolder)
    else:
        downloaded_data=os.listdir(destfolder)
    q = queue.Queue()
    for url in urls:
        us=url.split("/")
        name=str(us[4])+str("_")+str(us[-1])
        if name in downloaded_data:
            continue
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
    print(collector+"||"+datatype+"||"+start_time+"->"+end_time)
    urls=bgp.getUrl()
    folder_name="Data/"+str(start_time+"->"+end_time+"||"+collector+"("+datatype+")")  
    download(urls,folder_name,len(urls))
    parse(folder_name)
  
    
#route-views.eqix ribs 2021-07-12-06:00 2021-06-19-10:00
#python3 download.py -c route-views.eqix,rrc15 -d updates -s 2015-04-01-14:00 -e 2015-04-01-14:20
#all ribs 2021-07-12-01:00 2021-07-12-12:00
#python3 download.py -c rrc00 -d ribs -s 2021-01-01-06:00 -e 2021-01-01-20:00

#W withdrawl
#A announce
#STATE state message
#B RIB