# Author: Justin Culp coded and Andy Li added Toll zone functions
# Date: 12/06/2016
#
# Description: This script makes a copy of the network links and creates midpoints from these links. The link midpoints are
#              then used to spatial join with the TAZ. The spatial join is then used to update the TAZID in the network links shapefile. Next
#              the network nodes are spatial joined with the TAZ, then the spatil join in used to update the TAZID in the network nodes shapefile.

# Requires: ArcGIS 10.2 Desktop Basic
# run in cmd in this folder: C:\Python27\ArcGIS10.6\python 01_Update_HOT_arcpy.py

# Import arcpy module
print "\nRunning Update HOTzone Python Script\n\n\n" 
print "Importing arcpy site package...\n"
import arcpy, sys, os, imp, time, traceback

tollz_shp = r'inputs-04-14\\Tollz_shp.shp'
Scenario_Link = r'inputs-04-14\\C2_Link.shp'
Scenario_Node = r'inputs-04-14\\C2_Node.shp'
UsedZones = '3629'
temp_folder = r'temp_arcpy'
log = os.path.join(temp_folder,r'LogFile_UpdateHOT.txt')

# Set workspace environment
from arcpy import env
env.overwriteOutput = True

# Print key variabls to screen
print "tollz_shp: \n    "         + tollz_shp      + "\n"
print "Scenario_Link: \n    "     + Scenario_Link     + "\n"
print "Scenario_Node: \n    "     + Scenario_Node     + "\n"
print "UsedZones: \n    "         + str(UsedZones)    + "\n"
print "Temp Folder:  \n    "      + temp_folder       + "\n"

# Open log file
logFile = open(log, 'w')
logFile.write(tollz_shp+'\n')
logFile.write(Scenario_Link+'\n')
logFile.write(Scenario_Node+'\n')
logFile.write(str(UsedZones)+'\n')
logFile.write(temp_folder+'\n')

#raw_input()


## Define Variables
# Variables: Input
tollz_shp      = str(tollz_shp)
link_shp          = str(Scenario_Link)
node_shp          = str(Scenario_Node)
UsedZones         = str(UsedZones)
temp_folder       = str(temp_folder)

# Variables: Intermediate
link_taz_sj       = os.path.join(temp_folder, "Link_TAZ_SJ_deleteTemp.shp")
node_taz_sj       = os.path.join(temp_folder, "Node_TAZ_SJ_deleteTemp.shp")

# Variables: Output
out_link2          = os.path.join(temp_folder, "C1_Link_HOT.shp")
out_node2          = os.path.join(temp_folder, "C1_Node_HOT.shp")
out_link_mp       = os.path.join(temp_folder, "C1_Link_Midponts.shp")

# Codeblock to calculate HOTzone

fill_node_t = """def calctollzoneID(tazid, node, global_n):
  if node <= int(global_n):
    return 0
  else:
    return tazid """

fill_link_t = """def calctollzoneID(tazid, aField, bField, global_n):
    return tazid """


# Geoprocessing steps


def TagLinksWithtollzoneID():
    print "\n\nImporting Highway Link data..."
    arcpy.CopyFeatures_management(link_shp, out_link2) 
    # print "\nCalculating Highway Link distance (in miles) and updating DISTANCE field..."
    # arcpy.CalculateField_management(out_link2, "DISTANCE", "!shape.length@miles!", "PYTHON_9.3", "")
    print "\nCalculating Highway Link midpoint coord and updating X_MID & Y_MID fields..."
    # Add the X_MID and Y_MID fields - Check if existing first
    field_list = arcpy.ListFields(out_link2)
    for field in field_list:
        if field.name == "X_MID" or field.name == "Y_MID":
            arcpy.DeleteField_management(out_link2, field.name)
    arcpy.AddField_management(out_link2, "X_MID", "DOUBLE")
    arcpy.AddField_management(out_link2, "Y_MID", "DOUBLE")
    # Calculate link X_MID and Y_MID
    arcpy.CalculateField_management(out_link2, "X_MID", "!shape!.positionAlongLine(0.5, True).firstPoint.X", "PYTHON_9.3", "")
    arcpy.CalculateField_management(out_link2, "Y_MID", "!shape!.positionAlongLine(0.5, True).firstPoint.Y", "PYTHON_9.3", "")
    spatialRef = arcpy.Describe(out_link2).spatialReference
    print "\nMaking new point shapefile from Highway Link midpoint..."
    arcpy.MakeXYEventLayer_management(out_link2, "X_MID", "Y_MID", "MidPoints", spatialRef)
    arcpy.Select_analysis("MidPoints", out_link_mp)
    print "\nSpatial joining Tollz_shp to Link midpoints (this may take a few minutes)..."
    arcpy.SpatialJoin_analysis(out_link_mp, tollz_shp, link_taz_sj, "JOIN_ONE_TO_ONE", "", "", "WITHIN", "", "")
    arcpy.MakeTableView_management(out_link2, "LinkMP_TV")
    arcpy.AddJoin_management("LinkMP_TV", "LINKID", link_taz_sj, "LINKID")
    basename = arcpy.Describe("LinkMP_TV").basename
    joinbase = arcpy.Describe(link_taz_sj).basename
    print "\nUpdating Highway Link HOTZONE ID...\n"
    arcpy.CalculateField_management("LinkMP_TV", "HOT_ZONEID","calctollzoneID(!"+joinbase+".EL_Zone!,!"+basename+".A!,!"+basename+".B!,"+str(UsedZones)+")", "PYTHON_9.3", fill_link_t)
    arcpy.Delete_management("Midpoints")
    arcpy.Delete_management("LinkMP_TV")



def TagNodesWithTollzoneID() :
    print "\n\nImporting Highway Node data for joining toll zone purpose.."
    arcpy.CopyFeatures_management(node_shp, out_node2)
    print "\nSpatial joining Tollzone shape to Highway Nodes (this may take a few minutes)..."
    arcpy.SpatialJoin_analysis(out_node2, tollz_shp, node_taz_sj, "JOIN_ONE_TO_ONE", "", "", "WITHIN", "", "")
    arcpy.MakeTableView_management(out_node2, "Node_TV")
    arcpy.AddJoin_management("Node_TV", "N", node_taz_sj, "N")
    basename = arcpy.Describe("Node_TV").basename
    joinbase = arcpy.Describe(node_taz_sj).basename
    print "\nUpdating Highway Node TollzoneID...\n"
    arcpy.CalculateField_management("Node_TV", "HOT_ZONEID","calctollzoneID(!"+joinbase+".EL_Zone!,!"+basename+".N!,"+str(UsedZones)+")", "PYTHON_9.3", fill_node_t)
    arcpy.Delete_management("Node_TV")
    


def Main():
    try:
        print "\n\nRunning script..."
        print "Start Time: " + time.strftime('%X %x %Z')+"\n"
        TagLinksWithtollzoneID()
        #TagNodesWithTollzoneID()        
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




