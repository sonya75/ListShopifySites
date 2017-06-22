import ssl
import socket
from threading import Thread
import threading
import sys
import Queue
import time
import re
import json
import select
import httplib
failqueue=Queue.Queue()
savequeue=Queue.Queue()
varlock=threading.Lock()
def readsocket(sock,osock,limit):
	buf=""
	total=""
	done=0
	result=[]
	errors=[]
	while True:
		try:
			if done>=limit:
				break
			c=httplib.HTTPResponse(sock,buffering=True,strict=True)
			c.begin()
			d=c.read()
			if d=="":
				errors.append(done)
				done+=1
				continue
			if c.status in [403,430,429]:
				errors.append(done)
				done+=1
				continue
			result+=re.findall(r"[a-z|0-9|-]*?[a-z|0-9|-]\.myshopify\.com",d)
			for key,value in c.getheaders():
				if key.lower()=="location":
					if "checkout.shopify.com" not in value:
						result.append(value)
					break
			done+=1
		except:
			break
	result=list(set(result))
	return (result,done,errors)
def checkid():
	global allvars,varlock,SITE,failqueue,savequeue
	sess=None
	osock=None
	while True:
		varlock.acquire()
		todo=allvars.next()
		varlock.release()
		pack=""
		for i in todo:
			pack+=("GET {0} HTTP/1.1\r\nHost: {1}\r\nUser-Agent: Mozilla/5.0 (Windows; U; Windows NT 6.1; en-GB; rv:1.9.2.13) Gecko/20101203 Firefox/3.6.13\r\nAccept: */*\r\nAccept-Language: en-gb,en;q=0.5\r\nConnection: keep-alive\r\n\r\n".format("/"+str(i),"checkout.shopify.com"))
		try:
			if osock==None:
				osock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
				osock.settimeout(15)
				sock=ssl.wrap_socket(osock,ssl_version=ssl.PROTOCOL_TLSv1)
				sock.connect(("checkout.shopify.com",443))
			sock.send(pack)
			results,count,errors=readsocket(sock,osock,len(todo))
			for ij in results:
				savequeue.put(ij)
			for j in todo[count:]:
				failqueue.put(j)
			for jn in errors:
				failqueue.put(todo[jn])
			if count<len(todo):
				osock.close()
				osock=None
				time.sleep(3)
		except Exception as e:
			try:
				osock.close()
			except:
				pass
			osock=None
			print e
			for j in todo:
				failqueue.put(j)
def savetofile():
	global savequeue
	while True:
		f=savequeue.get()
		h=open('shopifysitelist.txt','a')
		h.write(str(f)+"\n")
		h.close()
Thread(target=savetofile).start()
def vargen():
	global failqueue
	o=1
	while True:
		pending=[]
		while True:
			if len(pending)>=200:
				yield pending
				pending=[]
				continue
			try:
				v=failqueue.get_nowait()
				print v
				pending.append(v)
			except:
				break
		if len(pending)<200:
			oo=o+200-len(pending)
			pending+=list(range(o,oo))
			o=oo
		yield pending
		print o
allvars=vargen()
for i in range(0,300):
	Thread(target=checkid).start()
