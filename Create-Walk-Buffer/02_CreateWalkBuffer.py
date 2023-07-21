# Edited:      Justin Culp
# Date:        06/02/2017
#
# Description: 
#
# Requires:    ArcGIS 10.2 Desktop Basic


# Import arcpy site package, sys, and os
print "\nRunning Create Walk Buffer Python Script\n\n\n" 
print "Importing arcpy site package...\n" 
import arcpy, sys, os, imp, time, traceback

# Set workspace environment
from arcpy import env
env.overwriteOutput = True

# Set file paths
Pyth_root_dir = os.path.dirname(sys.argv[0])
print "\n\nDefining variables...\n"
print "Python root directory: \n    " + Pyth_root_dir + "\n"

# Get input variables from Cube
get_variables = os.path.join(Pyth_root_dir, r"_VarCube_WalkBuffer.txt")
print "Cube variables input file: \n    " + get_variables + "\n\n"

# Load file variables from input text file
f = open(get_variables, 'r')
global data
data = imp.load_source('data', '', f)
f.close()

# Open and write to log file
log = os.path.join(Pyth_root_dir, "LogFile_WalkBuffer.txt")
logFile = open(log, 'w')
logFile.write(get_variables+'\n')
logFile.write(data.TAZ_shp+'\n')
logFile.write(data.Scenario_Link+'\n')
logFile.write(data.Scenario_Node+'\n\n')

print "TAZ_shp: \n    "           + data.TAZ_shp           + "\n"
print "Scenario_Link: \n    "     + data.Scenario_Link     + "\n"
print "Scenario_Node: \n    "     + data.Scenario_Node     + "\n"
print "Temp Folder:  \n    "      + data.temp_folder       + "\n"

#raw_input()


## Define Variables
# Variables: Input
TAZ_shp           = str(data.TAZ_shp)
Scenario_Link     = str(data.Scenario_Link)
Scenario_Node     = str(data.Scenario_Node)
#Transit_Links     =   #     str(data.Transit_Links_dbf)  #r"C:\_Projects\Summit\Summit v2 - 2017-05-23b\Scenarios\BY_2015\Temp\0_InputProcessing\TransitLinks.dbf"
spatialRef        = 26912 #NAD_1983_UTM_Zone_12N

# Intermediate
phi = "_DeleteTemp"
deletefiles = []
TAZ_FL          = r"in_memory\TAZ_WalkBuffer_FL"
All_Tran_Lines  = r"in_memory\AllTransitLines"
Local_Bus_Lines = r"in_memory\BusLines"
Local_Bus_Stops = r"in_memory\LineStops"
Link_View       = r"in_memory\Link_View"
Node_View       = r"in_memory\Node_View"

# Variables: Output
temp_folder       = str(data.temp_folder)
temp_taz = os.path.join(temp_folder, "Walk_Buffer_TAZ.shp")
arcpy.Select_analysis(TAZ_shp, temp_taz)

## Subroutines
create_link_ID = "str(!A!) + '_' + str(!B!)"

stops_codeblock = """def calcStops(field):
    if field > 0:
        return 1
    else:
        return 0"""
        
area_codeblock = """def calcArea(field, value):
    if value > 0:
        return value
    else:
        return field"""

def DeleteIntermediate():
    for file in deletefiles:
        if arcpy.Exists(file):
            arcpy.Delete_management(file)


## Geoprocessing Functions
# Make Table Views
def makeTableView():
    print "makeTableView started: " + time.strftime('%X %x %Z')+"\n"
    arcpy.MakeFeatureLayer_management(temp_taz, TAZ_FL)
    arcpy.MakeFeatureLayer_management(Scenario_Link, Link_View)
    arcpy.MakeFeatureLayer_management(Scenario_Node, Node_View)

# Create Local Bus Lines shapefile
def createBusLines():
    print "createBusLines started: " + time.strftime('%X %x %Z')+"\n"
    arcpy.TableSelect_analysis(os.path.join(temp_folder, "TransitLinks.dbf"), "in_memory/Table_Select", '"MODE"=4')     # Change input .dbf and add query for local bus '"MODE" = 4'
    arcpy.AddField_management("in_memory/Table_Select", "LINKID", "TEXT", 16)
    arcpy.CalculateField_management("in_memory/Table_Select",
                                    "LINKID",
                                    create_link_ID,
                                    "PYTHON_9.3")
    arcpy.AddJoin_management(Link_View, "LINKID", "in_memory/Table_Select", "LINKID", "KEEP_COMMON")
    arcpy.Select_analysis(Link_View, Local_Bus_Lines, "FT<12")
    arcpy.RemoveJoin_management(Link_View, "")
    arcpy.DefineProjection_management(Local_Bus_Lines, spatialRef) 
    deletefiles.append("in_memory/Table_Select")

# Create Stops shapefile
def createBusStops():
    print "createBusStops started: " + time.strftime('%X %x %Z')+"\n"
    arcpy.TableSelect_analysis(os.path.join(temp_folder, "TransitLinks.dbf"), "in_memory/Stops_Select", '"MODE">4 AND "MODE"<=9')  # Add query for stops '"MODE">=4 AND "MODE"<=9' modified >4
    deletefiles.append("in_memory/Stops_Select")
    arcpy.Statistics_analysis("in_memory/Stops_Select", "in_memory/StopAStats", [["STOPA", "MAX"]], "A")
    deletefiles.append("in_memory/StopAStats")
    arcpy.Statistics_analysis("in_memory/Stops_Select", "in_memory/StopBStats", [["STOPB", "MAX"]], "B")
    deletefiles.append("in_memory/StopBStats")

    fieldnames = [field.name for field in arcpy.ListFields(Node_View)]
    if "TranStop" in fieldnames:
        print "TranStop field already exists in Node shapefile.  Overwriting data...\n"
    #try:
    else:
        arcpy.AddField_management(Node_View, "TranStop", "SHORT", 1)
    #except Exception as e:
    #    print(e)
    #    sys.exit("Couldn't add the 'TranStop' Field to the Scenario Node Network. This probably means that you need to rerun _1CreateTransitDBF.s")
    
    arcpy.AddJoin_management(Node_View, "N", "in_memory/StopAStats", "A", "KEEP_COMMON")
    arcpy.CalculateField_management(Node_View, 
                                    "TranStop",
                                    "calcStops(!"+"StopAStats"+"."+"MAX_STOPA"+"!)",
                                    "PYTHON_9.3",
                                    stops_codeblock)
    arcpy.RemoveJoin_management(Node_View, "")
    arcpy.AddJoin_management(Node_View, "N", "in_memory/StopBStats", "B", "KEEP_COMMON")
    arcpy.CalculateField_management(Node_View,
                                    "TranStop",
                                    "calcStops(!"+"StopBStats"+"."+"MAX_STOPB"+"!)",
                                    "PYTHON_9.3",
                                    stops_codeblock)
    arcpy.RemoveJoin_management(Node_View, "")
    arcpy.Select_analysis(Node_View, Local_Bus_Stops, "\"TranStop\" = 1")
    arcpy.DefineProjection_management(Local_Bus_Stops, spatialRef)


# Add Fields in WalkBuffer.dbf to Update
def zeroFields():
    print "zeroFields started: " + time.strftime('%X %x %Z')+"\n"
    fieldlist = ["TAZAREA", "LOCALAREA", "STOPSAREA", "LOCALPCT", "STOPSPCT", "WALKPCT"]
    taz_fields = arcpy.ListFields(TAZ_FL)
    for field in fieldlist:
        if field not in taz_fields:
            arcpy.AddField_management(TAZ_FL, field, "DOUBLE")
        if field == "TAZAREA":
            arcpy.CalculateField_management(TAZ_FL, field, "!shape.area@squaremeters!", "PYTHON_9.3")
        else:
            arcpy.CalculateField_management(TAZ_FL, field, 0, "PYTHON_9.3")


# Select, Buffer, Intersect, Dissolve, Calculate Area, Summarize, and Update Local Area
def updateLinesArea():
    print "updateLinesArea started: " + time.strftime('%X %x %Z')+"\n"    
    arcpy.Buffer_analysis(Local_Bus_Lines, "in_memory/BusLines_Buffer", "0.4 Miles", "FULL", "ROUND", "ALL")
    arcpy.Intersect_analysis(["in_memory/BusLines_Buffer", "in_memory/TAZ_WalkBuffer_FL"], "in_memory/BusLines_TAZ_Intersect", "ALL", "", "INPUT")
    arcpy.Dissolve_management("in_memory/BusLines_TAZ_Intersect", "in_memory/BusLines_Dissolve", "TAZID", "", "MULTI_PART", "DISSOLVE_LINES")
    arcpy.CalculateAreas_stats("in_memory/BusLines_Dissolve", "in_memory/BusLines_Area")
    arcpy.Statistics_analysis("in_memory/BusLines_Area", "in_memory/BusLines_AreaStats", [["F_AREA", "MAX"]], "TAZID")
    arcpy.AddJoin_management(TAZ_FL, "TAZID", "in_memory/BusLines_AreaStats", "TAZID", "KEEP_ALL")
    arcpy.CalculateField_management(TAZ_FL,
                                    arcpy.Describe(TAZ_FL).basename+"."+"LOCALAREA",
                                    "calcArea(!"+arcpy.Describe(TAZ_FL).basename+"."+"LOCALAREA"+"!, !"+"BusLines_AreaStats"+"."+"MAX_F_AREA"+"!)",
                                    "PYTHON_9.3",
                                    area_codeblock)
    arcpy.RemoveJoin_management(TAZ_FL, "")
    arcpy.CopyFeatures_management("in_memory/BusLines_Buffer", os.path.join(temp_folder, "wb_elseBusLines_Buffer.shp"))
    arcpy.CopyFeatures_management("in_memory/BusLines_TAZ_Intersect", os.path.join(temp_folder, "wb_BusLines_TAZ_Intersect.shp"))
    arcpy.CopyFeatures_management("in_memory/BusLines_Dissolve", os.path.join(temp_folder, "wb_BusLines_Dissolve.shp"))
    arcpy.CopyFeatures_management("in_memory/BusLines_Area", os.path.join(temp_folder, "wb_BusLines_Area.shp"))
    deletefiles.append("in_memory/BusLines_Buffer")
    deletefiles.append("in_memory/BusLines_TAZ_Intersect")
    deletefiles.append("in_memory/BusLines_Dissolve")
    deletefiles.append("in_memory/BusLines_Area")
    deletefiles.append("in_memory/BusLines_AreaStats")
    print "Updated Local Area"+"\n"


# Buffer, Intersect, Dissolve, Calculate Area, Summarize, and Update Stops Area
def updateStopsArea():
    print "updateStopsArea started: " + time.strftime('%X %x %Z')+"\n"    
    arcpy.Buffer_analysis(Local_Bus_Stops, "in_memory/BusStops_Buffer", "0.4 Miles", "FULL", "ROUND", "ALL")
    arcpy.Intersect_analysis(["in_memory/BusStops_Buffer", "in_memory/TAZ_WalkBuffer_FL"], "in_memory/BusStops_TAZ_Intersect", "ALL", "", "INPUT")
    arcpy.Dissolve_management("in_memory/BusStops_TAZ_Intersect", "in_memory/BusStops_Dissolve", "TAZID", "", "MULTI_PART", "DISSOLVE_LINES")
    arcpy.CalculateAreas_stats("in_memory/BusStops_Dissolve", "in_memory/BusStops_Area")
    arcpy.Statistics_analysis("in_memory/BusStops_Area", "in_memory/BusStops_StatsArea", [["F_AREA", "MAX"]], "TAZID")
    arcpy.AddJoin_management(TAZ_FL, "TAZID", "in_memory/BusStops_StatsArea", "TAZID", "KEEP_ALL")
    arcpy.CalculateField_management(TAZ_FL,
                                    arcpy.Describe(TAZ_FL).basename+"."+"STOPSAREA",
                                    "calcArea(!"+arcpy.Describe(TAZ_FL).basename+"."+"STOPSAREA"+"!, !"+"BusStops_StatsArea"+"."+"MAX_F_AREA"+"!)",
                                    "PYTHON_9.3",
                                    area_codeblock)
    arcpy.RemoveJoin_management(TAZ_FL, "")
    arcpy.CopyFeatures_management("in_memory/BusStops_Buffer", os.path.join(temp_folder, "wb_BusStops_Buffer.shp"))
    arcpy.CopyFeatures_management("in_memory/BusStops_TAZ_Intersect", os.path.join(temp_folder, "wb_BusStops_TAZ_Intersect.shp"))
    arcpy.CopyFeatures_management("in_memory/BusStops_Dissolve", os.path.join(temp_folder, "wb_BusStops_Dissolve.shp"))
    arcpy.CopyFeatures_management("in_memory/BusStops_Area", os.path.join(temp_folder, "wb_BusStops_Area.shp"))
    deletefiles.append("in_memory/BusStops_Buffer")
    deletefiles.append("in_memory/BusStops_TAZ_Intersect")
    deletefiles.append("in_memory/BusStops_Dissolve")
    deletefiles.append("in_memory/BusStops_Area")
    deletefiles.append("in_memory/BusStops_StatsArea") 
    print "Updated Stops Area"+"\n"


# Update Local, Stops, and Walk Percentages
def updatePercentages():
    print "updatePercentages started: " + time.strftime('%X %x %Z')+"\n"    
    cursor = arcpy.da.UpdateCursor(TAZ_FL, ["TAZAREA", "LOCALPCT", "STOPSPCT", "LOCALAREA", "WALKPCT", "STOPSAREA"])
    for row in cursor:
        if row[0] == 0 or row[0] == None:
            row[1] = 0
            row[2] = 0
        else:
            row[1] = ((row[3] / row[0]) * 100)
            row[2] = ((row[5] / row[0]) * 100)
        if row[1] > row[2]:
            row[4] = row[1]
        else:
            row[4] = row[2]
        cursor.updateRow(row)
    del cursor


# Overwrite Calculation with Special Zones (100 Percent Accessible)
def overWriteZones():
    print "overWriteZones started: " + time.strftime('%X %x %Z')+"\n"
    arcpy.CalculateField_management(TAZ_FL,
                                    "WALKPCT",
                                    "calcArea(!WALKPCT!, !WALK100!)",
                                    "PYTHON_9.3",
                                    area_codeblock)
    print "Updated Percentages"+"\n"
 

def Main():
    try:
        print "\n\nRunning script..."
        print "Start Time: " + time.strftime('%X %x %Z')+"\n"
        makeTableView()
        createBusLines()
        createBusStops()
        zeroFields()
        updateLinesArea()
        updateStopsArea()
        updatePercentages()
        overWriteZones()
        arcpy.CopyFeatures_management(Local_Bus_Lines, os.path.join(temp_folder, "wb_LocalBus.shp"))
        arcpy.CopyFeatures_management(Local_Bus_Stops, os.path.join(temp_folder, "wb_Stops.shp"))
        arcpy.Delete_management(TAZ_FL)
        DeleteIntermediate()
        print "All Finished"+"\n"
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
