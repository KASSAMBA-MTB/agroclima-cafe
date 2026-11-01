"""Acceptance tests for HIToB's SpatiaLite-to-WKB reader."""

import sqlite3
import struct
import unittest

from shapely.geometry import Polygon

from tools.validacao_espacial_hitob_corrigida_v2 import (
    DB,
    spatialite_to_shape,
)


class SpatialiteDecoderTests(unittest.TestCase):
    def test_real_sample_decodes_as_plausible_valid_polygon(self):
        uri = DB.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as con:
            con.execute("PRAGMA query_only=ON")
            rowid, blob = con.execute(
                "SELECT rowid, geometry FROM storm_events "
                "WHERE geometry IS NOT NULL ORDER BY rowid LIMIT 1"
            ).fetchone()

        raw = bytes(blob)
        self.assertEqual(len(raw), 2368)
        self.assertEqual(raw[0:2], b"\x00\x01")
        self.assertEqual(int.from_bytes(raw[2:6], "little"), 4326)
        self.assertEqual(raw[38], 0x7C)
        self.assertEqual(raw[39:43], b"\x03\x00\x00\x00")
        self.assertEqual(raw[-1], 0xFE)

        # WKB's little-endian marker is absent from the SpatiaLite body.
        reconstructed = b"\x01" + raw[39:-1]
        self.assertEqual(reconstructed[0], 1)
        self.assertEqual(int.from_bytes(reconstructed[1:5], "little"), 3)

        geom = spatialite_to_shape(blob)
        self.assertEqual(geom.geom_type, "Polygon", f"rowid={rowid}")
        self.assertFalse(geom.is_empty, f"rowid={rowid}")
        self.assertTrue(geom.is_valid, f"rowid={rowid}; bounds={geom.bounds}")
        minx, miny, maxx, maxy = geom.bounds
        self.assertTrue(-180 <= minx <= maxx <= 180, geom.bounds)
        self.assertTrue(-90 <= miny <= maxy <= 90, geom.bounds)
        self.assertIsInstance(geom, Polygon)

    def test_wkb_endianness_is_reconstructed_from_spatialite_header(self):
        # A minimal SpatiaLite envelope containing a POINT, in either byte order.
        for order, flag in (("little", 1), ("big", 0)):
            with self.subTest(order=order):
                srid = (4326).to_bytes(4, order, signed=True)
                coords = (1.25, -2.5)
                packed = struct.pack("<dd" if order == "little" else ">dd", *coords)
                blob = b"\x00" + bytes([flag]) + srid + (b"\x00" * 32)
                blob += b"\x7c" + (1).to_bytes(4, order) + packed + b"\xfe"
                geom = spatialite_to_shape(blob)
                self.assertEqual(geom.geom_type, "Point")
                self.assertEqual((geom.x, geom.y), coords)


if __name__ == "__main__":
    unittest.main()
