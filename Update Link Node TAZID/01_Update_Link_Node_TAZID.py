# Author: Justin Culp coded and Andy Li added Toll zone functions
# Date: 12/06/2016
#
# Description: This script makes a copy of the network links and creates midpoints from these links. The link midpoints are
#              then used to spatial join with the TAZ. The spatial join is then used to update the TAZID in the network links shapefile. Next
#              the network nodes are spatial joined with the TAZ, then the spatil join in used to update the TAZID in the network nodes shapefile.

# Requires: ArcGIS 10.2 Desktop Basic


# Import arcpy module
print("\nRunning Update TAZID Python Script\n\n\n" )
print("Importing arcpy site package...\n" )
import arcpy, sys, os, imp, time, traceback

# Set workspace environment
from arcpy import env
env.overwriteOutput = True

# Set file paths
Pyth_root_dir = os.path.dirname(sys.argv[0])
print("\n\nDefining variables...\n" )
print("Python root directory: \n    " + Pyth_root_dir + "\n" )

# Get input variables from Cube
get_variables = os.path.join(Pyth_root_dir, r"_VarCube_UpdateTAZID.txt")
print("Cube variables input file: \n    " + get_variables + "\n\n" )

# Load file variables from input text file
f = open(get_variables, 'r')
global data
data = imp.load_source('data', '', f)
f.close()

# print(key variabls to screen
print("TAZ_shp: \n    "           + data.TAZ_shp           + "\n" )
print("Scenario_Link: \n    "     + data.Scenario_Link     + "\n" )
print("Scenario_Node: \n    "     + data.Scenario_Node     + "\n" )
print("UsedZones: \n    "         + str(data.UsedZones)    + "\n" )

print("Temp Folder:  \n    "      + data.temp_folder       + "\n" )

# Open log file
log = os.path.join(Pyth_root_dir, "LogFile_UpdateTAZID.txt")
logFile = open(log, 'w')
logFile.write(get_variables+'\n')
logFile.write(data.TAZ_shp+'\n')
logFile.write(data.Scenario_Link+'\n')
logFile.write(data.Scenario_Node+'\n')
logFile.write(str(data.UsedZones)+'\n')
logFile.write(data.temp_folder+'\n')

#raw_input()


## Define Variables
# Variables: Input
taz_shp           = str(data.TAZ_shp)
link_shp          = str(data.Scenario_Link)
node_shp          = str(data.Scenario_Node)
UsedZones         = str(data.UsedZones)
temp_folder       = str(data.temp_folder)

# Variables: Intermediate
link_taz_sj       = os.path.join(temp_folder, "Link_TAZ_SJ_deleteTemp.shp")
node_taz_sj       = os.path.join(temp_folder, "Node_TAZ_SJ_deleteTemp.shp")

# Variables: Output
out_link          = os.path.join(temp_folder, "C1_Link_TAZID.shp")
out_node          = os.path.join(temp_folder, "C1_Node_TAZID.shp")
out_link_mp       = os.path.join(temp_folder, "C1_Link_Midponts.shp")

# Codeblock to calculate TAZID
fill_node = """def calcTAZID(tazid, node, global_n):
  if node <= int(global_n):
    return node
  else:
    return tazid """


fill_link = """def calcTAZID(tazid, aField, bField, global_n):
  if aField <= int(global_n):
    return aField
  elif bField <= int(global_n):
    return bField
  else:
    return tazid """



# Geoprocessing steps
def TagLinksWithTAZID():
    print("\n\nImporting Highway Link data...")
    arcpy.CopyFeatures_management(link_shp, out_link) 
    print("\nCalculating Highway Link distance (in miles) and updating DISTANCE field...")
    arcpy.CalculateField_management(out_link, "DISTANCE", "!shape.length@miles!", "PYTHON_9.3", "")
    print("\nCalculating Highway Link midpoint coord and updating X_MID & Y_MID fields...")
    # Add the X_MID and Y_MID fields - Check if existing first
    field_list = arcpy.ListFields(out_link)
    for field in field_list:
        if field.name == "X_MID" or field.name == "Y_MID":
            arcpy.DeleteField_management(out_link, field.name)
    arcpy.AddField_management(out_link, "X_MID", "DOUBLE")
    arcpy.AddField_management(out_link, "Y_MID", "DOUBLE")
    # Calculate link X_MID and Y_MID
    arcpy.CalculateField_management(out_link, "X_MID", "!shape!.positionAlongLine(0.5, True).firstPoint.X", "PYTHON_9.3", "")
    arcpy.CalculateField_management(out_link, "Y_MID", "!shape!.positionAlongLine(0.5, True).firstPoint.Y", "PYTHON_9.3", "")
    spatialRef = arcpy.Describe(out_link).spatialReference
    print("\nMaking new point shapefile from Highway Link midpoint...")
    arcpy.MakeXYEventLayer_management(out_link, "X_MID", "Y_MID", "MidPoints", spatialRef)
    arcpy.Select_analysis("MidPoints", out_link_mp)
    print("\nSpatial joining TAZ to Link midpoints (this may take a few minutes)...")
    arcpy.SpatialJoin_analysis(out_link_mp, taz_shp, link_taz_sj, "JOIN_ONE_TO_ONE", "", "", "CLOSEST", "", "")
    arcpy.MakeTableView_management(out_link, "LinkMP_TV")
    arcpy.AddJoin_management("LinkMP_TV", "LINKID", link_taz_sj, "LINKID")
    basename = arcpy.Describe("LinkMP_TV").basename
    joinbase = arcpy.Describe(link_taz_sj).basename
    print("\nUpdating Highway Link TAZID...\n")
    arcpy.CalculateField_management("LinkMP_TV", "TAZID","calcTAZID(!"+joinbase+".TAZID_1!,!"+basename+".A!,!"+basename+".B!,"+str(UsedZones)+")", "PYTHON_9.3", fill_link)
    arcpy.Delete_management("Midpoints")
    arcpy.Delete_management("LinkMP_TV")



def TagNodesWithTAZID():
    print("\n\nImporting Highway Node data...")
    arcpy.CopyFeatures_management(node_shp, out_node)
    print("\nSpatial joining TAZ to Highway Nodes (this may take a few minutes)...")
    arcpy.SpatialJoin_analysis(out_node, taz_shp, node_taz_sj, "JOIN_ONE_TO_ONE", "", "", "CLOSEST", "", "")
    arcpy.MakeTableView_management(out_node, "Node_TV")
    arcpy.AddJoin_management("Node_TV", "N", node_taz_sj, "N")
    basename = arcpy.Describe("Node_TV").basename
    joinbase = arcpy.Describe(node_taz_sj).basename
    print("\nUpdating Highway Node TAZID...\n")
    arcpy.CalculateField_management("Node_TV", "TAZID","calcTAZID(!"+joinbase+".TAZID_1!,!"+basename+".N!,"+str(UsedZones)+")", "PYTHON_9.3", fill_node)
    arcpy.Delete_management("Node_TV")
    


def Main():
    try:
        print("\n\nRunning script...")
        print("Start Time: " + time.strftime('%X %x %Z')+"\n")
        TagLinksWithTAZID()
        TagNodesWithTAZID()
        print("Script End Time: " + time.strftime('%X %x %Z'))
        logFile.write("All Finished"+"\n")
        logFile.write("Script End Time: " + time.strftime('%X %x %Z'))
        logFile.close()
    except:
        print("*** There was an error running this script - Check output logfile.")
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "\nPYTHON ERRORS:\nTraceback info:\n"+tbinfo+"\nError Info:\n"+str(sys.exc_info())
        msgs = "\nArcPy ERRORS:\n"+arcpy.GetMessages()+"\n"
        logFile.write(""+pymsg+"\n")
        logFile.write(""+msgs+"\n")
        logFile.close()
        sys.exit(1)

Main()




