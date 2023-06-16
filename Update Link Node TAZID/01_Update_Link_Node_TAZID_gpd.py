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
import numpy as np
from shapely.geometry import box
import pandas as pd

TAZ_shp = r'inputs-04-14\\TAZ.shp'
Scenario_Link = r'inputs-04-14\\C1_Link.shp'
Scenario_Node = r'inputs-04-14\\C1_Node.shp'
UsedZones = '3629'
temp_folder = r'temp_gpd2'
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

    
def find_nearest_polygon(point_gdf, polygon_gdf,buffer_distance):
    point_gdf2 = point_gdf.copy()
    # Create a spatial index for the polygon geometries
    polygon_sindex = polygon_gdf.sindex
    
    nearest_tazid = []
    for point in point_gdf2.geometry:
        # Get the indices of candidate polygons based on the point's bounding box
        point_buffer = point.buffer(buffer_distance)
        expanded_bounds = box(*point_buffer.bounds)
        potential_nearest_idx = list(polygon_sindex.intersection(expanded_bounds.bounds))
        
        if len(potential_nearest_idx) > 0:
            # Calculate distances only for the potential candidate polygons
            distances = polygon_gdf.geometry.iloc[potential_nearest_idx].distance(point)
            
            # Find the index of the polygon with the minimum distance
            nearest_idx = distances.idxmin()
            
            # Retrieve the corresponding 'TAZID' value
            nearest_tazid.append(polygon_gdf.loc[nearest_idx, 'TAZID'])
        else:
            # Handle the case when there are no candidate polygons
            nearest_tazid.append(None)
            print('No TAZ polygon close enough to this link midpoint. Increase buffer size in code.')
    
    point_gdf2['nearest_tazid'] = nearest_tazid
    return point_gdf2

# Geoprocessing steps
def TagLinksWithTAZID():
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
    gdf_midpoints.to_file(out_link_mp)

    print("\nSpatial joining TAZ to Link midpoints (this may take a few minutes)...")
    # read in taz shapefile and calculate which tazes are closest to each midpoint value
    gdf_taz = gpd.read_file(taz_shp)
    gdf_midpoints_nearest_taz = find_nearest_polygon(gdf_midpoints,gdf_taz,1000)
    gdf_midpoints_nearest_taz = gdf_midpoints_nearest_taz[['LINKID','nearest_tazid']]

    drop_columns = ['TAZID_V832', 'SORT', 'CO_IDX', 'CO_TAZID', 'SUBAREAID', 'ACRES', 'DEVACRES', 'DEVPBLEPCT', 'X', 'Y', 'ADJ_XY', 'CO_FIPS', 'CO_NAME', 'CITY_FIPS', 'CITY_UGRC', 'CITY_NAME', 'DISTSUPER', 'DSUP_NAME', 'DISTLRG', 'DLRG_NAME', 'DISTMED', 'DMED_NAME', 'DISTSML', 'DSML_NAME', 'CBD', 'TERMTIME', 'PRKCSTPERM', 'PRKCSTTEMP', 'WALK100', 'ECOEDPASS', 'FREEFARE', 'REMM']

    # get the tazid for all those midpoints that exist within a tazid
    gdf_link_taz_sj = gpd.sjoin(gdf_midpoints, gdf_taz, how="left", op="within")
    gdf_link_taz_sj = gdf_link_taz_sj.rename(columns={'TAZID_left':'TAZID','TAZID_right':'TAZID_1'})
    gdf_link_taz_sj = gdf_link_taz_sj.drop(columns=drop_columns)

    # update TAZID_1 to be the value of the nearest tazid to the midpoint for those midpoints that don't exist within a taz polygon
    gdf_link_taz_sj_F = gdf_link_taz_sj.merge(gdf_midpoints_nearest_taz, on = 'LINKID', how = 'left')
    gdf_link_taz_sj_F['TAZID_1'] = np.where(gdf_link_taz_sj_F['TAZID_1'].isna(), gdf_link_taz_sj_F['nearest_tazid'], gdf_link_taz_sj_F['TAZID_1'])

    # get missing column data from taz dataframe
    df_taz = pd.DataFrame(gdf_taz).drop(columns={'geometry'})
    gdf_link_taz_sj_F = gdf_link_taz_sj_F.merge(df_taz, left_on='TAZID_1',right_on='TAZID', how='left')
    gdf_link_taz_sj_F = gdf_link_taz_sj_F.rename(columns={'TAZID_x':'TAZID'}).drop(columns={'TAZID_y'})
    gdf_link_taz_sj_F.to_file(link_taz_sj)

    print("\nUpdating Highway Link TAZID...\n")
    gdf_link_mp = gdf_link_taz_sj_F.copy()
    gdf_link_mp["TAZID"] = gdf_link_mp.apply(lambda row: calcTAZID_Link(row["TAZID_1"], row["A"], row["B"], UsedZones), axis=1)
    gdf_link_mp = gdf_link_mp.drop(columns=drop_columns).drop(columns={'nearest_tazid','TAZID_1'})
    gdf_link_mp.to_file(out_link)

def TagNodesWithTAZID():
    print("\n\nImporting Highway Node data...")
    gdf_nodes = gpd.read_file(node_shp)

    print("\nSpatial joining TAZ to Highway Nodes (this may take a few minutes)...")
    gdf_taz = gpd.read_file(taz_shp)
    gdf_nodes_nearest_taz = find_nearest_polygon(gdf_nodes,gdf_taz,1000)

    # convert taz geodataframe to regular dataframe
    df_taz = pd.DataFrame(gdf_taz).drop(columns={'geometry'}).rename(columns={'X':'X_1','Y':'Y_1', 'TAZID':'TAZID_1'})
    gdf_node_taz_sj = gdf_nodes_nearest_taz.merge(df_taz, left_on='nearest_tazid',right_on='TAZID_1', how='left')
    gdf_node_taz_sj = gdf_node_taz_sj.drop(columns={'nearest_tazid'})
    gdf_node_taz_sj.to_file(node_taz_sj)
     
    print("\nUpdating Highway Node TAZID...\n")
    gdf_node_mp = gdf_nodes_nearest_taz.copy()
    gdf_node_mp['TAZID'] = gdf_node_mp.apply(lambda row: calcTAZID_Node(row['nearest_tazid'], row['N'], UsedZones), axis = 1)
    gdf_node_mp = gdf_node_mp.drop(columns={'nearest_tazid'})
    gdf_node_mp.to_file(out_node)
    


def Main():
    try:
        print("\n\nRunning script...")
        print("Start Time: " + time.strftime('%X %x %Z')+"\n")
        #TagLinksWithTAZID()
        TagNodesWithTAZID()
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




