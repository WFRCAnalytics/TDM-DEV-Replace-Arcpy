# Author: Justin Culp & Andy Li 
# Updated by Josh Reynolds & Chris Day
# Date Edited:        07/01/2023
#
# Description: This script makes a copy of the network links and creates midpoints from these links. The link midpoints are
#              then used to spatial join with the TAZ. The spatial join is then used to update the TAZID in the network links shapefile. Next
#              the network nodes are spatial joined with the TAZ, then the spatil join in used to update the TAZID in the network nodes shapefile.

# Requires:    Geopandas, Pandas

#C:\Users\cday\AppData\Local\ESRI\conda\envs\arcgispro-py3-geopandas\python.exe 01_Update_Link_Node_TAZID_gpd.py

print("\nRunning Update Link Node TAZID Python Script\n\n\n")

import sys, os, imp, time, traceback
import pandas as pd
import geopandas as gpd
import numpy as np
import importlib.machinery

# Set file paths
Pyth_root_dir = os.path.dirname(sys.argv[0])
print("\n\nDefining variables...\n")
print("Python root directory: \n    " + Pyth_root_dir + "\n")

# Get input variables from Cube
get_variables = os.path.join(Pyth_root_dir, r"_VARCUBE_UPDATETAZID.txt")
print("Cube variables input file: \n    " + get_variables + "\n\n")

# Load file variables from input text file
data = importlib.machinery.SourceFileLoader('data', os.path.join(Pyth_root_dir, r"_VARCUBE_UPDATETAZID.txt")).load_module()

# Open and write to log file
log = os.path.join(Pyth_root_dir, "LogFile_UpdateLinkNodeTAZID.txt")
logFile = open(log, 'w')
logFile.write(data.TAZ_shp +'\n')
logFile.write(data.Scenario_Link+'\n')
logFile.write(data.Scenario_Node+'\n')
logFile.write(str(data.UsedZones)+'\n')

print("TAZ_shp: \n    "           + data.TAZ_shp           + "\n")
print("Scenario_Link: \n    "     + data.Scenario_Link     + "\n")
print("Scenario_Node: \n    "     + data.Scenario_Node     + "\n")
print("UsedZones: \n    "         + str(data.UsedZones)    + "\n")
print("Temp Folder:  \n    "      + data.temp_folder       + "\n")

## Define Variables
# Variables: Input
taz_shp           = str(data.TAZ_shp)
link_shp          = str(data.Scenario_Link)
node_shp          = str(data.Scenario_Node)
UsedZones         = str(data.UsedZones)
temp_folder       = str(data.temp_folder)

# Variables: Output
out_link          = os.path.join(temp_folder, "C1_Link_TAZID.csv")
out_node          = os.path.join(temp_folder, "C1_Node_TAZID.csv")


# Codeblocks to calculate TAZID
def calcTAZID_Node(tazid, node, global_n):
  if node <= int(global_n):
    return node
  else:
    return tazid
  
def calcTAZID_Link(tazid, aField, bField, global_n):
    if int(aField) <= int(global_n):
        return aField
    elif int(bField) <= int(global_n):
        return bField
    else:
        return tazid
    
def Main():
    try:
        print("\n\nRunning script...")
        starttime = time.strftime('%X %x %Z')
        print("Start Time: " + time.strftime('%X %x %Z')+"\n")

        #=====================
        #Tag Links with TAZID
        #=====================

        print("\n\nImporting Highway Link data...")
        gdf_link = gpd.read_file(link_shp)

        print("\nCalculating Highway Link distance (in miles) and updating DISTANCE field...")
        gdf_link["DISTANCE"] = gdf_link.geometry.length / 1609.34

        print("\nCalculating Highway Link midpoint coord and updating X_MID & Y_MID fields...")
        gdf_link["X_MID"] = gdf_link.geometry.interpolate(0.5, normalized=True).x
        gdf_link["Y_MID"] = gdf_link.geometry.interpolate(0.5, normalized=True).y

        print("\nMaking new point shapefile from Highway Link midpoint...")
        gdf_midpoints = gdf_link.copy()
        gdf_midpoints = gdf_midpoints.set_geometry(gdf_midpoints.geometry.centroid)

        print("\nSpatial joining TAZ to Link midpoints (this may take a few minutes)...")
        # read in taz shapefile and calculate which tazes are closest to each midpoint value
        gdf_taz = gpd.read_file(taz_shp)
        gdf_nearest = gpd.sjoin_nearest(gdf_midpoints,gdf_taz, distance_col = 'nearest_dist')

        #drop duplicates where tazes are equidistant from the link midpoint by keeping the first occurence
        second_occurences = gdf_nearest['LINKID'].duplicated(keep='first')
        gdf_nearest_final = gdf_nearest[~second_occurences]
        gdf_link_taz_sj = gdf_nearest_final.rename(columns={'TAZID_left':'TAZID','TAZID_right':'TAZID_1'})

        drop_columns = ['TAZID_V832', 'SORT', 'CO_IDX', 'CO_TAZID', 'SUBAREAID', 'ACRES', 'DEVACRES', 'DEVPBLEPCT', 'X', 'Y', 'ADJ_XY', 'CO_FIPS', 'CO_NAME', 'CITY_FIPS', 'CITY_UGRC', 'CITY_NAME', 'DISTSUPER', 'DSUP_NAME', 'DISTLRG', 'DLRG_NAME', 'DISTMED', 'DMED_NAME', 'DISTSML', 'DSML_NAME', 'CBD', 'TERMTIME', 'PRKCSTPERM', 'PRKCSTTEMP', 'WALK100', 'ECOEDPASS', 'FREEFARE', 'REMM']

        print("\nUpdating Highway Link TAZID...\n")
        gdf_link_mp = gdf_link_taz_sj.copy()
        gdf_link_mp["TAZID"] = gdf_link_mp.apply(lambda row: calcTAZID_Link(row["TAZID_1"], row["A"], row["B"], UsedZones), axis=1)
        gdf_link_mp = gdf_link_mp.drop(columns=drop_columns).drop(columns={'nearest_dist','TAZID_1'})
        gdf_link_mp = gdf_link_mp.sort_values(by='LINKID', ascending=True)
        gdf_link_mp = gdf_link_mp.rename(columns={'A':';A'})
        gdf_link_mp = gdf_link_mp[[';A','B','LINKID','DISTANCE','TAZID','geometry']]

        df_link_mp = pd.DataFrame(gdf_link_mp.drop(columns='geometry'))
        df_link_mp.to_csv(out_link, index=False)

        #=====================
        #Tag Nodes with TAZID
        #=====================

        print("\n\nImporting Highway Node data...")
        gdf_nodes = gpd.read_file(node_shp)

        print("\nSpatial joining TAZ to Highway Nodes (this may take a few minutes)...")
        # read in taz shapefile and calculate which tazes are closest to each midpoint value
        gdf_taz = gpd.read_file(taz_shp)
        gdf_nodes_nearest_taz = gpd.sjoin_nearest(gdf_nodes,gdf_taz, distance_col = 'nearest_dist')

        #drop duplicates where tazes are equidistant from the link midpoint by keeping the first occurence
        second_node_occurences = gdf_nodes_nearest_taz['N'].duplicated(keep='first')
        gdf_node_nearest_final = gdf_nodes_nearest_taz[~second_node_occurences]
        gdf_node_taz_sj = gdf_node_nearest_final.rename(columns={'X_left':'X','Y_left':'Y','TAZID_left':'TAZID','TAZID_right':'TAZID_1','X_right':'X_1','Y_right':'Y_1'})
        gdf_node_taz_sj = gdf_node_taz_sj.drop(columns={'nearest_dist'})

        print("\nUpdating Highway Node TAZID...\n")
        gdf_node_mp = gdf_node_taz_sj.copy()
        gdf_node_mp['TAZID'] = gdf_node_mp.apply(lambda row: calcTAZID_Node(row['TAZID_1'], row['N'], UsedZones), axis = 1)
        gdf_node_mp = gdf_node_mp.iloc[:,:43]
        gdf_node_mp = gdf_node_mp.rename(columns={'N':';N'})
        gdf_node_mp = gdf_node_mp[[';N','X','Y','TAZID','geometry']]

        #save output as csv
        df_node_mp = pd.DataFrame(gdf_node_mp.drop(columns='geometry'))
        df_node_mp.to_csv(out_node, index=False)

        #===============
        # Finish Script
        #===============

        print("Script End Time: " + time.strftime('%X %x %Z'))
        logFile.write("All Finished"+"\n")
        logFile.write("Script Start Time: " + starttime +"\n")
        logFile.write("Script End Time: " + time.strftime('%X %x %Z'))
        logFile.close()

    except:
        # Error Code if something doesn't work
        print("*** There was an error running this script - Check output logfile.")
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "\nPYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info())
        msgs = "\nGeopandas ERRORS:\n" + str(sys.exc_info()[1]) + "\n"
        logFile.write(pymsg + "\n")
        logFile.write(msgs + "\n")
        sys.exit(1)

Main()