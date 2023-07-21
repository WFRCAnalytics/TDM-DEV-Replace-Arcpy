# Author: Justin Culp & Andy Li 
# Updated by Josh Reynolds & Chris Day
# Date Edited:        06/01/2023
#
# 
# Description: This script calculates the amount of walkable area within each TAZ to bus stops and bus lines
#
# Requires:    Geopandas, Pandas

print("\nRunning Create Walk Buffer Python Script\n\n\n") 

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
get_variables = os.path.join(Pyth_root_dir, r"_VarCube_WalkBuffer.txt")
print("Cube variables input file: \n    " + get_variables + "\n\n")

# Load file variables from input text file
data = importlib.machinery.SourceFileLoader('data', os.path.join(Pyth_root_dir, "_VarCube_WalkBuffer.txt")).load_module()

# Open and write to log file
log = os.path.join(Pyth_root_dir, "LogFile_WalkBuffer.txt")
logFile = open(log, 'w')
logFile.write(get_variables+'\n')
logFile.write(data.TAZ_shp+'\n')
logFile.write(data.Scenario_Link+'\n')
logFile.write(data.Scenario_Node+'\n\n')

print("TAZ_shp: \n    "           + data.TAZ_shp           + "\n")
print("Scenario_Link: \n    "     + data.Scenario_Link     + "\n")
print("Scenario_Node: \n    "     + data.Scenario_Node     + "\n")
print("Temp Folder:  \n    "      + data.temp_folder       + "\n")

## Define Variables
# Variables: Input
TAZ_shp           = str(data.TAZ_shp)
Scenario_Link     = str(data.Scenario_Link)
Scenario_Node     = str(data.Scenario_Node)
spatialRef        = 26912 #NAD_1983_UTM_Zone_12N

# Intermediate
delete_files = []

# Variables: Output
temp_folder       = str(data.temp_folder)
temp_taz = os.path.join(temp_folder, "Walk_Buffer_TAZ.shp")

def Main():
    try:
        print("\n\nRunning script...")
        print("Start Time: " + time.strftime('%X %x %Z')+"\n")

        #=================
        # makeTableView
        #=================
        
        print("makeTableView started: " + time.strftime('%X %x %Z')+"\n")
        taz_df = gpd.read_file(TAZ_shp)
        links_df = gpd.read_file(Scenario_Link)
        Local_Bus_Stops = gpd.read_file(Scenario_Node)

        #====================================
        # Create Local Bus Lines shapefile
        #====================================

        print("createBusLines started: " + time.strftime('%X %x %Z')+"\n")
        transit_links_df = gpd.read_file(os.path.join(temp_folder, "TransitLinks.dbf"))
        transit_links_df = transit_links_df[transit_links_df['MODE'] == 4].copy()

        transit_links_df['LINKID'] = transit_links_df['A'].astype(str) + '_' + transit_links_df['B'].astype(str)
        del transit_links_df['A']
        del transit_links_df['B']
        del transit_links_df['geometry']

        links_columns = list(links_df.columns)
        links_df = links_df.merge(transit_links_df, on='LINKID', how='inner')
        Local_Bus_Lines = links_df[links_df['FT']< 12].copy()
        Local_Bus_Lines = Local_Bus_Lines[links_columns].copy()
        Local_Bus_Lines = Local_Bus_Lines.set_crs(spatialRef)
        delete_files.append(transit_links_df)

        #=========================
        # Create Stops shapefile
        #=========================

        print("createBusStops started: " + time.strftime('%X %x %Z')+"\n")
        transit_links_df = gpd.read_file(os.path.join(temp_folder, "TransitLinks.dbf"))
        transit_links_df = transit_links_df[(transit_links_df['MODE'] > 4) & (transit_links_df['MODE'] <= 9)].copy()

        stop_a_max = transit_links_df.groupby('A', as_index=False)['STOPA'].max()
        stop_a_max.to_csv(os.path.join(temp_folder, "TEST_StopsA.csv"))
        stop_b_max = transit_links_df.groupby('B', as_index=False)['STOPB'].max()
        stop_b_max.to_csv(os.path.join(temp_folder, "TEST_StopsB.csv"))

        stop_a_max.rename({'STOPA':'MAX_STOPA'}, axis=1, inplace=True)
        stop_b_max.rename({'STOPB':'MAX_STOPB'}, axis=1, inplace=True)
        delete_files.append(stop_a_max)
        delete_files.append(stop_b_max)

        fieldnames = Local_Bus_Stops.columns

        if "TranStop" in fieldnames:
            print("TranStop field already exists in Node shapefile. Overwriting data...\n")
        else:
            Local_Bus_Stops['TranStop'] = np.nan

        Local_Bus_Stops = Local_Bus_Stops.merge(stop_a_max, left_on='N', right_on='A', how='left')
        Local_Bus_Stops = Local_Bus_Stops.merge(stop_b_max, left_on='N', right_on='B', how='left')

        Local_Bus_Stops.loc[Local_Bus_Stops['MAX_STOPB'] <= 0 ,'TranStop'] = 0
        Local_Bus_Stops.loc[Local_Bus_Stops['MAX_STOPA'] <= 0 ,'TranStop'] = 0
        Local_Bus_Stops.loc[Local_Bus_Stops['MAX_STOPB'] > 0 ,'TranStop'] = 1
        Local_Bus_Stops.loc[Local_Bus_Stops['MAX_STOPA'] > 0 ,'TranStop'] = 1
        

        Local_Bus_Stops = Local_Bus_Stops[Local_Bus_Stops['TranStop'] == 1].copy()
        Local_Bus_Stops = Local_Bus_Stops.set_crs(spatialRef)


        #=======================================================
        #  zeroFields - Add Fields in WalkBuffer.dbf to Update
        #=======================================================

        print ("zeroFields started: " + time.strftime('%X %x %Z')+"\n")
        fieldlist = ["TAZAREA", "LOCALAREA", "STOPSAREA", "LOCALPCT", "STOPSPCT", "WALKPCT"]
        # taz_df = gpd.read_file(temp_taz)
        taz_fields = list(taz_df.columns)
        for field in fieldlist:
                if field not in taz_fields:
                        taz_df[field] = 0

        taz_df['TAZAREA'] = taz_df['geometry'].area # calulates area in square meters as long as taz features are in utm

        #==========================
        # updateLinesArea
        #==========================

        # Select, Buffer, Intersect, Dissolve, Calculate Area, Summarize, and Update Local Area   
        print("updateLinesArea started: " + time.strftime('%X %x %Z')+"\n")  
        lbl_buffer = Local_Bus_Lines.drop(['TAZID'], axis=1)
        meters_to_buffer =  .4 * 1609.344 # 0.4-mile buffer
        lbl_buffer['geometry'] = lbl_buffer['geometry'].buffer(meters_to_buffer, join_style=1, cap_style=1)
        lbl_buffer = lbl_buffer.dissolve()
        lbl_buffer = lbl_buffer[['geometry']].copy()
        
        BusLines_TAZ_Intersect = lbl_buffer.overlay(taz_df, how='intersection')
        BusLines_Dissolve = BusLines_TAZ_Intersect.dissolve(by='TAZID')
        BusLines_Dissolve = BusLines_Dissolve[['geometry']].copy()

        BusLines_Area = BusLines_Dissolve.copy()
        BusLines_Area['F_AREA'] = BusLines_Area['geometry'].area

        BusLines_Max_Area = BusLines_Area.groupby('TAZID')[['F_AREA']].max().reset_index()
        BusLines_Max_Area.rename({'F_AREA':'MAX_F_AREA'}, axis=1, inplace=True)
        BusLines_Max_Area = BusLines_Dissolve.merge(BusLines_Max_Area, left_on='TAZID', right_on='TAZID', how='left')

        taz_df = taz_df.merge(BusLines_Max_Area.drop(['geometry'], axis=1), left_on='TAZID', right_on='TAZID', how='left')
        taz_df.loc[taz_df['MAX_F_AREA'] > 0 ,'LOCALAREA'] = taz_df['MAX_F_AREA']
        taz_df.loc[taz_df['MAX_F_AREA'] <= 0 ,'LOCALAREA'] = taz_df['LOCALAREA']
        del taz_df['MAX_F_AREA']

        lbl_buffer.to_file(os.path.join(temp_folder, "wb_elseBusLines_Buffer.shp"))
        BusLines_TAZ_Intersect.to_file(os.path.join(temp_folder, "wb_BusLines_TAZ_Intersect.shp"))
        BusLines_Dissolve.to_file(os.path.join(temp_folder, "wb_BusLines_Dissolve.shp"))
        BusLines_Area.to_file(os.path.join(temp_folder, "wb_BusLines_Area.shp"))

        delete_files.append(lbl_buffer)
        delete_files.append(BusLines_TAZ_Intersect)
        delete_files.append(BusLines_Dissolve)
        delete_files.append(BusLines_Area)
        delete_files.append(BusLines_Max_Area)
        print("Updated Local Area"+"\n")

        #==================
        # updateStopsArea
        #==================

        # Buffer, Intersect, Dissolve, Calculate Area, Summarize, and Update Stops Area
        print("updateStopsArea started: " + time.strftime('%X %x %Z')+"\n")    
        lbs_buffer = Local_Bus_Stops.drop(['TAZID'], axis=1)
        meters_to_buffer =  .4 * 1609.344 # 0.4-mile buffer
        lbs_buffer['geometry'] = lbs_buffer['geometry'].buffer(meters_to_buffer, join_style=1, cap_style=1)
        lbs_buffer = lbs_buffer.dissolve()
        lbs_buffer = lbs_buffer[['geometry']].copy()

        BusStops_TAZ_Intersect = lbs_buffer.overlay(taz_df, how='intersection')
        BusStops_Dissolve = BusStops_TAZ_Intersect.dissolve(by='TAZID')
        BusStops_Dissolve = BusStops_Dissolve[['geometry']].copy()
        
        BusStops_Area = BusStops_Dissolve.copy()
        BusStops_Area['F_AREA'] = BusStops_Area['geometry'].area

        BusStops_Max_Area = BusStops_Area.groupby('TAZID')[['F_AREA']].max().reset_index()
        BusStops_Max_Area.rename({'F_AREA':'MAX_F_AREA'}, axis=1, inplace=True)
        BusStops_Max_Area = BusStops_Dissolve.merge(BusStops_Max_Area, left_on='TAZID', right_on='TAZID', how='left')

        taz_df= taz_df.merge(BusStops_Max_Area.drop(['geometry'], axis=1), left_on='TAZID', right_on='TAZID', how='left')
        taz_df.loc[taz_df['MAX_F_AREA'] > 0 ,'STOPSAREA'] = taz_df['MAX_F_AREA']
        taz_df.loc[taz_df['MAX_F_AREA'] <= 0 ,'STOPSAREA'] = taz_df['STOPSAREA']
        del taz_df['MAX_F_AREA']

        lbs_buffer.to_file(os.path.join(temp_folder, "wb_BusStops_Buffer.shp"))
        BusStops_TAZ_Intersect.to_file(os.path.join(temp_folder, "wb_BusStops_TAZ_Intersect.shp"))
        BusStops_Dissolve.to_file(os.path.join(temp_folder, "wb_BusStops_Dissolve.shp"))
        BusStops_Area.to_file(os.path.join(temp_folder, "wb_BusStops_Area.shp"))
        
        delete_files.append(lbs_buffer)
        delete_files.append(BusStops_TAZ_Intersect)
        delete_files.append(BusStops_Dissolve)
        delete_files.append(BusStops_Area)
        delete_files.append(BusStops_Max_Area) 
        print("Updated Stops Area"+"\n")

        #===========================
        # updatePercentages
        #===========================

        # Update Local, Stops, and Walk Percentages
        print("updatePercentages started: " + time.strftime('%X %x %Z')+"\n" ) 
        taz_df.loc[(taz_df['TAZAREA'] == 0) | (taz_df['TAZAREA'].isna == True), 'LOCALPCT'] = 0
        taz_df.loc[(taz_df['TAZAREA'] == 0) | (taz_df['TAZAREA'].isna == True), 'STOPSPCT'] = 0

        taz_df.loc[(taz_df['TAZAREA'] > 0), 'LOCALPCT'] = (taz_df['LOCALAREA'] / taz_df['TAZAREA']) * 100
        taz_df.loc[(taz_df['TAZAREA'] > 0), 'STOPSPCT'] = (taz_df['STOPSAREA'] / taz_df['TAZAREA']) * 100

        taz_df.loc[(taz_df['LOCALPCT'] > taz_df['STOPSPCT'] ), 'WALKPCT'] = taz_df['LOCALPCT']
        taz_df.loc[(taz_df['LOCALPCT'] <= taz_df['STOPSPCT'] ), 'WALKPCT'] = taz_df['STOPSPCT']

        #================
        # overWriteZones
        #================

        # Overwrite Calculation with Special Zones (100 Percent Accessible)
        print("overWriteZones started: " + time.strftime('%X %x %Z')+"\n")
        taz_df.loc[taz_df['WALK100'] > 0 ,'WALKPCT'] = taz_df['WALK100']
        taz_df.loc[taz_df['WALK100'] <= 0 ,'WALKPCT'] = taz_df['WALKPCT']
        print("Updated Percentages"+"\n")
        
        #=====================
        # DeleteIntermediate
        #=====================

        for file in delete_files:
            try:
                del file
            except:
                 pass

        taz_df.to_file(os.path.join(temp_folder, "Walk_Buffer_TAZ.shp"))
        Local_Bus_Lines.to_file(os.path.join(temp_folder, "wb_LocalBus.shp"))
        Local_Bus_Stops.to_file(os.path.join(temp_folder, "wb_Stops.shp"))
        del taz_df

        print ("All Finished"+"\n")
        print ("Script End Time: " + time.strftime('%X %x %Z'))
        logFile.write("All Finished"+"\n")
        logFile.write("Script End Time: " + time.strftime('%X %x %Z'))
        logFile.close()

    except:
        print("*** There was an error running this script - Check output logfile.")
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "\nPYTHON ERRORS:\nTraceback info:\n"+tbinfo+"\nError Info:\n"+str(sys.exc_info())
        logFile.write(""+pymsg+"\n")
        logFile.close()
        sys.exit(1)

Main()
