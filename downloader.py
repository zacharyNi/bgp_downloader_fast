import requests
import os
import sys
import threading
import queue
from bs4 import BeautifulSoup
import urllib.request
from urllib.parse import urlparse
import urllib.error
import re
import json
import datetime
import websocket
import configparser
from mrtparse import Reader,MRT_T
from dump_form import BgpDump

cp = configparser.ConfigParser()
cp.read('config/collector_list.ini')

routeViews="http://archive.routeviews.org/"
routeViews_Collectors=cp.get('collector_list','RouteViews')
routeViews_Collector_list=json.loads(routeViews_Collectors)

RIPE="http://data.ris.ripe.net/"
RIPE_collectors=cp.get('collector_list','RIPE')
RIPE_collector_list=json.loads(RIPE_collectors)

class DownloadThread(threading.Thread):
	def __init__(self, q, destfolder):
		super(DownloadThread, self).__init__()
		self.q = q
		self.destfolder = destfolder
		self.daemon = True
	def run(self):
		while True:
			url = self.q.get()
			try:
				self.download_url(url)
			except Exception as e:
				print("   Error: %s"%e)
			self.q.task_done()

	def download_url(self,url):
		vantage_folder=self.destfolder
		name=str(url.split('/')[4])+str("_")+str(url.split('/')[-1])
		destination="./"+vantage_folder+"/"+name
		print(destination)
		r=requests.get(url, allow_redirects=True)
		open(destination, 'wb').write(r.content)
		print(name)

#	def download_url(self, url):
#		# change it to a different way if you require
#		name = url.split('/')[-1]
#		dest = os.path.join(self.destfolder, name)
#		print "[%s] Downloading %s -> %s"%(self.ident, url, dest)
#		urllib.urlretrieve(url, dest)

def download(urls, destfolder, numthreads=30):
	q = queue.Queue()
	for url in urls:
		q.put(url)
	for i in range(numthreads):
		t = DownloadThread(q, destfolder)
		t.start()
	q.join()

class timeHandler:
    def __init__(self, time):
        self.time=time
        st=time.split("-")
        self.start_year=st[0]
        self.start_month=st[1]
        if self.start_month[0]=='0':
            self.start_month=self.start_month[1:]
        self.start_day=st[2]
        if self.start_day[0]=='0':
            self.start_day=self.start_day[1:]
        hnm=st[3]
        hnms=hnm.split(":")
        self.start_hour=hnms[0]
        if self.start_hour[0]=='0':
            self.start_hour=self.start_hour[1:]
        self.start_minutes=hnms[1]
        if self.start_minutes[0]=='0':
            self.start_minutes=self.start_minutes[1:]

    def yrandmonth(self):
        return datetime.datetime(int(self.start_year),int(self.start_month),1)

    def accurate_time(self):
        return datetime.datetime(int(self.start_year),int(self.start_month),int(self.start_day),int(self.start_hour),int(self.start_minutes))

def parseCommand(command):
    commands = command.split(" ")
    #4 necessary command: 
    #1.collector: routeview collector, ripe collector, all
    #2.type:update or rib
    #3.time:start and end
    #4.interval --days
    if len(commands)<4:
        print("Invaild Command!")
        sys.exit()
    collector = commands[0]
    datatype = commands[1]
    start_time = commands[2]
    end_time = commands[3]
    if len(commands) == 5:
        interval = commands[4]
    else:
        interval = 1
    
    #get final collectors
    if collector == "all":
        chosen_collectors=routeViews_Collector_list+RIPE_collector_list
    else:
        collectors = collector.split(",")
        chosen_collectors=[]
        for c in collectors:
            if c.lower() in routeViews_Collector_list or c.lower() in RIPE_collector_list:
                chosen_collectors.append(c.lower())
    
    #get type
    if datatype.upper() == "RIBS":
        datatype="RIBS"
    elif datatype.upper() == "UPDATES":
        datatype="UPDATES"
    return collector, chosen_collectors, datatype, start_time, end_time, interval

def findElement(base_url, pattern_str):
    #use beautifulsoup to get element in html
    sources=[]
    bs4_parser = "html.parser"
    try:
        response = urllib.request.urlopen(base_url)
        html = BeautifulSoup(response.read(), bs4_parser)
        for link in html.findAll('a',text=re.compile(pattern_str)):
            sources.append(link['href'])
        response.close()
    except urllib.error.HTTPError:
        print(base_url + " dont have such data!") 
    return sources

def live_mode():
    file_name = datetime.datetime.now().strftime('%Y-%m-%d-%H:%M:%S')
    with open("live_data/"+file_name,'w') as wf:    
        #get data
        ws = websocket.WebSocket()
        ws.connect("wss://ris-live.ripe.net/v1/ws/?client=py-manual")
        ws.send(json.dumps({"type": "ris_subscribe", "data": {"type":"UPDATE"}}))
        print("writing----press ctrl+C to stop writing")
        for data in ws:
            parsed = json.loads(data)
            wf.write(parsed["type"])
            data=str(parsed["data"])
            wf.write(data)
            wf.write("\n")

if __name__=='__main__':
    RibUrls=[] 

    line = input()
    if line.lower()=="live":
        live_mode()
    else:
        collector, chosen_collectors, datatype, start_time, end_time, interval = parseCommand(line)
        
        #get time handled by datetime in order to compare 
        start_time_handler = timeHandler(start_time)
        end_time_handler = timeHandler(end_time)

        start_time_yrandmonth = start_time_handler.yrandmonth()
        end_time_yrandmonth = end_time_handler.yrandmonth()

        start_time_accurate=start_time_handler.accurate_time()
        end_time_accurate=end_time_handler.accurate_time()

        #create folder if the folder doesnt exist
        folder_name=str(start_time+"->"+end_time+"||"+collector+"("+datatype+")")
        try:
            os.stat(folder_name)
        except:
            os.mkdir(folder_name)
            os.mkdir(folder_name+"/result")

        for cc in chosen_collectors:
            sources=[]
            if cc in routeViews_Collector_list:
                base_url = routeViews + cc + "/bgpdata"
            else:
                base_url = RIPE + cc + "/"
            
            sources = findElement(base_url, '^(((?:19|20)\d\d).(0?[1-9]|1[0-2]))')
            times=[]
            for s in sources:
                times.append(s.split("/")[0])

            selected_times=[]    

            for t in times:
                st=t.split(".")
                time_index_year=st[0]
                time_index_month=st[1]
                if time_index_month[0]=="0":
                    time_index_month=time_index_month[1:]
                time_index=datetime.datetime(int(time_index_year),int(time_index_month),1)
                if start_time_yrandmonth <= time_index and end_time_yrandmonth >= time_index:
                    selected_times.append(t)
            
            if len(selected_times)==0:
                print(cc+" dont have such data in your start_time and end_time")
                continue

            selected_packages=[]

            for st in selected_times:
                sources=[]
                if cc in routeViews_Collector_list:
                    base_url=routeViews + cc+ "/bgpdata/" + st + "/" + datatype + "/"
                else:
                    base_url = RIPE + cc + "/" + st + "/"

                if cc in routeViews_Collector_list:
                    if datatype=="UPDATES":
                        pattern_str='^updates'
                    elif datatype=="RIBS":
                        pattern_str='.bz2$'
                else:
                    if datatype=="UPDATES":
                        pattern_str='^updates'
                    elif datatype=="RIBS":
                        pattern_str='^bview'
                
                sources = findElement(base_url, pattern_str)

                for s in sources:
                    data=s.split(".")
                    yr_month_day=data[1]
                    hours_minuties=data[2]
                    year=yr_month_day[0:4]
                    month=yr_month_day[4:6]
                    if month[0]=="0":
                        month=month[1:]
                    day=yr_month_day[6:]
                    if day[0]=="0":
                        day=day[1:]
                    hour=hours_minuties[0:2]
                    if hour[0]=="0":
                        hour=hour[1:]
                    minute=hours_minuties[2:]
                    if minute[0]=="0":
                        minute=minute[1:]
                    time_accurate=datetime.datetime(int(year),int(month),int(day),int(hour),int(minute))
                    if start_time_accurate <= time_accurate and end_time_accurate >= time_accurate:
                        if cc in routeViews_Collector_list:
                            finalurl=routeViews+"/"+cc+"/bgpdata/"+st+"/"+datatype+"/"+s
                        else:
                            finalurl=RIPE+cc+"/"+st+"/"+s
                        RibUrls.append(finalurl)

        download(RibUrls, folder_name)
        dirlist=os.listdir(folder_name)
        i = 0
        for name in dirlist:
            i += 1
            #self-defined parse 
            if name=='result':
                continue
            path_to_file = str(folder_name) + "/" + str(name)
            path_to_write = str(folder_name) + '/result/' + str(name) + str(".txt")
            r = Reader(path_to_file)   
            count = 0
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
            print("finish %d / %d"%(i,len(dirlist)))
        print("done!")

#route-views.eqix ribs 2021-07-12-06:00 2021-06-19-10:00
#route-views.eqix,rrc15 updates 2015-04-01-14:00 2015-04-01-14:20
#all ribs 2021-07-12-01:00 2021-07-12-12:00
# rrc03 ribs 2021-07-12-12:00 2021-07-12-18:00

#W withdrawl
#A announce
#STATE state message
#B RIB

#TODO:
#1.prefect LIVE mode
#2.self-defined parser