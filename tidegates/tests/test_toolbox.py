import os
from pkg_resources import resource_filename

import arcpy
import numpy

import nose.tools as nt
import numpy.testing as nptest
import tidegates.testing as tgtest
import mock

import tidegates
from tidegates import utils, toolbox


@nt.nottest
class MockResult(object):
    @staticmethod
    def getOutput(index):
        if index == 0:
            return resource_filename("tidegates.testing.input", "test_zones.shp")


class CheckToolbox_Mixin(object):
    mockMap = mock.Mock(spec=utils.EasyMapDoc)
    mockLayer = mock.Mock(spec=arcpy.mapping.Layer)
    mockUtils = mock.Mock(spec=utils)
    mxd = resource_filename("tidegates.testing.input", "test.mxd")
    simple_shp = resource_filename("tidegates.testing.input", "test_zones.shp")
    outfile = "output.shp"

    def test_isLicensed(self):
        # every toolbox should be always licensed!
        nt.assert_true(self.tbx.isLicensed())

    def test__set_parameter_dependency_single(self):
        self.tbx._set_parameter_dependency(
            self.tbx.ID_column,
            self.tbx.polygons
        )

        nt.assert_list_equal(
            self.tbx.ID_column.parameterDependencies,
            [self.tbx.polygons.name]
        )

    def test__set_parameter_dependency_many(self):
        self.tbx._set_parameter_dependency(
            self.tbx.ID_column,
            self.tbx.workspace,
            self.tbx.polygons,
        )

        nt.assert_list_equal(
            self.tbx.ID_column.parameterDependencies,
            [self.tbx.workspace.name, self.tbx.polygons.name]
        )

    def test__show_header(self):
        header = self.tbx._show_header("TEST MESSAGE", verbose=False)
        expected = "\nTEST MESSAGE\n------------"
        nt.assert_equal(header, expected)

    def test_add_result(self):
        with mock.patch.object(utils.EasyMapDoc, 'add_layer') as add_layer:
            ezmd = self.tbx._add_to_map(self.simple_shp, mxd=self.mxd)
            nt.assert_true(isinstance(ezmd, utils.EasyMapDoc))
            add_layer.assert_called_once_with(self.simple_shp)

    def test__add_scenario_columns_elev(self):
        with mock.patch.object(utils, 'add_field_with_value') as afwv:
            self.tbx._add_scenario_columns(MockResult, elev=5.0)
            afwv.assert_called_once_with(
                table=MockResult,
                field_name='flood_elev',
                field_value=5.0,
                msg="Adding 'flood_elev' field to ouput",
                verbose=True,
                asMessage=True
            )

    def test__add_scenario_columns_slr(self):
        with mock.patch.object(utils, 'add_field_with_value') as afwv:
            self.tbx._add_scenario_columns(MockResult, slr=5)
            afwv.assert_called_once_with(
                table=MockResult,
                field_name='slr',
                field_value=5,
                msg="Adding sea level rise field to ouput",
                verbose=True,
                asMessage=True
            )

    def test__add_scenario_columns_surge(self):
        with mock.patch.object(utils, 'add_field_with_value') as afwv:
            self.tbx._add_scenario_columns(MockResult, surge='TESTING')
            afwv.assert_called_once_with(
                table=MockResult,
                field_name="surge",
                field_value='TESTING',
                field_length=10,
                msg="Adding storm surge field to ouput",
                verbose=True,
                asMessage=True
            )

    def test_workspace(self):
        nt.assert_true(hasattr(self.tbx, 'workspace'))
        nt.assert_true(isinstance(self.tbx.workspace, arcpy.Parameter))
        nt.assert_equal(self.tbx.workspace.parameterType, "Required")
        nt.assert_equal(self.tbx.workspace.direction, "Input")
        nt.assert_equal(self.tbx.workspace.datatype, "Workspace")
        nt.assert_equal(self.tbx.workspace.name, 'workspace')

    def test_dem(self):
        nt.assert_true(hasattr(self.tbx, 'dem'))
        nt.assert_true(isinstance(self.tbx.dem, arcpy.Parameter))
        nt.assert_equal(self.tbx.dem.parameterType, "Required")
        nt.assert_equal(self.tbx.dem.direction, "Input")
        nt.assert_equal(self.tbx.dem.datatype, "Raster Dataset")
        nt.assert_equal(self.tbx.dem.name, 'dem')

    def test_polygons(self):
        nt.assert_true(hasattr(self.tbx, 'polygons'))
        nt.assert_true(isinstance(self.tbx.polygons, arcpy.Parameter))
        nt.assert_equal(self.tbx.polygons.parameterType, "Required")
        nt.assert_equal(self.tbx.polygons.direction, "Input")
        nt.assert_equal(self.tbx.polygons.datatype, "Feature Class")
        nt.assert_equal(self.tbx.polygons.name, 'polygons')

    def test_ID_column(self):
        nt.assert_true(hasattr(self.tbx, 'ID_column'))
        nt.assert_true(isinstance(self.tbx.ID_column, arcpy.Parameter))
        nt.assert_equal(self.tbx.ID_column.parameterType, "Required")
        nt.assert_equal(self.tbx.ID_column.direction, "Input")
        nt.assert_equal(self.tbx.ID_column.datatype, "Field")
        nt.assert_equal(self.tbx.ID_column.name, 'ID_column')

    def test_flood_output(self):
        nt.assert_true(hasattr(self.tbx, 'flood_output'))
        nt.assert_true(isinstance(self.tbx.flood_output, arcpy.Parameter))
        nt.assert_equal(self.tbx.flood_output.parameterType, "Required")
        nt.assert_equal(self.tbx.flood_output.direction, "Input")
        nt.assert_equal(self.tbx.flood_output.datatype, "String")
        nt.assert_equal(self.tbx.flood_output.name, 'flood_output')

    def test_building_output(self):
        nt.assert_true(hasattr(self.tbx, 'building_output'))
        nt.assert_true(isinstance(self.tbx.building_output, arcpy.Parameter))
        nt.assert_equal(self.tbx.building_output.parameterType, "Optional")
        nt.assert_equal(self.tbx.building_output.direction, "Input")
        nt.assert_equal(self.tbx.building_output.datatype, "String")
        nt.assert_equal(self.tbx.building_output.name, 'building_output')

    def test_wetland_output(self):
        nt.assert_true(hasattr(self.tbx, 'wetland_output'))
        nt.assert_true(isinstance(self.tbx.wetland_output, arcpy.Parameter))
        nt.assert_equal(self.tbx.wetland_output.parameterType, "Optional")
        nt.assert_equal(self.tbx.wetland_output.direction, "Input")
        nt.assert_equal(self.tbx.wetland_output.datatype, "String")
        nt.assert_equal(self.tbx.wetland_output.name, 'wetland_output')

    def test__do_flood(self):
        with mock.patch.object(tidegates.tidegates, 'flood_area') as fa:
            with mock.patch.object(self.tbx, '_add_scenario_columns') as asc:
                res = self.tbx._do_flood(
                    'dem', 'poly', 'tgid', 5.7,
                    self.outfile, surge='surge', slr=2
                )

                fa.assert_called_once_with(
                    dem='dem', polygons='poly', ID_column='tgid',
                    elevation_feet=5.7, filename=self.outfile,
                    verbose=True, asMessage=True
                )

                asc.assert_called_once_with(
                    res, elev=5.7, surge='surge', slr=2
                )

    def test__do_assessment(self):
        with mock.patch.object(tidegates.tidegates, 'assess_impact') as ai:
            ai.return_value = (1, 2, 3)
            x, y, z = self.tbx._do_assessment(
                floods_path="output",
                idcol="GeoID",
                wetlands="flooded_wetlands",
                buildings="flooded_buildings"
            )

            ai.assert_called_once_with(
                floods_path="output",
                ID_column="GeoID",
                wetlands_path="flooded_wetlands",
                wetlandsoutput="_wetlands_output",
                buildings_path="flooded_buildings",
                buildingsoutput="_buildinds_output",
                cleanup=True,
                verbose=True,
                asMessage=True,
            )

    def test__prep_flooder_input_elev_only(self):
        elev, header, fname = self.tbx._prep_flooder_input(elev="7.8", flood_output="test.shp")
        nt.assert_equal(elev, 7.8)
        nt.assert_equal(header, "Analyzing flood elevation: 7.8 ft")
        nt.assert_equal(fname, 'test7_8.shp')

    def test__prep_flooder_input_surge_and_slr(self):
        elev, header, fname = self.tbx._prep_flooder_input(slr=2.5, surge='50yr', flood_output="test.shp")
        nt.assert_equal(elev, 12.1)
        nt.assert_equal(header, "Analyzing flood elevation: 12.1 ft (50yr, 2.5)")
        nt.assert_equal(fname, 'test12_1.shp')


class Test_Flooder(CheckToolbox_Mixin):
    def setup(self):
        self.tbx = toolbox.Flooder()

    def test_elevation(self):
        nt.assert_true(hasattr(self.tbx, 'elevation'))
        nt.assert_true(isinstance(self.tbx.elevation, arcpy.Parameter))
        nt.assert_equal(self.tbx.elevation.parameterType, "Required")
        nt.assert_equal(self.tbx.elevation.direction, "Input")
        nt.assert_equal(self.tbx.elevation.datatype, "Double")
        nt.assert_equal(self.tbx.elevation.name, 'elevation')

    def test_getParameterInfo(self):
        params = self.tbx.getParameterInfo()
        names = [str(p.name) for p in params]
        known_names = ['workspace', 'dem', 'polygons', 'ID_column', 'elevation',
                       'flood_output', 'wetlands', 'wetland_output',
                       'buildings', 'building_output']
        nt.assert_list_equal(names, known_names)


class Test_StandardScenarios(CheckToolbox_Mixin):
    def setup(self):
        self.tbx = toolbox.StandardScenarios()

    def test_getParameterInfo(self):
        params = self.tbx.getParameterInfo()
        names = [str(p.name) for p in params]
        known_names = ['workspace', 'dem', 'polygons', 'ID_column',
                       'flood_output', 'wetlands', 'wetland_output',
                       'buildings', 'building_output']
        nt.assert_list_equal(names, known_names)