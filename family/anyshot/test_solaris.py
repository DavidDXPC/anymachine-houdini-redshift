"""Offline camera regressions. Run python -m unittest test_solaris in this folder."""
from pathlib import Path
import unittest

import numpy as np
from pxr import Usd, UsdGeom

import solaris


def stage():
    scene = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageMetersPerUnit(scene,1.)
    UsdGeom.SetStageUpAxis(scene,UsdGeom.Tokens.y)
    return scene


class SolarisCameras(unittest.TestCase):
    def test_example_cut_holds_and_preserves_physical_lenses(self):
        s = stage()
        world = UsdGeom.Xform.Define(s,"/World")
        world.AddTranslateOp().Set((10,0,0))
        cut = solaris.author(s,"camera/examples/solaris_shots.json",Path(__file__).parent)
        c = UsdGeom.Camera.Get(s,cut["camera"])
        self.assertEqual((cut["frames"],cut["fps"]),(84,24))
        self.assertTrue(np.allclose(c.ComputeLocalToWorldTransform(1).ExtractTranslation(),(3,2,4)))
        self.assertTrue(np.allclose(c.ComputeLocalToWorldTransform(48.9).ExtractTranslation(),(2,1.8,3)))
        self.assertAlmostEqual(c.GetFocalLengthAttr().Get(48.9),.42,places=5)
        self.assertAlmostEqual(c.GetFocalLengthAttr().Get(49),.65,places=5)
        solaris.author(s,dict(shots=[dict(name="wide",frames=1,eye=[2,0,0],target=[0,0,0])]),".")
        self.assertEqual(c.GetFocalLengthAttr().GetTimeSamples(),[1.])

    def test_named_tracking_z_input_and_dolly_zoom(self):
        s = stage()
        subject = UsdGeom.Xform.Define(s,"/World/Cup")
        motion = subject.AddTranslateOp()
        motion.Set((0,1,0),1)
        motion.Set((0,1,1),3)
        shot = dict(name="push",move="dolly_zoom",frames=3,eye=[0,-4,1],
                    end_eye=[0,-3,1],target="Cup",focus=dict(mode="track",obj="/World/Cup"),lens=40)
        cut = solaris.author(s,dict(input_axes="Z",shots=[shot]),".")
        c = UsdGeom.Camera.Get(s,cut["camera"])
        self.assertAlmostEqual(c.GetFocusDistanceAttr().Get(1),4.)
        self.assertAlmostEqual(c.GetFocusDistanceAttr().Get(3),2.)
        self.assertAlmostEqual(c.GetFocalLengthAttr().Get(3),.2)

    def test_clearance_measures_mesh_surface_at_each_frame(self):
        s = stage()
        m = UsdGeom.Mesh.Define(s,"/World/Triangle")
        m.CreatePointsAttr([(-2,0,-2),(2,0,-2),(-2,0,2)])
        m.CreateFaceVertexIndicesAttr([0,1,2])
        m.CreateFaceVertexCountsAttr([3])
        shot = dict(name="travel",move="dolly",frames=3,eye=[-1,.4,-1],end_eye=[1,.4,1],target=[0,1,0])
        spec = dict(clearance=dict(on_hit="report",include=["/World/Triangle"]),shots=[shot])
        hits = solaris.author(s,spec,".")["clearance_hits"]
        self.assertEqual([h["frame"] for h in hits],[1,2])
        self.assertAlmostEqual(hits[0]["distance_m"],.4)
        spec["clearance"]["on_hit"] = "error"
        with self.assertRaisesRegex(ValueError,"Triangle"):
            solaris.author(s,spec,".")


if __name__ == "__main__":
    unittest.main()
