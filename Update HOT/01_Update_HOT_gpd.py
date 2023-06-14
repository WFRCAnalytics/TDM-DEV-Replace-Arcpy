# Author: Justin Culp coded and Andy Li added Toll zone functions -- Updated by Josh Reynolds and Chris Day
# Date: 12/06/2016 -- Updated 06/01/2023
#
# Description: This script makes a copy of the network links and creates midpoints from these links. The link midpoints are
#              then used to spatial join with the TAZ. The spatial join is then used to update the TAZID in the network links shapefile. Next
#              the network nodes are spatial joined with the TAZ, then the spatil join in used to update the TAZID in the network nodes shapefile.
# Requires: Geopandas
#
#

# open cmd in this folder and run this command: C:\Users\cday\Anaconda3\python.exe 01_Update_HOT_gpd.py
#C:\Users\cday\AppData\Local\ESRI\conda\envs\arcgispro-py3-geopandas\python.exe 01_Update_HOT_gpd.py

# Start Script
print("\nRunning Update HOTzone Python Script\n\n\n")

# Import geopandas module
print("Importing geopandas site package...\n")
import geopandas as gpd
import sys
import os
import time
import traceback
from pandas.api.types import is_numeric_dtype
import importlib.machinery

# Set file paths
print("\n\nDefining variables...\n")
#Pyth_root_dir = os.path.dirname(sys.argv[0])
#print("Python root directory: \n    " + Pyth_root_dir + "\n")
data = importlib.machinery.SourceFileLoader('data', r"_VARCUBE_UPDATEHOT.txt").load_module() #('data', os.path.join(Pyth_root_dir, r"_VarCube_UPDATEHOT.txt")).load_module()


# Print key variables to screen
print("tollz_shp: \n    "         + data.tollz_shp         + "\n")
print("Scenario_Link: \n    "     + data.Scenario_Link     + "\n")
print("Scenario_Node: \n    "     + data.Scenario_Node     + "\n")
print("UsedZones: \n    "         + str(data.UsedZones)    + "\n")
print("Temp Folder:  \n    "      + r'temp_gpd'            + "\n")  #data.temp_folder       + "\n")

# Open log file
temp_folder = r'temp_gpd' # delete in real script
#temp_folder      = str(data.temp_folder)
log = os.path.join(temp_folder,r'LogFile_UpdateHOT.txt')
logFile = open(log, 'w')
logFile.write(data.tollz_shp+'\n')
logFile.write(data.Scenario_Link+'\n')
logFile.write(data.Scenario_Node+'\n')
logFile.write(str(data.UsedZones)+'\n')
logFile.write(temp_folder+'\n')


# Define Variables ------------------------------------------------------------------------------------
# Variables: Input
tollz_shp         = str(data.tollz_shp)
link_shp          = str(data.Scenario_Link)
node_shp          = str(data.Scenario_Node)
UsedZones         = str(data.UsedZones)

# Variables: Intermediate
link_taz_sj       = os.path.join(temp_folder, "Link_TAZ_SJ_deleteTemp.shp")
node_taz_sj       = os.path.join(temp_folder, "Node_TAZ_SJ_deleteTemp.shp")

# Variables: Output
out_link         = os.path.join(temp_folder, "C1_Link_HOT.shp")
out_node         = os.path.join(temp_folder, "C1_Node_HOT.shp")
out_link_mp      = os.path.join(temp_folder, "C1_Link_Midponts.shp")


# Define Functions ------------------------------------------------------------------------------------
# Codeblock to calculate HOTzone node value
def calctollzoneID_Node(tazid, node, global_n):
    if node <= int(global_n):
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


# Geoprocessing steps ---------------------------------------------------------------------------------
try:
    print("\n\nRunning script...")
    print("Start Time: " + time.strftime('%X %x %Z')+"\n")

    # Tag Links With Toll Zone ID
    print("\n\nImporting Highway Link data...")
    gdf_link = gpd.read_file(link_shp)

    print("\nCalculating Highway Link midpoint coord and updating X_MID & Y_MID fields...")
    gdf_link["X_MID"] = gdf_link.geometry.interpolate(0.5, normalized=True).x
    gdf_link["Y_MID"] = gdf_link.geometry.interpolate(0.5, normalized=True).y

    print("\nMaking new point shapefile from Highway Link midpoint...")
    gdf_midpoints = gdf_link.copy()
    gdf_midpoints = gdf_midpoints.set_geometry(gdf_midpoints.geometry.centroid)
    gdf_midpoints = fill_na_sedf(gdf_midpoints)
    gdf_midpoints.to_file(out_link_mp)

    print("\nSpatial joining Tollz_shp to Link midpoints (this may take a few minutes)...")
    gdf_tollz = gpd.read_file(tollz_shp)
    gdf_link_taz_sj = gpd.sjoin(gdf_midpoints, gdf_tollz, how="left", op="within")
    gdf_link_taz_sj = fill_na_sedf(gdf_link_taz_sj)
    gdf_link_taz_sj.to_file(link_taz_sj)    

    print("\nUpdating Highway Link HOTZONE ID...\n")
    df_link_taz_sf = gdf_link_taz_sj[['LINKID','EL_Zone']]
    gdf_link_join = gdf_link.merge(df_link_taz_sf, how = 'left', on='LINKID')
    gdf_link_join["HOT_ZONEID"] = gdf_link_join["EL_Zone"]
    gdf_link_join = gdf_link_join.drop(columns='EL_Zone', axis=1)
    gdf_link_join = fill_na_sedf(gdf_link_join)
    gdf_link_join.to_file(out_link)


    # Tag Nodes With Toll Zone ID
    print("\n\nImporting Highway Node data for joining toll zone purpose..")
    gdf_node = gpd.read_file(node_shp)  

    print("\nSpatial joining Tollzone shape to Highway Nodes (this may take a few minutes)...")
    gdf_tollz = gpd.read_file(tollz_shp)
    gdf_node_tollz = gpd.sjoin(gdf_node,gdf_tollz, how="left", op="within") 

    print("\nUpdating Highway Node TollzoneID...\n")
    gdf_node_taz_sj = fill_na_sedf(gdf_node_tollz)
    gdf_node_taz_sj.to_file(node_taz_sj)    

    gdf_node_taz_hot = gdf_node_tollz.copy()
    gdf_node_taz_hot["HOT_ZONEID"] = gdf_node_taz_hot.apply(lambda row: calctollzoneID_Node(row["EL_Zone"], row["N"], UsedZones), axis=1) 
    gdf_node_taz_hot = gdf_node_taz_hot.drop(columns={'index_right','OBJECTID', 'Name', 'EL_Zone', 'Shape_Leng', 'Shape_Area'})
    gdf_node_taz_hot = fill_na_sedf(gdf_node_taz_hot)
    gdf_node_taz_hot.to_file(out_node) 

    # Finish Script
    print("Script End Time: " + time.strftime('%X %x %Z'))
    logFile.write("All Finished"+"\n")
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





