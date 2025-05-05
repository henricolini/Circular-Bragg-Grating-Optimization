# -*- coding: utf-8 -*-
"""
Created on Tue Apr 23 17:09:47 2019

@author: ques
"""

import paramiko
import getpass
import os
import socket
import sys
import scp
import numpy as np
import time
import re

class Cluster:
    def __init__(self,username,hostname,port=22):
        self.username=username
        self.hostname=hostname
        self.port = port
        self.password = self.prompt_password(username)
        self.sshcli = paramiko.SSHClient()
        self.sshcli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connect()
        
    def __del__(self):
        self.sshcli.close()

    def prompt_password(self,user):
        """
        Parameters
        ----------
        user : user name

        Returns
        -------
        text : user input password
        """
        from PyQt5.QtWidgets import  QInputDialog, QLineEdit, QApplication
        from PyQt5.QtCore import QCoreApplication

        # Let's avoid to crash Qt-based dev environment (Spyder...)
        app = QCoreApplication.instance()
        if app is None:
            app = QApplication([])

        text, ok = QInputDialog.getText(
            None,
            "Credential",
            "user {}:".format(user),
            QLineEdit.Password)
        if ok and text:
            return text
        raise ValueError("Must specify a valid password")
        
    def connect(self,attempt=10):
        UseGSSAPI = (paramiko.GSS_AUTH_AVAILABLE)
        DoGSSAPIKeyExchange = (paramiko.GSS_AUTH_AVAILABLE)
        connected=False
        counter = 0
        while not connected and counter<attempt:
            try:
                self.sshcli.connect(self.hostname,self.port,self.username,self.password,gss_auth=UseGSSAPI,gss_kex=DoGSSAPIKeyExchange)
                connected=True
                print(100*"\b"+"|--> SSH connection established ")
            except paramiko.AuthenticationException as e:
                self.disconnect()
                print('Wrong password.')
                self.password = self.prompt_password(self.username)
                self.connect(attempt)
            except Exception as e:
                connected=False
                print(100*"\b"+"|--> SSH connection failed "+str(counter+1)+'/'+str(attempt)+' : '+str(e),end='')
                time.sleep(0.1)
                counter+=1
        
        
    def disconnect(self):
        self.sshcli.close()
        
    def put_file(self,l_src,r_dst,verbose=False):
        if verbose:
            print("Transfer to remote ",os.path.basename(l_src)," -> ",os.path.basename(r_dst))
        success=False
        while not success:
            try:
                scp_cli = scp.SCPClient(self.sshcli.get_transport())
                scp_cli.put(l_src,r_dst)
                scp_cli.close()
                success = True
                return True
            except FileNotFoundError as e:
                print('Local file not found : '+str(e))
                return False
            except Exception as e:
                if 'No such file or directory' in str(e):
                    print('File Error : '+str(e))
                    return False
                else:
                    print(e)
                    self.disconnect()
                    self.connect()
                    success = False
            
        
        
    def get_file(self,r_src,l_dst,verbose=False):
        if verbose:
            print("Transfer to local ",os.path.basename(r_src)," -> ",os.path.basename(l_dst))
        success=False
        while not success:
            try:
                scp_cli = scp.SCPClient(self.sshcli.get_transport())
                scp_cli.get(r_src,l_dst)
                scp_cli.close()
                success = True
            except Exception as e:
                if 'No such file or directory' in str(e):
                    print('File Error : '+str(e))
                    success = True
                else:
                    print(e)
                    self.disconnect()
                    self.connect()
                    success = False
        
        
        
    def command(self,cmd):
        try:
            stdin,stdout,stderr = self.sshcli.exec_command('bash -l -c \"'+str(cmd)+'\"')
        except:
            self.connect()
            stdin,stdout,stderr = self.sshcli.exec_command(cmd)
        out=[]
        for line in stdout:
            out.append(line.strip('\n'))
            
        err=[]
        for line in stderr:
            out.append(line.strip('\n'))
        if len(err)>0:
            raise RuntimeError('Command error '+str(err))
            
        return out
    
    
    def start_new_cluster(self):
#        a = self.command("/lsf/local/bin/bstat -r -u "+self.username+" | grep qrsh")
        a = self.list_running_node("qrsh")
        count = len(a)
        
        
        self.command("/opt/torque4/bin/qrsh")
        a = self.command("/lsf/local/bin/bstat -r -u "+self.username+" | grep qrsh")
        if len(a)!=count+1 :
            raise RuntimeError("Could not start new cluster session")
        else:
            print("New session started !")
            
            
    def list_running_node(self):
        a = self.command("/lsf/local/bin/bstat -u "+self.username +" | grep ' RUN '")
        
        ID = []
        for line in a:
            g = re.search('(?P<i>\d+).+'+self.username+'.+',line)
            if g is not None:
                ID.append(g.group("i"))
        return ID
    
    def list_hold_node(self):
        a = self.command("/lsf/local/bin/bstat -u "+self.username +" | grep ' PEND '")
        ID = []
        for line in a.split(','):
            g = re.search('\'(?P<i>\d+).+'+self.username+'.+',line)
            ID.append(g.group("i"))
        return ID
    
    def list_queue_node(self):
        a = self.command("/lsf/local/bin/bstat -u "+self.username +" | grep ' PEND '")
        ID = []
        for line in a.split(','):
            g = re.search('\'(?P<i>\d+).+'+self.username+'.+',line)
            ID.append(g.group("i"))
        return ID

    def list_completed_node(self):
        a = self.command("/lsf/local/bin/bstat -u "+self.username +" | grep ' DONE '")
        ID = []
        for line in a.split(','):
            g = re.search('\'(?P<i>\d+).+'+self.username+'.+',line)
            ID.append(g.group("i"))
        return ID
    
    def get_completed_index(self,ID):
        list_proc = self.command("/lsf/local/bin/bstat -u "+self.username +" "+str(ID)+" | grep ' DONE '")
        ID = []
        for proc in list_proc:
            g = re.search('\[(?P<i>\d+)\]',proc)
            if g is not None:
                ID.append(g.group('i'))  
        return np.array(ID,dtype=np.int)
                
    def get_running_index(self,ID):
        list_proc = self.command("/lsf/local/bin/bstat -u "+self.username +" "+str(ID)+" | grep ' RUN '")
        
        indx = []
        for proc in list_proc:
        
            g = re.search('\[(?P<i>\d+)\]',proc)
            if g is not None:
                indx.append(g.group('i'))
        return np.array(indx,dtype=np.int)
    
    def get_hold_index(self,ID):
        list_proc = self.command("/lsf/local/bin/bstat -u "+self.username +" "+str(ID)+" | grep ' PEND '")
        
        indx = []
        
        for proc in list_proc:
            g = re.search('\[(?P<i>\d+)\]',proc)
            if g is not None:
                indx.append(g.group('i'))
        return np.array(indx,dtype=np.int)
    
    def get_queue_index(self,ID):
        list_proc = self.command("/lsf/local/bin/bstat -u "+self.username +" "+str(ID)+" | grep ' PEND '")
        
        indx = []
        
        for proc in list_proc:
            g = re.search('\[(?P<i>\d+)\]',proc)
            if g is not None:
                indx.append(g.group('i'))
        return np.array(indx,dtype=np.int)    
    
    def get_all_index(self,ID):
        list_proc = self.command("/lsf/local/bin/bstat -u "+self.username +" "+str(ID))
        
        indx = []
        
        for proc in list_proc:
            g = re.search('\[(?P<i>\d+)\]',proc)
            if g is not None:
                indx.append(g.group('i'))
        return np.array(indx,dtype=np.int)
    
    def exists(self,path):
        a = self.command("find "+path)
        if "No such file or directory" in a[0]:
            return False
        else:
            return True
        
        

    
    
    def qsub_array(self,script_name,jobname,data_path,data_name,num_file,max_concurrent=None,solver='FDTD',hours=120,cpu_core=4,mem_usage =4):
        if max_concurrent is None:
            max_concurrent=''
        elif np.isscalar(max_concurrent):
            max_concurrent='%'+str(max_concurrent)
            
            
        self.command("mkdir "+data_path+'/LOGS')
        
        if data_path[0]=='~':
            data_path = '/zhome/24/0/140963/'+data_path[1:]
        
        cmd = "tee "+script_name+" << EOF\n"
        cmd+= "#!/bin/sh\n"
        cmd+= "#BSUB -J "+jobname+"\n"
        cmd+= "#BSUB -u ques@fotonik.dtu.dk\n"
#        cmd+= "#PBS -l feature=XeonE5-2660\n"
#        cmd+= "#BSUB -R \"select[model == XeonE5_2660v3]\"\n"
        cmd+= "#BSUB -n "+str(cpu_core)+"\n"
        cmd+= "#BSUB -R \"rusage[mem="+str(mem_usage)+"GB]\"\n"
        cmd+= "#BSUB -q fotonano\n"
        cmd+= "#BSUB -W "+str(hours)+":00\n"
        cmd+= "#BSUB -o "+data_path+'/LOGS/'+"Log"+"_%J_%I.out\n"
        cmd+= "#BSUB -e "+data_path+'/LOGS/'+"Log"+"_%J_%I.err\n"
        if np.isscalar(num_file):
            cmd+= "#BSUB -J "+jobname+"[1-"+str(num_file)+"]"+max_concurrent+'\n'
        else:
            tmp = "["
            for n_file in num_file:
                tmp+=str(n_file)+","
            tmp = tmp[:-1]
            tmp+= "]"
            cmd+= "#BSUB -J "+jobname+tmp+max_concurrent+'\n'
        cmd+= "export OMP_NUM_THREADS=\$LSB_DJOB_NUMPROC\n"
        cmd+= "module load mpi/1.6.5-gcc-4.4.7\n"
        
        cmd+="OUT=1\n"
        cmd+="while [ \"\$OUT\" != \"0\" ]\n"
        cmd+="do\n"
        cmd+="\t"+"echo \"Running Lumerical \" \n"
#        cmd+= "TMP=\"$LSB_JOBINDEX\"" +"\n"
        if solver=='FDTD':
#            cmd+= "mpiexec -n 4 /appl/FDTD/8.20.1661/bin/fdtd-engine-ompi-lcl -t 1 -log-stdout "+data_path+'/'+data_name+'_\$LSB_JOBINDEX.fsp\n'
            cmd+= "\t"+"mpiexec -n 4 /appl/FDTD/8.20.1661/bin/fdtd-engine-ompi-lcl -t 1  "+data_path+'/'+data_name+'_\$LSB_JOBINDEX.fsp\n'
        elif solver=='varFDTD':
            cmd+= "\t"+"mpiexec -n 4 /appl/MODE/7.12.1661/bin/varfdtd-engine-ompi -log-stdout "+data_path+'/'+data_name+'_\$LSB_JOBINDEX.lms\n'
        elif solver == 'FDE':
            cmd+= "\t"+"/appl/MODE/7.12.1661/bin/fd-engine -log-stdout "+data_path+'/'+data_name+'_\$LSB_JOBINDEX.lms\n'
        elif solver=='EME':
            cmd+= "\t"+"/appl/MODE/7.12.1661/bin/eme-engine -log-stdout "+data_path+'/'+data_name+'_\$LSB_JOBINDEX.lms\n'
        cmd+="\t"+"OUT=\$?\n"
        cmd+="\t"+"echo \$OUT\n"
        cmd+="\t"+"if [ \"\$OUT\" != \"0\" ]\n"
        cmd+="\t"+"then\n"

        cmd+="\t"+"\t"+"echo \"Lumerical error (licence)\"\n"
        cmd+="\t"+"fi\n"
        cmd+="done\n"
        cmd+="\n\n"
        cmd+='EOF'
        self.sshcli.exec_command(cmd)
        
        out = self.command("/lsf/10.1/linux3.10-glibc2.17-x86_64/bin/bsub < "+script_name)
        
        g = re.search("<(?P<jobid>\d+)>",out[0])
        if g is not None:
            jobid = g.group("jobid")
        else:
            raise RuntimeError('Could not launch job : '+str(out))
        counter=1
        stop=1e12
        while len(self.get_all_index(jobid))==0 and counter<=stop:
            print(f"\r{' '*50}\r    |-->Waiting for start...{counter}/{stop}", end='', flush=True)
            time.sleep(5)
            counter+=1
        if len(self.get_all_index(jobid))==0:
            raise RuntimeError('Cluster job could not start !!!')
#        self.command("rm "+script_name)
         
        return jobid    
    

    def bsub(self,data_path,filename):
        
        jobname = os.path.basename(filename).split('.')[0]
        
        cmd = "tee "+data_path+f"/run_{jobname}.sh << EOF\n"
        cmd+= "# embedded options to bsub - start with #BSUB\n"
        cmd+= "#!/bin/sh\n"
        cmd+= "#BSUB -J "+jobname+"\n"
        cmd+= "#BSUB -q hpc\n"
        cmd+= "#BSUB -n 12\n"
        cmd+= "#BSUB -R span[hosts=1]\n"
        cmd+= "#BSUB -R \"rusage[mem=2GB]\"\n"
        cmd+= "#BSUB -W 8:00\n"
        cmd+= "#BSUB -N\n"
        cmd+= "#BSUB -oo "+data_path+'/'+jobname+".out\n"
        cmd+= "#BSUB -eo "+data_path+'/'+jobname+".err\n"
        
        cmd+= "export OMP_NUM_THREADS=\$LSB_DJOB_NUMPROC\n"
        cmd+= "LUMERICALROOT=/appl/lumerical/2022-R1-2898/\n"
        cmd+= "export PATH=\$LUMERICALROOT/mpich2/nemesis/bin:\$PATH\n"
        cmd+= "export\n"
        cmd+= "LD_LIBRARY_PATH=\$LUMERICALROOT/mpich2/nemesis/lib:\$LD_LIBRARY_PATH\n"
        cmd+= "HYDRA_BOOTSTRAP=lsf\n"
        cmd+= "mpiexec \$LUMERICALROOT/bin/fdtd-engine-mpich2-lcl -t 1 "+data_path+'/'+os.path.basename(filename)+"\n"
        cmd+='EOF'
        self.sshcli.exec_command(cmd)
        
        remote_script = f"{data_path}/run_{jobname}.sh"
        
    
        execute = f"/lsf/10.1/linux3.10-glibc2.17-x86_64/bin/bsub < {remote_script}"
        print(f"Submitting job: {execute}")

        out = self.command(execute)
        g = re.search("<(?P<jobid>\d+)>",out[0])
        if g is not None:
            jobid = g.group("jobid")
        else:
            raise RuntimeError('Could not launch job : '+str(out))
        counter=1
        stop=1e12
        while jobid not in self.list_running_node() and counter<=stop:
            print(50*'\b'+"    |-->Waiting for start..."+str(counter)+'/'+str(stop),end='')
            time.sleep(5)
            counter+=1
        if jobid not in self.list_running_node():
            raise RuntimeError('Cluster job could not start !!!')
        #self.command("rm "+data_path+'/FDTD_launcher.sh')
         
        return jobid  


        
    def qsub(self,filename,data_path,solver='FDTD',hours=120,cpu_core=4,mem_usage=4):
        
        jobname = os.path.basename(filename).split('.')[0]
        
        cmd = "tee "+data_path+"/FDTD_launcher.sh << EOF\n"
        cmd+= "#!/bin/sh\n"
        cmd+= "#BSUB -J "+jobname+"\n"
        cmd+= "#BSUB -u 1\n"
#        cmd+= "#PBS -l feature=XeonE5-2660\n"
#        cmd+= "#BSUB -R \"select[model == XeonE5_2660v3]\"\n"
        cmd+= "#BSUB -n "+str(cpu_core)+"\n"
        cmd+= "#BSUB -R \"rusage[mem="+str(mem_usage)+"GB]\"\n"
        cmd+= "#BSUB -q fotonano\n"
        cmd+= "#BSUB -W "+str(hours)+":00\n"
        cmd+= "#BSUB -oo "+data_path+'/'+jobname+".out\n"
        cmd+= "#BSUB -eo "+data_path+'/'+jobname+".err\n"
        
        cmd+= "export OMP_NUM_THREADS=\$LSB_DJOB_NUMPROC\n"
        cmd+= "module load mpi/1.6.5-gcc-4.4.7\n"
#        cmd+= "TMP=\"$LSB_JOBINDEX\"" +"\n"
        if solver=='FDTD':
            cmd+= "mpiexec -n 4 /appl/FDTD/8.20.1661/bin/fdtd-engine-ompi-lcl -t 1 -log-stdout "+data_path+'/'+os.path.basename(filename)+"\n" 
        elif solver=='MODE':
            cmd+= "mpiexec -n 4 /appl/MODE/7.12.1661/bin/varfdtd-engine-ompi -log-stdout "+data_path+'/'+os.path.basename(filename)+"\n" 
        elif solver=='EME':
            cmd+= "/appl/MODE/7.12.1661/bin/eme-engine -log-stdout "+data_path+'/'+os.path.basename(filename)+"\n" 
        cmd+='EOF'
        self.sshcli.exec_command(cmd)
        
        out = self.command("/lsf/10.1/linux3.10-glibc2.17-x86_64/bin/bsub < "+data_path+'/FDTD_launcher.sh')
        
        g = re.search("<(?P<jobid>\d+)>",out[0])
        if g is not None:
            jobid = g.group("jobid")
        else:
            raise RuntimeError('Could not launch job : '+str(out))
        counter=1
        stop=1e12
        while jobid not in self.list_running_node() and counter<=stop:
            print(50*'\b'+"    |-->Waiting for start..."+str(counter)+'/'+str(stop),end='')
            time.sleep(5)
            counter+=1
        if jobid not in self.list_running_node():
            raise RuntimeError('Cluster job could not start !!!')
        self.command("rm "+data_path+'/FDTD_launcher.sh')
         
        return jobid  
        
        
        
        
    
    #    def qsub_array(self,script_name,jobname,data_path,data_name,num_file,max_concurrent=None,solver='FDTD',hours=24):
#        
#        self.command("mkdir "+data_path+'/LOGS')
#        
#        if data_path[0]=='~':
#            data_path = '\${HOME}'+data_path[1:]
#        
#        cmd = "tee "+script_name+" << EOF\n"
#        cmd+= "#!/bin/sh\n"
#        cmd+= "#PBS -N "+jobname+"\n"
#        cmd+= "#PBS -M ques@fotonik.dtu.dk\n"
#        cmd+= "#PBS -l feature=XeonE5-2660\n"
#        cmd+= "#PBS -l nodes=1:ppn=4\n"
#        cmd+= "#PBS -l procs=4\n"
#        cmd+= "#PBS -q fotonano\n"
#        cmd+= "#PBS -l walltime="+str(hours)+":00:00\n"
#        cmd+= "#PBS -o "+data_path+'/LOGS/'+jobname+"_\${PBS_ARRAYID}.out\n"
#        cmd+= "#PBS -e "+data_path+'/LOGS/'+jobname+"_\${PBS_ARRAYID}.err\n"
#        cmd+= "module load mpi\n"
#        if solver=='FDTD':
#            print('Solving for FDTD')
#            cmd+= "mpiexec -n 4 /appl/FDTD/8.20.1661/bin/fdtd-engine-ompi-lcl -t 1 -log-stdout "+data_path+'/'+data_name+'_\${PBS_ARRAYID}.fsp'
#        elif solver=='MODE':
#            print('Solving for VARFDTD')
#            cmd+= "mpiexec -n 4 /appl/MODE/7.12.1661/bin/varfdtd-engine-ompi -log-stdout "+data_path+'/'+data_name+'_\${PBS_ARRAYID}.lms'
#        elif solver=='EME':
#            print('Solving for EME')
#            cmd+= "/appl/MODE/7.12.1661/bin/eme-engine -log-stdout "+data_path+'/'+data_name+'_\${PBS_ARRAYID}.lms'
#        self.command(cmd)
#        
#        if max_concurrent is None:
#            max_concurrent=''
#        elif np.isscalar(max_concurrent):
#            max_concurrent='%'+str(max_concurrent)
#            
#        out = self.command("/opt/torque4/bin/qsub -t 1-"+str(num_file)+str(max_concurrent)+' '+script_name)
#        
#        
#        jobid = out[0].split('[')[0]
#        counter=1
#        stop=1e12
#        while len(self.list_running_node(jobid))==0 and counter<=stop:
#            print(50*'\b'+"    |-->Waiting for start..."+str(counter)+'/'+str(stop),end='')
#            time.sleep(5)
#            counter+=1
#        if len(self.list_running_node(jobid))==0:
#            raise RuntimeError('Cluster job could not start !!!')
#        self.command("rm "+script_name)
#        print()
#        
#        return jobid
    
    
    
#    def qsub_pbs(self,filename,data_path,solver='FDTD',hours=24):
#            
#        jobname = os.path.basename(filename).split('.')[0]
#    
#        cmd = "tee "+data_path+"/FDTD_launcher.sh << EOF\n"
#        cmd+= "#!/bin/sh\n"
#        cmd+= "#PBS -N "+jobname+"\n"
#        cmd+= "#PBS -M ques@fotonik.dtu.dk\n"
#        cmd+= "#PBS -l feature=XeonE5-2660\n"
#        cmd+= "#PBS -l nodes=1:ppn=4\n"
#        cmd+= "#PBS -l procs=4\n"
#        cmd+= "#PBS -q fotonano\n"
#        cmd+= "#PBS -l walltime="+str(hours)+":00:00\n"
#        cmd+= "#PBS -o "+data_path+'/'+jobname+".out\n"
#        cmd+= "#PBS -e "+data_path+'/'+jobname+".err\n"
#        cmd+= "module load mpi\n"    
#        if solver=='FDTD':
#            cmd+= "mpiexec -n 4 /appl/FDTD/8.20.1661/bin/fdtd-engine-ompi-lcl -t 1 -log-stdout "+data_path+'/'+os.path.basename(filename)+"\n" 
#        elif solver=='MODE':
#            cmd+= "mpiexec -n 4 /appl/MODE/7.12.1661/bin/varfdtd-engine-ompi -log-stdout "+data_path+'/'+os.path.basename(filename)+"\n" 
#        elif solver=='EME':
#            cmd+= "/appl/MODE/7.12.1661/bin/eme-engine -log-stdout "+data_path+'/'+os.path.basename(filename)+"\n" 
#        cmd+='EOF'
#        self.sshcli.exec_command(cmd)
#        print(cmd)
#
#        out = self.command("/lsf/10.1/linux3.10-glibc2.17-x86_64/bin/bsub < "+data_path+"/FDTD_launcher.sh")
#        
#        g = re.search("<(?P<jobid>\d+)>",out[0])
#        if g is not None:
#            jobid = g.group("jobid")
#        else:
#            raise RuntimeError('Could not launch job : '+str(out))
#        counter=1
#        stop=1e12
#        while len(self.get_all_index(jobid))==0 and counter<=stop:
#            print(50*'\b'+"    |-->Waiting for start..."+str(counter)+'/'+str(stop),end='')
#            time.sleep(5)
#            counter+=1
#        if len(self.get_all_index(jobid))==0:
#            raise RuntimeError('Cluster job could not start !!!')
##        self.command("rm "+data_path+"/FDTD_launcher.sh")
#        
#        return jobid
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
if __name__=="__main__":
    hpc = Cluster("ques","login2.gbar.dtu.dk",22)
    
        