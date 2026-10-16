"""Regression checks for the four independent Python vector figures."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import shutil

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("epoch_figures",HERE/"generate.py")
figures=importlib.util.module_from_spec(spec)
spec.loader.exec_module(figures)

class FigureTests(unittest.TestCase):
    def test_full_retained_inputs(self):
        envelope,pairs=figures.read_inputs()
        self.assertEqual(len(pairs),174)
        self.assertEqual(float(envelope[0]["rho"]),0)
        self.assertEqual(float(envelope[-1]["rho"]),4)

    def test_changed_frontier_value_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/"results/horizon";target.mkdir(parents=True)
            source=figures.ROOT/"results/horizon"
            for name in ("broadcast-envelope.dat","stress-paired.csv"):
                shutil.copy2(source/name,target/name)
            file=target/"broadcast-envelope.dat"
            text=file.read_text(encoding="utf-8")
            file.write_text(text.replace("0.0 38.0 43.0","0.0 39.0 43.0",1),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"exact frontier"):
                figures.read_inputs(root)

    def test_omitted_paired_case_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/"results/horizon";target.mkdir(parents=True)
            source=figures.ROOT/"results/horizon"
            shutil.copy2(source/"broadcast-envelope.dat",target/"broadcast-envelope.dat")
            lines=(source/"stress-paired.csv").read_text(encoding="utf-8").splitlines()
            (target/"stress-paired.csv").write_text("\n".join(lines[:-1])+"\n",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"174 distinct"):
                figures.read_inputs(root)

    def test_direct_embedded_font_settings(self):
        self.assertFalse(figures.plt.rcParams["text.usetex"])
        self.assertEqual(figures.plt.rcParams["pdf.fonttype"],42)
        self.assertEqual(figures.NAMES,("fork","horizon","envelope","candidates"))

if __name__=="__main__":unittest.main()
