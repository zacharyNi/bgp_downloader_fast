import os,sys

folder_name="2021-07-12-01:00->2021-07-12-12:00||all(RIBS)/result/"
dirlist=os.listdir(folder_name)
data=set()
for name in dirlist:
    for line in open(folder_name+name):
        data.add(line)
w=open(folder_name+"finalRes.txt","w")
for d in data:
    w.writelines(d)
w.close()