import geopandas as gpd
from spatial_kde import spatial_kernel_density
import os
#os.environ['PROJ_LIB'] = 'C:\\Users\\jreynolds\\Anaconda3\\envs\\testgeo2\\Library\\share\\proj'
#import gdal

#Volumeshape = os.path.join(data.Scenarios_folder, r"volumeshapefile.shp")
#VolumeDensity = os.path.join(data.Scripts_folder, r"supporting_files\KernelDensity.gdb\VolumeDensity")
#Parcel = os.path.join(data.Scripts_folder, r"supporting_files\KernelDensity.gdb\parcelpointshape04102017UTM")
#VolumePoint = os.path.join(data.Scripts_folder, r"supporting_files\KernelDensity.gdb\volumepoint")


#print("Calculating Kernel Density")
#outKDens = KernelDensity(Volumeshape, "DY_VOL", 100, 1000, "SQUARE_MAP_UNITS")
#print VolumeDensity
#print "Calculating Kernel Densityxxxxxxxxxxxx"
#outKDens.save(VolumeDensity)
#print "Join to Point"
#ExtractValuesToPoints(Parcel, VolumeDensity, VolumePoint,
                      #"NONE", "VALUE_ONLY")
 
Volumeshape = gpd.read_file(r"E:\Tasks\TDM_Arcpy_Phaseout\parcel_volume\supporting_files\volumeshapefile.shp")

spatial_kernel_density(points= Volumeshape, radius=1000, output_path="skd_not_scaled.tif", output_pixel_size=100, output_driver="GTiff", weight_col="DY_VOL", scaled=False)