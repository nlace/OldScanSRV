
# Simple Scan Server
# Nicholas Lace



import os, shutil
import time
from Queue import Queue
from threading import Thread

import cherrypy
from mako.template import Template
from os import listdir
from os.path import isfile, join, isdir
import zipfile


#simple global variable to tell the interface if the scanner is running or not
scannerrunning=False


#root directory of server
root = "/home/pi/scans"

#root of mushu storage server (mounted already)
mushuroot = "/home/pi/merp"


from PIL import Image
from fpdf import FPDF

# I dont' want to block the cherrypy instance from doing its job while we do a scan job
# Its a bit overkill, but I setup a queue and a seperate thread just for running the scans

def handlescan(q):
    global scannerrunning
    while True:
        item = q.get()
        batch = item['time']
        res = item['res']
        print('Thread got',item)
        doscan(batch, res)
        q.task_done()
        scannerrunning = False

q = Queue(maxsize=0)
#num_threads = 1

worker = Thread(target=handlescan, args=(q,))
worker.setDaemon(True)
worker.start()


## Post processing on the PI takes too long, any additional work should be done
## another computer, I'll leave this here as threading would make post process
## very fast


## post processing queue 
#
#def doproc(q):
#    while True:
#        lecommand = q.get()
#        os.system(lecommand)
#
#        
#        q.task_done()
#
#
#
#ppq = Queue(maxsize=0)
#for i in range(4):
#    w2 = Thread(target=doproc, args=(ppq,))
#    w2.setDaemon(True)
#    w2.start()
#    

def doscan(letime, res):


    os.mkdir(letime)
    os.chdir(letime)

    batch = letime+"-%04d.jpg"
    #first capture scans from scanner
    os.system('scanimage --source="ADF Duplex" -d fujitsu:fi-5750Cdj:100509 --format=jpeg --mode=color --batch="%s" --resolution=%s ' % (batch, res))
    print('Capture Complete')
    
    lepath = "."
    onlyfiles = [f for f in listdir(lepath) if isfile(join(lepath, f))]   
    onlyfiles.sort()

    pdf = None
    zf = zipfile.ZipFile('%s.zip' % letime, mode='w')
    accum = []
    pair = 1
    for f in onlyfiles:
        accum.append(f)
        
        #when accum is 2 long, we have a front/back pair of scans
        if len(accum) == 2:
            
            
            
            pages = map(Image.open, accum)
            w, h = zip(*(i.size for i in pages))
            
            total_width = sum(w)
            max_height = max(h)
            
            new_im = Image.new('RGB', (total_width, max_height))
            
            x_offset = 0
            for im in pages:
              new_im.paste(im, (x_offset,0))
              x_offset += im.size[0]
            
            concat = 'Page-%s-%04d.jpg' % (letime, pair) #formatting for new name
            new_im.save(concat, format='JPEG')
            zf.write(concat)
            
            #Nuke source images
            for i in accum:
                os.remove(i)
            #if pdf hasn't been set yet, create pdf with size of first scan
            if pdf == None:
                cover = Image.open(concat)
                width, height = cover.size

                pdf = FPDF(unit = "pt", format = [width, height])
            pdf.add_page()
            pdf.image(concat, 0, 0)
                
            accum = []
            pair = pair + 1
            
    #the files we want are the zip and pdf, lets close and write those now          
    zf.close()
    pdf.output("%s.pdf" % letime, "F")
    
    
    #now copy to MUSHU (or whatever you name your storage server)
    mushudir = os.path.join(mushuroot, letime)
    os.mkdir(mushudir)
    shutil.copy('%s.zip' % letime, mushudir)
    shutil.copy('%s.pdf' % letime, mushudir)
    
    os.chdir(root)


class scanserver(object):
    @cherrypy.expose
    def index(self, doscan="", **kwargs):
        global scannerrunning
        epoch_time = int(time.time())
        letime = str(epoch_time)

        
        if doscan == "Y":
            a = {"time": letime, 'res': kwargs['res']}
            q.put(a) #add to the queue
            scannerrunning = True
            #now redirect to the output page
            raise cherrypy.HTTPRedirect("output?sid=%s" % letime)
            

        #get scan dirs in folder   
        onlydir = [f for f in listdir(root) if isdir(join(root, f))]
        onlydir.sort()            
     
        mytemplate = Template(filename=root+'/basic.html')
        out = mytemplate.render(odir=onlydir, running=scannerrunning)
        return out
    
    index.exposed = True
    @cherrypy.expose
    def output(self, sid):
        lepath = os.path.join(root, sid)
        onlyfiles = [f for f in listdir(lepath) if isfile(join(lepath, f))]
        onlyfiles.sort()
        
        mytemplate = Template(filename=root+'/view.html')
        out = mytemplate.render( sid=sid, files=onlyfiles)
        return out

# setup the root folder as a static directory - so we can serve the output files
# to the browser
conf = {
   '/static': {
       'tools.staticdir.on': True,
       'tools.staticdir.dir': root
    }
}

cherrypy.server.socket_host = '0.0.0.0'
cherrypy.quickstart(scanserver(),'/',conf)
