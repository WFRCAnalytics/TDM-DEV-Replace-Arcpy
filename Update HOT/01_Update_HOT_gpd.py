# Author: Justin Culp & Andy Li 
# Updated by Josh Reynolds & Chris Day
# Date Edited:        06/01/2023
#
# Description: This script makes a copy of the network links and creates midpoints from these links. The link midpoints are
#              then used to spatial join with the TAZ. The spatial join is then used to update the TAZID in the network links shapefile. Next
#              the network nodes are spatial joined with the TAZ, then the spatil join in used to update the TAZID in the network nodes shapefile.
#
# Requires:    Geopandas, Pandas

#C:\Users\cday\AppData\Local\ESRI\conda\envs\arcgispro-py3-geopandas\python.exe 01_Update_HOT_gpd.py

print("\nRunning Update HOTzone Python Script\n\n\n")

import sys, os, imp, time, traceback
import geopandas as gpd
import pandas as pd
from pandas.api.types import is_numeric_dtype
import importlib.machinery

# Set file paths
Pyth_root_dir = os.path.dirname(sys.argv[0])
print("\n\nDefining variables...\n")
print("Python root directory: \n    " + Pyth_root_dir + "\n")

# Get input variables from Cube
get_variables = os.path.join(Pyth_root_dir, r"_VarCube_UPDATEHOT.txt")
print("Cube variables input file: \n    " + get_variables + "\n\n")

# Load file variables from input text file
data = importlib.machinery.SourceFileLoader('data', os.path.join(Pyth_root_dir, r"_VarCube_UPDATEHOT.txt")).load_module()

# Open and write to log file
log = os.path.join(Pyth_root_dir, "LogFile_UPDATEHOT.txt")
logFile = open(log, 'w')
logFile.write(data.tollz_shp+'\n')
logFile.write(data.Scenario_Link+'\n')
logFile.write(data.Scenario_Node+'\n')
logFile.write(str(data.UsedZones)+'\n')

print("tollz_shp: \n    "         + data.tollz_shp         + "\n")
print("Scenario_Link: \n    "     + data.Scenario_Link     + "\n")
print("Scenario_Node: \n    "     + data.Scenario_Node     + "\n")
print("UsedZones: \n    "         + str(data.UsedZones)    + "\n")
print("Temp Folder:  \n    "      + data.temp_folder       + "\n")

## Define Variables 
# Variables: Input
tollz_shp         = str(data.tollz_shp)
link_shp          = str(data.Scenario_Link)
node_shp          = str(data.Scenario_Node)
UsedZones         = str(data.UsedZones)
temp_folder       = str(data.temp_folder)

# Variables: Output
out_link         = os.path.join(temp_folder, "C1_Link_HOT.csv")
out_node         = os.path.join(temp_folder, "C1_Node_HOT.csv")


# Codeblock to calculate HOTzone node value
def calctollzoneID_Node(tazid, node, global_n):
    if int(node) <= int(global_n):
        return 0
    else:
        return tazid
    
# Fill NA values in Spatially enabled dataframes (ignores geometry column)
def fill_na_sedf(df_with_shape_column):
    if 'geometry' in df_with_shape_column.columns:
        df = df_with_shape_column.copy()
        shape_column = df['geometry'].copy()
        del df['geometry']

        # Apply fillna based on column types
        for column in df.columns:
            if is_numeric_dtype(df[column]):
                df[column] = df[column].fillna(0)
            else:
                df[column] = df[column].fillna('')

        gdf = gpd.GeoDataFrame(df)
        gdf = gdf.set_geometry(shape_column)
        gdf.crs = shape_column.crs  # Set CRS from shape column
        return gdf
    else:
        raise Exception("Dataframe does not include 'geometry' column")


def Main():
    try:
        print("\n\nRunning script...")
        starttime = time.strftime('%X %x %Z')
        print("Start Time: " + time.strftime('%X %x %Z')+"\n")

        #=============================
        # Tag Links With Toll Zone ID
        #=============================

        print("\n\nImporting Highway Link data...")
        gdf_link = gpd.read_file(link_shp)

        print("\nCalculating Highway Link midpoint coord and updating X_MID & Y_MID fields...")
        gdf_link["X_MID"] = gdf_link.geometry.interpolate(0.5, normalized=True).x
        gdf_link["Y_MID"] = gdf_link.geometry.interpolate(0.5, normalized=True).y

        print("\nMaking new point shapefile from Highway Link midpoint...")
        gdf_midpoints = gdf_link.copy()
        gdf_midpoints = gdf_midpoints.set_geometry(gdf_midpoints.geometry.centroid)
        gdf_midpoints = fill_na_sedf(gdf_midpoints)

        print("\nSpatial joining Tollz_shp to Link midpoints (this may take a few minutes)...")
        gdf_tollz = gpd.read_file(tollz_shp)
        gdf_link_taz_sj = gpd.sjoin(gdf_midpoints, gdf_tollz, how="left", op="within")
        gdf_link_taz_sj = fill_na_sedf(gdf_link_taz_sj)

        print("\nUpdating Highway Link HOTZONE ID...\n")
        df_link_taz_sf = gdf_link_taz_sj[['LINKID','EL_Zone']]
        gdf_link_join = gdf_link.merge(df_link_taz_sf, how = 'left', on='LINKID')
        gdf_link_join["HOT_ZONEID"] = gdf_link_join["EL_Zone"]
        gdf_link_join = gdf_link_join.drop(columns='EL_Zone', axis=1)
        gdf_link_join = fill_na_sedf(gdf_link_join)
        gdf_link_join = gdf_link_join[['A','B','LINKID','HOT_ZONEID', 'geometry']]

        #save output as csv
        df_link_join = pd.DataFrame(gdf_link_join.drop(columns='geometry'))
        df_link_join.to_csv(out_link, index=False)

        #===============================
        # Tag Nodes With Toll Zone ID
        #===============================

        print("\n\nImporting Highway Node data for joining toll zone purpose..")
        gdf_node = gpd.read_file(node_shp)  

        print("\nSpatial joining Tollzone shape to Highway Nodes (this may take a few minutes)...")
        gdf_tollz = gpd.read_file(tollz_shp)
        gdf_node_tollz = gpd.sjoin(gdf_node,gdf_tollz, how="left", op="within") 

        print("\nUpdating Highway Node TollzoneID...\n")
        gdf_node_taz_hot = gdf_node_tollz.copy()
        gdf_node_taz_hot["HOT_ZONEID"] = gdf_node_taz_hot.apply(lambda row: calctollzoneID_Node(row["EL_Zone"], row["N"], UsedZones), axis=1) 
        gdf_node_taz_hot = gdf_node_taz_hot.drop(columns={'index_right','OBJECTID', 'Name', 'EL_Zone', 'Shape_Leng', 'Shape_Area'})
        gdf_node_taz_hot = fill_na_sedf(gdf_node_taz_hot)
        gdf_node_taz_hot = gdf_node_taz_hot[['N','X','Y','HOT_ZONEID', 'geometry']]

        #save output as csv
        df_node_join = pd.DataFrame(gdf_node_taz_hot.drop(columns='geometry'))
        df_node_join.to_csv(out_node, index=False)

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




