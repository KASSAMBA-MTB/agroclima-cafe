import unittest

import geopandas as gpd
from shapely.geometry import Point

from tools.HIToB_G27d_validacao_independente import (
    SOURCE_CRS,
    establish_documented_crs,
)


class DocumentedCRSTests(unittest.TestCase):
    def test_assigns_documented_crs_without_reprojecting_coordinates(self):
        original = gpd.GeoDataFrame(
            {"id": [1]}, geometry=[Point(-46.56, -21.78)], crs=None
        )
        before = tuple(original.total_bounds)

        result = establish_documented_crs(original, "storm_events")

        self.assertEqual(result.crs.to_string(), SOURCE_CRS)
        self.assertEqual(tuple(result.total_bounds), before)
        self.assertEqual((result.geometry.iloc[0].x, result.geometry.iloc[0].y),
                         (-46.56, -21.78))

    def test_rejects_coordinates_outside_published_domain(self):
        outside = gpd.GeoDataFrame(
            {"id": [1]}, geometry=[Point(-10, 0)], crs=None
        )
        with self.assertRaisesRegex(ValueError, "fora do domínio publicado"):
            establish_documented_crs(outside, "storm_events")

    def test_rejects_conflicting_existing_crs(self):
        conflicting = gpd.GeoDataFrame(
            {"id": [1]}, geometry=[Point(-46.56, -21.78)], crs="EPSG:4674"
        )
        with self.assertRaisesRegex(ValueError, "diverge do CRS documentado"):
            establish_documented_crs(conflicting, "storm_events")


if __name__ == "__main__":
    unittest.main()
