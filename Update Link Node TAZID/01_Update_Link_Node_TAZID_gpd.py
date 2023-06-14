# Author: Justin Culp coded and Andy Li added Toll zone functions
# Date: 12/06/2016
#
# Description: This script makes a copy of the network links and creates midpoints from these links. The link midpoints are
#              then used to spatial join with the TAZ. The spatial join is then used to update the TAZID in the network links shapefile. Next
#              the network nodes are spatial joined with the TAZ, then the spatil join in used to update the TAZID in the network nodes shapefile.

# Requires: ArcGIS 10.2 Desktop Basic

#C:\Users\cday\AppData\Local\ESRI\conda\envs\arcgispro-py3-geopandas\python.exe 01_Update_Link_Node_TAZID_gpd.py

# Import geopandas module
print("\nRunning Update HOTzone Python Script\n\n\n")
print("Importing geopandas site package...\n")
import geopandas as gpd
import sys
import os
import imp
import time
import traceback

TAZ_shp = r'inputs-04-14\\TAZ.shp'
Scenario_Link = r'inputs-04-14\\C1_Link.shp'
Scenario_Node = r'inputs-04-14\\C1_Node.shp'
UsedZones = '3629'
temp_folder = r'temp_gpd'
log = os.path.join(temp_folder,r'LogFile_UpdateLinkNodeTAZID.txt')

# Print key variabls to screen
print("TAZ_shp: \n    "           + TAZ_shp           + "\n")
print("Scenario_Link: \n    "     + Scenario_Link     + "\n")
print("Scenario_Node: \n    "     + Scenario_Node     + "\n")
print("UsedZones: \n    "         + str(UsedZones)    + "\n")
print("Temp Folder:  \n    "      + temp_folder       + "\n")

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

def calcTAZID_Link(tazid, aField, bField, global_n):
    if aField <= int(global_n):
        return aField
    elif bField <- int(global_n):
        return bField
    else:
        return tazid

# Geoprocessing steps
def TagLinksWithTAZID():
    print("\n\nImporting Highway Link data...")
    gdf_link = gpd.read_file(link_shp)

    print("\nCalculating Highway Link distance (in miles) and updating DISTANCE field...")
    gdf_link["DISTANCE"] = gdf_link.geometry.length / 1609.34  # Conversion from meters to miles  (DO I NEED THIS CONVERSION?)

    print("\nCalculating Highway Link midpoint coord and updating X_MID & Y_MID fields...")
    gdf_link["X_MID"] = gdf_link.geometry.interpolate(0.5, normalized=True).x
    gdf_link["Y_MID"] = gdf_link.geometry.interpolate(0.5, normalized=True).y

    print("\nMaking new point shapefile from Highway Link midpoint...")
    gdf_midpoints = gdf_link
    gdf_midpoints = gdf_midpoints.set_geometry(gdf_midpoints.geometry.centroid)
    gdf_midpoints.to_file(out_link_mp)

    print("\nSpatial joining TAZ to Link midpoints (this may take a few minutes)...")
    gdf_taz = gpd.read_file(taz_shp)
    gdf_link_taz_sj = gpd.sjoin(gdf_midpoints, gdf_taz, how="inner", op="within") # LEFT JOIN?

    print("\nUpdating Highway Link TAZID...\n")
    gdf_midpoints_taz0 = gdf_midpoints.copy()
    gdf_midpoints_taz0['TAZID'] = 0
    gdf_midpoints_taz0.to_file(out_link)

    gdf_link_mp = gdf_midpoints_taz0.merge(gdf_link_taz_sj, left_on="LINKID", right_on="LINKID")
    gdf_link_mp["TAZID"] = gdf_link_mp.apply(lambda row: calcTAZID_Link(row["TAZID_1"], row["A"], row["B"], UsedZones), axis=1)
    gdf_link_mp.to_file(link_taz_sj)

#def TagNodesWithTAZID():
#    print("\n\nImporting Highway Node data...")
#    arcpy.CopyFeatures_management(node_shp, out_node)
#    print("\nSpatial joining TAZ to Highway Nodes (this may take a few minutes)...")
#    arcpy.SpatialJoin_analysis(out_node, taz_shp, node_taz_sj, "JOIN_ONE_TO_ONE", "", "", "CLOSEST", "", "")
#    arcpy.MakeTableView_management(out_node, "Node_TV")
#    arcpy.AddJoin_management("Node_TV", "N", node_taz_sj, "N")
#    basename = arcpy.Describe("Node_TV").basename
#    joinbase = arcpy.Describe(node_taz_sj).basename
#    print("\nUpdating Highway Node TAZID...\n")
#    arcpy.CalculateField_management("Node_TV", "TAZID","calcTAZID(!"+joinbase+".TAZID_1!,!"+basename+".N!,"+str(UsedZones)+")", "PYTHON_9.3", fill_node)
#    arcpy.Delete_management("Node_TV")
    


def Main():
    try:
        print("\n\nRunning script...")
        print("Start Time: " + time.strftime('%X %x %Z')+"\n")
        TagLinksWithTAZID()
        #TagNodesWithTAZID()
        print("Script End Time: " + time.strftime('%X %x %Z'))
        logFile.write("All Finished"+"\n")
        logFile.write("Script End Time: " + time.strftime('%X %x %Z'))
        logFile.close()
    except:
        print("*** There was an error running this script - Check output logfile.")
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "\nPYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info())
        msgs = "\nGeopandas ERRORS:\n" + str(sys.exc_info()[1]) + "\n"
        logFile.write(pymsg + "\n")
        logFile.write(msgs + "\n")
        sys.exit(1)

Main()




