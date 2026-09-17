import unittest

import cv2
import numpy as np

from docuvision.quality import analyze_quality
from docuvision.scanner import find_document_contour, four_point_transform, order_points, scan_document


class DocuVisionTests(unittest.TestCase):
    def test_order_points_returns_expected_corners(self):
        points = np.array([[[100, 100]], [[20, 20]], [[110, 20]], [[30, 110]]], dtype=np.float32)
        ordered = order_points(points)

        self.assertTrue(np.array_equal(ordered[0], [20, 20]))
        self.assertTrue(np.array_equal(ordered[1], [110, 20]))
        self.assertTrue(np.array_equal(ordered[2], [100, 100]))
        self.assertTrue(np.array_equal(ordered[3], [30, 110]))

    def test_four_point_transform_produces_document_like_rectangle(self):
        image = np.zeros((160, 160, 3), dtype=np.uint8)
        points = np.array([[[30, 20]], [[130, 25]], [[120, 130]], [[25, 120]]], dtype=np.float32)
        cv2.fillConvexPoly(image, points.astype(np.int32), (255, 255, 255))

        warped = four_point_transform(image, points, output_width=100)

        self.assertEqual(warped.shape[1], 100)
        self.assertGreater(warped.shape[0], 80)
        self.assertGreater(np.mean(warped), 180)

    def test_find_document_contour_detects_rectangle(self):
        edges = np.zeros((300, 300), dtype=np.uint8)
        cv2.rectangle(edges, (45, 50), (250, 260), 255, 3)

        contour, fallback = find_document_contour(edges, config=__import__("docuvision.config").config.ScannerConfig())

        self.assertFalse(fallback)
        self.assertEqual(len(contour), 4)

    def test_quality_report_flags_blank_image(self):
        blank = np.full((180, 180, 3), 128, dtype=np.uint8)
        report = analyze_quality(blank)

        self.assertFalse(report.passed)
        self.assertLess(report.contrast, 1)

    def test_scan_document_pipeline_returns_enhanced_image(self):
        image = np.full((500, 700, 3), 45, dtype=np.uint8)
        pts = np.array([[180, 70], [535, 95], [510, 430], [145, 395]], dtype=np.int32)
        cv2.fillConvexPoly(image, pts, (245, 245, 245))
        cv2.putText(image, "TEST PAGE", (240, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 3)

        result = scan_document(image)

        self.assertGreater(result.warped.shape[0], 100)
        self.assertGreater(result.warped.shape[1], 100)
        self.assertEqual(len(result.enhanced.shape), 2)


if __name__ == "__main__":
    unittest.main()

