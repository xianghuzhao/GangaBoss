#\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\#
from Ganga.GPIDev.Lib.Job import Job
from Ganga.GPIDev.Adapters.IRuntimeHandler import IRuntimeHandler
from Ganga.Utility.files import expandfilename
import Ganga.Utility.logging
from Ganga.GPIDev.Adapters.StandardJobConfig import StandardJobConfig
import Ganga.Utility.Config 
from RTHUtils import *
from GangaBoss.Lib.Dataset.BesDataset import *
from GangaBoss.Lib.Dataset.DatasetUtils import *

logger = Ganga.Utility.logging.getLogger()
#\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\#

class GaudiRunTimeHandler(IRuntimeHandler):
    """This is the application runtime handler class for Gaudi applications 
    using the local, interactive and LSF backends."""
  
    def __init__(self):
        pass
  
    def master_prepare(self,app,extra):

        if extra.inputdata and extra.inputdata.hasLFNs():
            xml_catalog_str = extra.inputdata.getCatalog()
            extra.master_input_buffers['catalog.xml'] = xml_catalog_str
            
        sandbox = get_master_input_sandbox(app.getJobObject(),extra)
        return StandardJobConfig( '', inputbox=sandbox, args=[])

    def prepare(self,app,extra,appmasterconfig,jobmasterconfig):

        if extra.inputdata and extra.inputdata.hasLFNs():
            s='\nFileCatalog().Catalogs = ["xmlcatalog_file:catalog.xml"]\n'
            extra.input_buffers['data.py'] += s

        sandbox = get_input_sandbox(extra)
        outdata = extra.outputdata
        if not outdata: outdata = app.getJobObject().outputdata
        script = create_runscript(app,outdata,app.getJobObject())
        #logger.error("zhangxm log: gaudiscript.py:\n %s " % script)

        return StandardJobConfig(FileBuffer('gaudiscript.py',script,
                                            executable=1),
                                 inputbox=sandbox, args=[],
                                 outputbox=extra.outputsandbox)
        
#\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\#
