# Author: Justin Culp coded and Andy Li added Toll zone functions
# Date: 12/06/2016
#
# Description: This script makes a copy of the network links and creates midpoints from these links. The link midpoints are
#              then used to spatial join with the TAZ. The spatial join is then used to update the TAZID in the network links shapefile. Next
#              the network nodes are spatial joined with the TAZ, then the spatil join in used to update the TAZID in the network nodes shapefile.

# Requires: ArcGIS 10.2 Desktop Basic

# open cmd in this folder and run this command: C:\Python27\ArcGIS10.6\python 01_Update_Link_Node_TAZID_arcpy.py

# Import arcpy module
print "\nRunning Update TAZID Python Script\n\n\n" 
print "Importing arcpy site package...\n"
import arcpy, sys, os, imp, time, traceback

#import importlib.machinery use this instead of imp
# data = importlib.machinery.SourceFileLoader('data', r"_VarCube_WalkBuffer.txt").load_module()
TAZ_shp = r'inputs-04-14\\TAZ.shp'
Scenario_Link = r'inputs-04-14\\C1_Link.shp'
Scenario_Node = r'inputs-04-14\\C1_Node.shp'
UsedZones = '3629'
temp_folder = r'temp_arcpy'
log = os.path.join(temp_folder,r'LogFile_UpdateLinkNodeTAZID.txt')

# Print key variables to screen
print "TAZ_shp: \n    "           + TAZ_shp      + "\n"
print "Scenario_Link: \n    "     + Scenario_Link     + "\n"
print "Scenario_Node: \n    "     + Scenario_Node     + "\n"
print "UsedZones: \n    "         + str(UsedZones)    + "\n"
print "Temp Folder:  \n    "      + temp_folder       + "\n"

# Open log file
logFile = open(log, 'w')
logFile.write(TAZ_shp+'\n')
logFile.write(Scenario_Link+'\n')
logFile.write(Scenario_Node+'\n')
logFile.write(str(UsedZones)+'\n')
logFile.write(temp_folder+'\n')

#raw_input()


## Define Variables
# Variables: Input
taz_shp           = str(TAZ_shp)
link_shp          = str(Scenario_Link)
node_shp          = str(Scenario_Node)
UsedZones         = str(UsedZones)
temp_folder       = str(temp_folder)

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




