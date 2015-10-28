import os
import sys
import glob
import datetime

import numpy

import arcpy

from . import utils

__all__ = ["flood_area", "assess_impact"]


METERS_PER_FOOT = 0.3048

MHHW = 4  * METERS_PER_FOOT # GUESS
SEALEVELRISE = numpy.arange(7) * METERS_PER_FOOT
SURGES = {
    'MHHW' :   4.0 * METERS_PER_FOOT, # no storm surge
    '10-yr':   8.0 * METERS_PER_FOOT, #  10-yr (approx)
    '25-yr':   8.5 * METERS_PER_FOOT, #  25-yr (guess)
    '50-yr':   9.6 * METERS_PER_FOOT, #  50-yr (approx)
    '100-yr': 10.5 * METERS_PER_FOOT, # 100-yr (guess
}



def flood_area(dem, polygons, tidegate_column, elevation_feet,
               filename=None, cleanup=True, **verbose_options):
    """ Mask out portions of a a tidegates area of influence below
    a certain elevation.

    Parameters
    ----------
    dem : str or arcpy.Raster
        The (filepath to the ) Digital Elevation Model of the area.
    polygons : str or arcpy.mapping.Layer
        The (filepath to the) zones that will be flooded. If a string,
        a Layer will be created.
    tidegate_column : str
        Name of the column in the ``polygons`` layer that associates
        each geomstry with a tidegate.
    elevation_feet: float
        The theoritical flood elevation (in ft MSL) that will be
        analyzed.
    filename : str, optional
        Filename to which the flooded zone will be saved.
    cleanup : bool (default = True)
        When True, temporary results are removed from disk.

    Additional Optional Parameters
    ------------------------------
    verbose : bool (default = False)
        Toggles the printing of messages communication the progress
        of the processing.
    asMessage : bool (default = False)
        When True, progress messages are passed through
        ``arcpy.AddMessage``. Otherwise, the msg is simply printed to
        stdin.

    Returns
    -------
    flood_polygons : arcpy.mapping.Layer
        arcpy Layer of the polygons showing the extent flooded behind
        each tidegate.

    """

    # convert the elevation to meters to match the DEM
    elevation_meters = elevation_feet * METERS_PER_FOOT

    if filename is None:
        datefmt = '%Y%m%d_%H%M'
        datestring = datetime.datetime.now().strftime(datefmt)
        temp_filename = "_temp_FloodedZones_" + datestring
    else:
        temp_filename = '_temp_' + filename

    utils.progress_print('1/9 Working in {}'.format(arcpy.env.workspace), **verbose_options)

    # load the raw DEM (topo data)
    raw_topo = utils.load_data(dem, "raster")
    utils.progress_print('2/9 {} raster loaded'.format(dem), **verbose_options)

    # load the zones of influence, converting to a raster
    cellsize = raw_topo.meanCellWidth
    zones_r, zone_res = utils.process_polygons(polygons, tidegate_column, cellsize=cellsize)
    utils.progress_print('3/9 {} polygon processed'.format(polygons), **verbose_options)

    # clip the DEM to the zones raster
    topo_r, topo_res = utils.clip_dem_to_zones(raw_topo, zones_r)
    utils.progress_print('4/9 topo clipped', **verbose_options)

    # convert the clipped DEM and zones to numpy arrays
    zones_a, topo_a = utils.rasters_to_arrays(zones_r, topo_r)
    utils.progress_print('5/9 rasters to arrays', **verbose_options)

    # compute floods of zoned areas of topo
    flooded_a = utils.flood_zones(zones_a, topo_a, elevation_meters)
    utils.progress_print('6/9 flood things', **verbose_options)

    # convert flooded zone array back into a Raster
    flooded_r = utils.array_to_raster(array=flooded_a, template=zones_r)
    with utils.OverwriteState(True):
        flooded_r.save('tempraster')
        utils.progress_print('7/9 coverted back to raster and saved', **verbose_options)

    # convert raster into polygons
    utils.progress_print('8/9 convert to polygon in {}'.format(arcpy.env.workspace), **verbose_options)
    temp_result = arcpy.conversion.RasterToPolygon(
        in_raster=flooded_r,
        out_polygon_features=temp_filename,
        simplify="SIMPLIFY",
        raster_field="Value"
    )

    # dissolve (merge) broken polygons for each tidegate
    flood_polygons = arcpy.management.Dissolve(
        in_features=utils.result_to_layer(temp_result),
        out_feature_class=filename,
        dissolve_field="gridcode",
        statistics_fields='#'
    )
    utils.progress_print('9/9 dissolve', **verbose_options)

    if cleanup:
        utils.cleanup_temp_results(temp_result, flooded_r, topo_r, zones_r)

    ezmd = utils.EasyMapDoc("CURRENT")
    if ezmd.mapdoc is not None and filename is not None:
        ezmd.add_layer(filename)

    return flood_polygons


def assess_impact(flood_layer, input_gdb, overwrite=False, **verbose_options):
    outputlayers = []
    assetnames = ["Landuse", "SaltMarsh", "Wetlands"]


    with utils.OverwriteState(overwrite):
        with utils.WorkSpace(input_gdb):
            utils.progress_print(arcpy.env.workspace, **verbose_options)
            input_layer = utils.load_data(flood_layer, "shape")
            # loop through the selected assets
            for asset in assetnames:
                # create the asset layer object
                utils.progress_print('load asset layer {}'.format(asset), **verbose_options)
                assetlayer = utils.load_data(asset, "shape")

                # intersect the flooding with the asset
                outputpath = '{}_{}'.format(flood_layer, asset)
                utils.progress_print("save intersection to {}".format(outputpath), **verbose_options)
                result = arcpy.analysis.Intersect([input_layer, assetlayer], outputpath)

                # append instersetected layer to the output list
                utils.progress_print("save results", **verbose_options)
                outputlayers.append(utils.result_to_layer(result))

    return outputlayers


def _assess_impact(inputspace, outputspace, SLR, surge, overwrite, assetnames):
    utils.progress_print(assetnames, **verbose_options)
    INPUT_FLOOD_LAYER = "FloodScenarios"
    outputlayers = []

    # flood layer object for the flooding and query for our scenario
    floodlayer = arcpy.mapping.Layer(os.path.join(inputspace, INPUT_FLOOD_LAYER))

    ## create the query string
    qry = '"SLR" = %d AND "surge" = \'%s\'' % (int(SLR), surge)

    ## apply the query to the layer
    floodlayer.definitionQuery = qry

    # add the layer to list of layer that will be output
    outputlayers.append(floodlayer)

    with utils.OverwriteState(overwrite) as state:
        # loop through the selected assets
        for asset in assetnames.split(';'):

            # create the asset layer object
            assetlayer = arcpy.mapping.Layer(os.path.join(inputspace, asset))
            #assetlayer = arcpy.mapping.Layer(asset)

            # intersect the flooding with the  asset
            outputpath = os.path.join(outputspace, "Test_Flood_%s_%d_%s" % (asset, int(SLR), surge))
            result = arcpy.analysis.Intersect([floodlayer, assetlayer], outputpath)

            # create a layer object of the intersected areas
            intersectedlayer = arcpy.mapping.Layer(result.getOutput(0))

            # append instersetected layer to the output list
            outputlayers.append(intersectedlayer)

    return outputlayers


# if __name__ == '__main__':
#     # input from dialogue
#     outputlayers = flood_area(*sys.argv[2:])
#     mapdoc = EasyMapDoc("CURRENT")
#     for lyr in outputlayers:
#         mapdoc.add_layer(lyr)
