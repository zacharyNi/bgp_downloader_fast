import requests
import threading


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


        
        
    