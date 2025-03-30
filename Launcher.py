# -*- coding: utf-8 -*-
"""
Created on Tue May 21 10:24:31 2019

@author: ques
"""
#from LumericalWrapper import Lumerical
from SSHHandler import Cluster

from PyQt5.QtWidgets import QApplication, QFileDialog

import threading as th

import os,time

class Launcher:
    def __init__(self,username,host,path):
#        self.lum = Lumerical()
        self.ssh = Cluster(username,host,22)
        
        
        self.r_dir = path
        
        self.current_ID = []
        self.current_l_file = []
        self.current_r_file = []
        
        self.run = False
        self.msg_disp=False
        
        self.thread_load = None
        

        
    def simulate(self, filename=None , hours=24,solver="FDTD", mem_usage = 4):  
        if filename is None or not os.path.exists(filename):
            files, _ = QFileDialog.getOpenFileNames(None, "Open Simulation", "", "Lumerical file (*.fsp *.lms)")
        else:
            files=[filename]
        IDs = []
        for file in files:
            if os.path.exists(file):
                self.msg_disp=False
                print('\nSimulating : '+file)
                new_file=file
                
                    
                self.ssh.put_file(file,self.r_dir+'/'+os.path.basename(new_file))
                
                    
                ID = self.ssh.bsub(self.r_dir,new_file)
                
                
                self.current_ID.append(ID)
                self.current_l_file.append(file)
                self.current_r_file.append(new_file)
                
                self.msg_disp=True
                IDs.append(ID)
                
                
#        if not self.run:
#            self.start_thread_download()
            
        return IDs


    def get_download(self,sleep=60*5):
        
        animation = "|/-\|/-\\"
        indx = 0
        
        self.run=True
        while self.run:
            if self.msg_disp:
                print("\r" + " " * 80, end="")  # Clears the entire line
                print(100*'\b'+animation[indx % len(animation)]+" Waiting simulations :",len(self.current_ID),end='')
                indx+=1
                time.sleep(sleep)       
            if self.run and len(self.current_ID)==0:
                self.run=False
            try:
                for i,ID in enumerate(self.current_ID):
                    if ID not in self.ssh.list_running_node():
                        print("\n Downloading...")
                        self.ssh.get_file(self.r_dir+'/'+os.path.basename(self.current_r_file[i]),self.current_r_file[i])
                        self.ssh.command('rm '+self.r_dir+'/'+os.path.basename(self.current_r_file[i]))
                        print('\n\n')
                        print('\n File downloaded : '+self.current_r_file[i])
                        print('\n\n')
                        self.current_l_file.remove(self.current_l_file[i])
                        self.current_r_file.remove(self.current_r_file[i])
                        self.current_ID.remove(self.current_ID[i])
                        break
            except KeyboardInterrupt:
                print('\nLoop stopped by user')
                self.run=False
                
    def start_thread_download(self,sleep=60*10):
        self.run=True
        self.msg_disp=True
        self.thread_load = th.Thread(target=self.get_download,name='Simulation Download',args=(sleep,))
        self.thread_load.start()
        print('\nStarting downloading simulations')
                
    def stop_thread_download(self):
        
        self.run = False
        self.thread_load.join()
        print('\nStopped downloading simulations')
        
        
    def __del__(self):
        self.run=False
        if self.thread_load is not None and self.thread_load.isAlive():
            self.thread_load.join()
                
            
            
            
            
# if __name__=='__main__':
#     launch = Launcher()
    
    
#     ID = launch.simulate(hours=120)
    
#     launch.start_thread_download(sleep=60*10)
