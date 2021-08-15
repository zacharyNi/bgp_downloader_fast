import websocket
import configparser
import json
from urllib.parse import urlparse
import datetime
from bs4 import BeautifulSoup
import urllib.request
import urllib.error
import re

cp = configparser.ConfigParser()
cp.read('config/collector_list.ini')

routeViews="http://archive.routeviews.org/"
routeViews_Collectors=cp.get('collector_list','RouteViews')
routeViews_Collector_list=json.loads(routeViews_Collectors)

RIPE="http://data.ris.ripe.net/"
RIPE_collectors=cp.get('collector_list','RIPE')
RIPE_collector_list=json.loads(RIPE_collectors)

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

class BGPDownloader:
    def __init__(self) -> None:
        self.chosen_collectors=[]
        self.start_time=""
        self.end_time=""
        self.data_type=""

    def set_collector(self,collector):
        self.collector=collector
        if collector == "all":
            self.chosen_collectors=routeViews_Collector_list+RIPE_collector_list
        else:
            collectors = collector.split(",")
            for c in collectors:
                if c.lower() in routeViews_Collector_list or c.lower() in RIPE_collector_list:
                    self.chosen_collectors.append(c.lower())
    
    def set_time(self,start_time,end_time):
        self.start_time=start_time
        self.end_time=end_time
    
    def set_datatype(self,datatype):
        if datatype.upper() == "RIBS":
            self.data_type="RIBS"
        elif datatype.upper() == "UPDATES":
            self.data_type="UPDATES"
    
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
    
    def getUrl(self):
        if self.chosen_collectors==[]:
            print("no collectors chosen!")
            return
        elif self.start_time=="" or self.end_time=="":
            print("no start_time or end_time!")
            return
        elif self.data_type=="":
            print("no data type!")
            return
        else:
            return self.findUrl() 
    
    def findUrl(self):
        RibUrls=[] 
        start_time_handler = timeHandler(self.start_time)
        end_time_handler = timeHandler(self.end_time)
        start_time_yrandmonth = start_time_handler.yrandmonth()
        end_time_yrandmonth = end_time_handler.yrandmonth()
        start_time_accurate=start_time_handler.accurate_time()
        end_time_accurate=end_time_handler.accurate_time()
        for cc in self.chosen_collectors:
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
            for st in selected_times:
                sources=[]
                if cc in routeViews_Collector_list:
                    base_url=routeViews + cc+ "/bgpdata/" + st + "/" + self.data_type + "/"
                else:
                    base_url = RIPE + cc + "/" + st + "/"

                if cc in routeViews_Collector_list:
                    if self.data_type=="UPDATES":
                        pattern_str='^updates'
                    elif self.data_type=="RIBS":
                        pattern_str='.bz2$'
                else:
                    if self.data_type=="UPDATES":
                        pattern_str='^updates'
                    elif self.data_type=="RIBS":
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
                            finalurl=routeViews+"/"+cc+"/bgpdata/"+st+"/"+self.data_type+"/"+s
                        else:
                            finalurl=RIPE+cc+"/"+st+"/"+s
                        RibUrls.append(finalurl)
        return RibUrls

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

