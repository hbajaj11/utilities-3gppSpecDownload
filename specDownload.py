# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 12:52:12 2020

@author: Harvinder Bajaj

@description: 
This program is used to bulk download 3GPP specs from either 3GPP site in DOC
format or from ETSI site in PDF format. DOC format files are in ZIP format so
program unzips the file and keep only doc files in the folder and removes 
zip files.

"""

import requests
import threading
import zipfile
import os, sys,getopt

class Spec3GPPDownload:
    """Class used to bulk download 3GPP specs in DOC or PDF format.
 
    PDF format 3GPP specs are available in ETSI site and DOC format are 
    available on 3GPP site. Class needs input for spec numbers with Major and
    Minor version and downloadType ("doc" or "pdf"). It will download specs
    in parallel using multi-threading to reduce download time.
    """
    
    #These are read only variables so can be shared by all instances
    specBaseDir = "https://www.etsi.org/deliver/etsi_ts/"
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
    d = {10:'a',11:'b',12:'c',13:'d',14:'e',15:'f',16:'g',17:'h',18:'i',19:'j',20:'k',21:'l',22:'m',}

    def __init__(self):
        """The constructor."""
        #These are read/write variables so should be instance specific
        self.fileFolder = ""
        self.doctype = "doc"
        self.filename = ""
        self.speclst = []
        self.cntLock = threading.Lock()
        self.fileDone = 0
        self.fileNotFound = 0
        self.totalFile = 0
   
    def checkDownloadDir(self):
        if self.fileFolder == "":
            self.fileFolder = "./download/"
            try:
                # Create target Directory
                os.makedirs(self.fileFolder)
                print("Default download Directory " , self.fileFolder ,  " Created ") 
            except FileExistsError:
                print("Directory " , self.fileFolder ,  " already exists")
    def usage(self):
        print('python specDownload.py -s "22.278.15.4.0,22.280.15.3.0,22.179.15.1.0" -f <filename> [-d downloadpath] [-t "doc"/"pdf"]')            
    
    def handleFileInput(self):
        if self.filename == "":
            print("Invalid file name")
            sys.exit()
        f = open(self.filename,"r")
        lines = f.readlines()
        specStr = ","
        lst = []
        for line in lines:
            lst.append( line.replace('v','.'))
        self.speclst = specStr.join(lst)    
    def main(self,args):
        specProvided = False
        filePresent = False
        try:
            opts, args = getopt.getopt(args, "hd:t:s:f:", ["help", "downloadpath=","doctype=","speclst=","file="])
        except getopt.GetoptError as err:
            # print help information and exit:
            print (str(err))  # will print something like "option -a not recognized"
            self.usage()
            sys.exit(2)
        #output = None
        #verbose = False
        for o, a in opts:
            if o in ("-d","--downloadpath"):
                self.fileFolder = a 
                try:
                    # Create target Directory
                    os.makedirs(a)
                    print("Directory " , a ,  " Created ") 
                except FileExistsError:
                    print("Directory " , a ,  " already" )
            elif o in ("-h", "--help"):
                self.usage()
                sys.exit()
            elif o in ("-t", "--doctype"):
                self.doctype = a
            elif o in ("-s", "--speclst"):
                self.speclst = a
                specProvided = True   
            elif o in ("-f","--file"):
                self.filename = a
                filePresent = True
            else:
                assert False, "unhandled option"

        if (specProvided == False) & (filePresent == False):
            self.usage()
            sys.exit()
        if (specProvided == True) & (filePresent == True):
            print("Either provide -s or -f and not both")
            self.usage()
            sys.exit()    
        self.checkDownloadDir()
        if(filePresent == True):
            self.handleFileInput()

    def downloadFile3GPP(self,specSeries,specNum,major,tech,editorial):
        """Method to download DOC specs from 3GPP site."""
        #http://www.3gpp.org/ftp//Specs/archive/22_series/22.179/22179-g50.zip
        major_mapped = self.major_map_fn(major)
        file = "%02d%03d-%s%01d%01d.zip" % (specSeries,specNum,major_mapped,tech,editorial)
        url = "http://www.3gpp.org/ftp//Specs/archive/%02d_series/%02d.%03d/%02d%03d-%s%01d%01d.zip" % (specSeries,specSeries,specNum,specSeries,specNum,major_mapped,tech,editorial)   
        
        #file = "ts_1{series}{spec}v{maj}{tec}{edt}p.pdf".format(series=specSeries,spec=specNum,maj=major,tec=tech,edt=editorial)
        
        headers = {'User-Agent': self.user_agent}
        r = requests.get(url,headers=headers, stream=True)
        if r.status_code == 200: 
            with open(self.fileFolder + file, 'wb') as fd:
                for chunk in r.iter_content(chunk_size=128):
                    fd.write(chunk)
            print('Url: {}'.format(url))
            #print('File: {}'.format(file))
        else:
            print("file not found:",url)
        if r.status_code == 200:    
            with zipfile.ZipFile(self.fileFolder + file, 'r') as zip_ref:
                zip_ref.extractall(self.fileFolder)    
            os.remove(self.fileFolder + file)    

        self.cntLock.acquire()
        try:
            if r.status_code == 200:
                self.fileDone = self.fileDone + 1
            else:
                self.fileNotFound = self.fileNotFound + 1
            print("{}/{} files downloaded".format(self.fileDone,self.totalFile))
            print("{}/{} files not found".format(self.fileNotFound,self.totalFile))
        finally:
            self.cntLock.release()        

    def downloadFileEtsi(self,specSeries,specNum,major,tech,editorial):
        """Method to download PDF specs from ETSI site."""
        lowerSpecNum = specNum - (specNum  % 100)
        higherSpecNum = specNum + (100 - 1- (specNum  % 100))
        #url = "https://www.etsi.org/deliver/etsi_ts/1{series}{lowerSpec}_1{series}{higherSpec}/1{series}{spec}/{maj}.{tec}.{edt}_60/ts_1{series}{spec}v{maj}{tec}{edt}p.pdf".format(series=specSeries,spec=specNum,lowerSpec=lowerSpecNum,higherSpec=higherSpecNum,maj=major,tec=tech,edt=editorial)   
        file = "ts_1%02d%03dv%02d%02d%02dp.pdf" % (specSeries,specNum,major,tech,editorial)
        url = "https://www.etsi.org/deliver/etsi_ts/1%02d%03d_1%02d%03d/1%02d%03d/%02d.%02d.%02d_60/%s" % (specSeries,lowerSpecNum,specSeries,higherSpecNum,specSeries,specNum,major,tech,editorial,file)   
        
        #file = "ts_1{series}{spec}v{maj}{tec}{edt}p.pdf".format(series=specSeries,spec=specNum,maj=major,tec=tech,edt=editorial)
        
        headers = {'User-Agent': self.user_agent}
        r = requests.get(url,headers=headers, stream=True)
        if r.status_code == 200:
            with open(self.fileFolder + file, 'wb') as fd:
                for chunk in r.iter_content(chunk_size=128):
                    fd.write(chunk)
            print('Url: {}'.format(url))
        else:
            print("file not found:",url)

        self.cntLock.acquire()
        try:
            if r.status_code == 200:
                self.fileDone = self.fileDone + 1
            else:
                self.fileNotFound = self.fileNotFound + 1
            print("{}/{} files downloaded".format(self.fileDone,self.totalFile))
            print("{}/{} files not found".format(self.fileNotFound,self.totalFile))
        finally:
            self.cntLock.release()       
    
    def major_map_fn(self,major):
        if major < 10:
            return major
        else:
            return self.d[major]     
    
    def downloadSpecs(self):
        """Method called from main which handles parameters and accordingly
        call function specific to download doc or pdf format specs.Also
        it handles multithreading aspects of downloading multiple specs
        in parallel to reduce time to download"""
        
        thr = []
        slst = list(self.speclst.split(","))
        self.totalFile = len(slst)
        for tmplst in slst:
            lst = list(map(int,tmplst.split(".")))
            #print(lst)
            if self.doctype == "doc" :
                thr.append(threading.Thread(target=self.downloadFile3GPP, args=(lst[0],lst[1],lst[2],lst[3],lst[4]))  )        
            elif self.doctype == "pdf" :
                thr.append(threading.Thread(target=self.downloadFileEtsi, args=(lst[0],lst[1],lst[2],lst[3],lst[4]))  )        
            else:
                print("Invalid download type ({}) specified".format(downloadType))
                return
        for j in thr:
            j.start()
    
        for k in thr:
            k.join()
    

if __name__ == '__main__':

    specLst = [[22,278 ,15,4,0],
            [22,280 ,15,3,0],
            [22,179 ,15,1,0]]
    
    downloadSpec = Spec3GPPDownload()
    downloadSpec.main(sys.argv[1:])
    downloadSpec.downloadSpecs()

