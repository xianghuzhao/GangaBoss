#\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\#
import os
import tempfile
from Ganga.Core import ApplicationConfigurationError
import Ganga.Utility.Config
from Ganga.Utility.files import expandfilename
from Ganga.GPIDev.Lib.File import FileBuffer, File
import Ganga.Utility.logging
from GangaBoss.Lib.Dataset.DatasetUtils import *
from GangaBoss.Lib.DIRAC.Dirac import Dirac
from GangaBoss.Lib.DIRAC.DiracUtils import *

logger = Ganga.Utility.logging.getLogger()
#\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\#

def jobid_as_string(job):
  jstr=''
  if job.master: jstr=str(job.master.id)+os.sep+str(job.id)
  else: jstr=str(job.id)
  return jstr

def get_master_input_sandbox(job,extra):
    sandbox = job.inputsandbox[:]
    sandbox += extra.master_input_files[:]
    buffers = extra.master_input_buffers
    sandbox += [FileBuffer(n,s) for (n,s) in buffers.items()]
    logger.debug("Master input sandbox: %s",str(sandbox))
    return sandbox

def get_input_sandbox(extra):
     sandbox = []
     sandbox += extra.input_files[:]
     sandbox += [FileBuffer(n,s) for (n,s) in extra.input_buffers.items()]
     logger.debug("Input sandbox: %s",str(sandbox))
     return sandbox

def is_gaudi_child(app):
    if app.__class__.__name__ == 'Gaudi' \
           or type(app).__bases__[0].__name__ == 'Gaudi':
        return True
    
    if type(app).__bases__[0].__name__ == 'TaskApplication':
        if not app.__class__.__name__ == 'GaudiPython':
            return True
    
    return False


config_boss = Ganga.Utility.Config.getConfig('Boss')
round_search_path = config_boss['RoundSearchPath']
f_rs = open(round_search_path, 'r')
rs_allLines = f_rs.readlines()
f_rs.close()
rs_ranges = []
for rs_line in rs_allLines:
    data = rs_line.strip()
    items = data.split(',')
    rs_ranges.append((int(items[0]), int(items[1]), items[5].lower()))

def get_round_nums(runRangeBlocks):
    '''Get the round number of the run period'''

    roundSet = set()

    for rs_range in rs_ranges:
        rs_runL = rs_range[0]
        rs_runH = rs_range[1]
        for runRange in runRangeBlocks:
            runL = runRange[0]
            runH = runRange[1]

            if runL <  rs_runL and runH >= rs_runL or runL >= rs_runL and runL <= rs_runH or runL >  rs_runH and runH <= rs_runH:
                roundSet.add(rs_range[2])
                break

    if not roundSet:
        roundSet.add('roundxx')

    roundNums = list(roundSet)
    roundNums.sort()
    return roundNums

def get_runLH(runRangeBlocks):
    runL = 0
    runH = 0
    if runRangeBlocks:
        runL = runRangeBlocks[0][0]
        runH = runRangeBlocks[0][1]

    for runRange in runRangeBlocks:
        if runRange[0] < runL:
            runL = runRange[0]
        if runRange[1] < runL:
            runL = runRange[1]
        if runRange[0] > runH:
            runH = runRange[0]
        if runRange[1] > runH:
            runH = runRange[1]
    return (runL, runH)

def create_runscript(app,outputdata,job):

  config = Ganga.Utility.Config.getConfig('Boss')
  which = 'GaudiPython'
  opts = None
  if is_gaudi_child(app):
      which = 'Gaudi'
      opts = 'options.pkl'
      recopts = 'recoptions.pkl'
      #opts = app.optsfile[0].name
  
  jstr = jobid_as_string(job)
  appname = app.get_gaudi_appname()
  rec = 0
  if app.recoptsfile:
     rec = 1
  script =  "#!/usr/bin/env python\n\nimport os,sys\n\n"
  script += 'data_output = %s\n' % outputdata.files
  script += 'xml_cat = \'%s\'\n' % 'catalog.xml'
  script += 'data_opts = \'data.py\'\n'
  script += 'recdata_opts = \'recdata.py\'\n'
  script += 'opts = \'%s\'\n' % opts 
  script += 'recopts = \'%s\'\n' % recopts 
  script += 'app = \'%s\'\n' % appname
  script += 'app_upper = \'%s\'\n' % appname.upper()
  script += 'version = \'%s\'\n' % app.version
  script += 'package = \'%s\'\n' % app.package
  script += "job_output_dir = '%s/%s/%s/outputdata'\n" % \
            (config['DataOutput'],outputdata.location,jstr)
  script += 'cp = \'%s\'\n' % config['cp_cmd']
  script += 'mkdir = \'%s\'\n' % config['mkdir_cmd']
  script += 'platform = \'%s\'\n' % app.platform
  script += 'import os \n'   
  
  if opts:
    script += """# check that options file exists
if not os.path.exists(opts):
    opts = 'notavailable'
    os.environ['JOBOPTPATH'] = opts
else:
    #os.environ['JOBOPTPATH'] = '%s/%s/%s_%s/%s/%s/%s/options/job.opts' \
                               #% (os.environ['BesArea'],app_upper,
                               #   app_upper,version,package,app,version)
    print 'Using the master optionsfile:', opts
    #print 'the current directory and files:', os.system('ls -lR')
    print 'the data files:', os.system('ls -al /ihepbatch/cc/zhangxm/BESIII_64/6.6.0/TestRelease/TestRelease-00-00-75/run/rhopi_1.rtraw')
    sys.stdout.flush()
    
"""

  script+="""# check that SetupProject.sh script exists, then execute it
os.environ['User_release_area'] = ''  
os.environ['CMTCONFIG'] = platform  
#bossShell = os.environ['GANGABOSSENVIRONMENT']
#print 'Using %s to set up BOSS env' % bossShell
#os.system('/usr/bin/env bash -c \"source %s && printenv > \
#/tmp/env.tmp\"' % bossShell)
#for line in open('/tmp/env.tmp').readlines():
#    varval = line.strip().split('=')
#    os.environ[varval[0]] = ''.join(varval[1:])
sys.stdout.flush()
        
# add lib subdir in case user supplied shared libs where copied to pwd/lib
os.environ['LD_LIBRARY_PATH'] = '.:%s/lib:%s\' %(os.getcwd(),
                                                 os.environ['LD_LIBRARY_PATH'])
                                                 
#run
sys.stdout.flush()
os.environ['PYTHONPATH'] = '%s/InstallArea/python:%s' % \\
                            (os.getcwd(), os.environ['PYTHONPATH'])
os.environ['PYTHONPATH'] = '%s/InstallArea/%s/python:%s' % \\
                            (os.getcwd(), platform,os.environ['PYTHONPATH'])
bopts= os.path.splitext(opts)[0] + '.opts'
brecopts= os.path.splitext(recopts)[0] + '.opts'

"""
  if which is 'GaudiPython':
    script += 'cmdline = \"python ./gaudipython-wrapper.py\"\n'
  else:
    #script += 'cmdline = \"%s/scripts/gaudirun.py %s data.py\" % '
    #script += 'cmdline = \"source %s;\" % '
    #script += 'bossShell\n'
    script += 'cmdline = \"gaudirun.py -n -v -o %s %s %s;\" % '
    script += '(bopts,opts,data_opts)\n'
    #script += "(os.environ['GAUDIROOT'],opts)\n"
    script += 'cmdline += \"boss.exe %s;\" % ' 
    script += 'bopts\n' 
    if rec:
       script += 'cmdline += \"gaudirun.py -n -v -o %s %s %s;\" % '
       script += '(brecopts,recopts,recdata_opts)\n'
       script += 'cmdline += \"boss.exe %s\" % '
       script += 'brecopts\n'
    script += """
# run command
os.system(cmdline)
print cmdline

# make output directory + cp files to it
if data_output:
    os.system('%s -p %s' % (mkdir,job_output_dir))
for f in data_output:
    cpval = os.system('%s %s %s/%s' % (cp,f,job_output_dir,f))
    print 'Copying %s to %s' % (f,job_output_dir)
    sys.stdout.flush()
    if cpval != 0:
        print 'WARNING:  Could not copy file %s to %s' % (f,job_output_dir)
        print 'WARNING:  File %s will be lost' % f
        cmd = 'ls -l %s' % f
        print 'DEBUG INFO: Performing \"%s\" (check stdout & stderr)' % cmd
        os.system(cmd)
        sys.stdout.flush()
    # sneaky rm
    os.system('rm -f ' + f)
"""    
  return script

#\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\#
