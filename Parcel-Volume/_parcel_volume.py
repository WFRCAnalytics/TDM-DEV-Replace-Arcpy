
# Begin script
print "\nRunning Calculate Parcel-Volume Python Script\n\n\n" 


# Import arcpy module
print "Importing arcpy site package...\n\n"
import arcpy, sys, os, imp, time, traceback
from arcpy.sa import *


# Set workspace environment
from arcpy import env
env.overwriteOutput = True


# Set python script path
Pyth_root_dir = os.path.dirname(sys.argv[0])
print "Python root directory: \n  " + Pyth_root_dir + "\n\n"


# Begin log file
log = os.path.join(Pyth_root_dir, "LogFile_REMM_ParcelVol.txt")
logFile = open(log, 'w')

logFile.write('Begin LOG File:\n\n\n')

logFile.write('Log File:\n')
logFile.write('  ' + log + '\n\n')

logFile.write('Python Root Folder:\n')
logFile.write('  ' + Pyth_root_dir + '\n')

print "Log File: \n  " + log + "\n\n"


# Get input variables from Cube
get_variables = os.path.join(Pyth_root_dir, r"_VarCube_REMM_ParcelVol.txt")

# Load file variables from input text file
f = open(get_variables, 'r')
global data
data = imp.load_source('data', '', f)
f.close()

logFile.write('Cube variables input file:\n')
logFile.write('  ' + get_variables + '\n\n')

logFile.write('  ' + data.Scripts_folder   + '\n')
logFile.write('  ' + data.Scenarios_folder + '\n')

print "Cube variables input file: \n    " + get_variables + "\n\n"

print "Scripts Folder: \n  "    + data.Scripts_folder    + "\n"
print "Scenarios Folder: \n  "  + data.Scenarios_folder  + "\n\n"



def CalcParcelVolume():
    print "\n\nStart Computing Volume"
    Volumeshape = os.path.join(data.Scenarios_folder, r"volumeshapefile.shp")
    VolumeDensity = os.path.join(data.Scripts_folder, r"supporting_files\KernelDensity.gdb\VolumeDensity")
    Parcel = os.path.join(data.Scripts_folder, r"supporting_files\KernelDensity.gdb\parcelpointshape04102017UTM")
    VolumePoint = os.path.join(data.Scripts_folder, r"supporting_files\KernelDensity.gdb\volumepoint")
    
    print "Getting License"
    while arcpy.CheckExtension("Spatial") != "Available":
        print "Waiting For License"
        time.sleep(60)
    arcpy.CheckOutExtension("Spatial")
    print "Calculating Kernel Density"
    outKDens = KernelDensity(Volumeshape, "DY_VOL", 100, 1000, "SQUARE_MAP_UNITS")
    print VolumeDensity
    print "Calculating Kernel Densityxxxxxxxxxxxx"
    outKDens.save(VolumeDensity)
    print "Join to Point"
    ExtractValuesToPoints(Parcel, VolumeDensity, VolumePoint,
                          "NONE", "VALUE_ONLY")
    print "Return License"
    arcpy.CheckInExtension("Spatial")
    print "Export Table"
    #arcpy.FeatureClassToShapefile_conversion(VolumePoint, os.getcwd())
    
    arcpy.FeatureClassToFeatureClass_conversion(VolumePoint, data.Scenarios_folder, 
                                                "volumepoint.shp")
    print "End Computing Volume"


def Main():
    try:
        print "\n\nRunning script..."
        print "Start Time: " + time.strftime('%X %x %Z')+"\n"
        CalcParcelVolume()      
        print "Script End Time: " + time.strftime('%X %x %Z')
        logFile.write("All Finished"+"\n")
        logFile.write("Script End Time: " + time.strftime('%X %x %Z'))
        logFile.close()
    except:
        print "*** There was an error running this script - Check output logfile."
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "\nPYTHON ERRORS:\nTraceback info:\n"+tbinfo+"\nError Info:\n"+str(sys.exc_info())
        msgs = "\nArcPy ERRORS:\n"+arcpy.GetMessages()+"\n"
        logFile.write(""+pymsg+"\n")
        logFile.write(""+msgs+"\n")
        logFile.close()
        sys.exit(1)
  
Main()

#CalcParcelVolume() 


