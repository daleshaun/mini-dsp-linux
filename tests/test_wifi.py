import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest

source = Path(__file__).resolve().parents[1] / "tools/mini-wifi"
loader = importlib.machinery.SourceFileLoader("wifi", str(source))
spec = importlib.util.spec_from_loader(loader.name, loader)
wifi = importlib.util.module_from_spec(spec)
loader.exec_module(wifi)


class WifiSafetyTests(unittest.TestCase):
    def info(self):
        return {"model": "Macmini4,1", "kernel": "6.test", "wl_vermagic": "6.test SMP",
                "cards": [{"modalias": "pci:v000014E4d0000432Bsv0000106Bsd00000000bc02sc80i00"}],
                "wl_aliases": ["pci:v000014E4d0000432Bsv*sd*bc*sc*i*"]}

    def test_actual_module_alias_required(self):
        data = self.info()
        self.assertEqual(wifi.eligibility(data), "")
        data["cards"][0]["modalias"] = "pci:v000014E4d0000FFFFsv0000106Bsd00000000bc02sc80i00"
        self.assertIn("does not advertise", wifi.eligibility(data))

    def test_wrong_model_missing_or_mismatched_module_refused(self):
        for key, value in [("model", "Macmini8,1"), ("wl_vermagic", ""),
                           ("wl_vermagic", "7.other SMP"), ("cards", [])]:
            data = self.info()
            data[key] = value
            self.assertTrue(wifi.eligibility(data))

    def test_apply_repeat_rollback_preserves_original(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            name = next(iter(wifi.FILES))
            path = root / name.lstrip("/")
            path.parent.mkdir(parents=True)
            path.write_text("# user's original\n")
            path.chmod(0o640)
            wifi.apply_files(root)
            wifi.apply_files(root)
            wifi.rollback(root)
            self.assertTrue((root / str(wifi.DISABLED).lstrip("/")).exists())
            self.assertEqual(path.read_text(), "# user's original\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            for other in list(wifi.FILES)[1:]:
                self.assertFalse((root / other.lstrip("/")).exists())

    def test_user_edits_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            wifi.apply_files(root)
            path = root / next(iter(wifi.FILES)).lstrip("/")
            path.write_text("# user adjusted settings\n")
            with self.assertRaises(RuntimeError):
                wifi.apply_files(root)
            with self.assertRaises(RuntimeError):
                wifi.rollback(root)
            self.assertEqual(path.read_text(), "# user adjusted settings\n")

    def test_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            target = root / "unrelated"
            target.write_text("keep")
            path = root / next(iter(wifi.FILES)).lstrip("/")
            path.parent.mkdir(parents=True)
            path.symlink_to(target)
            with self.assertRaises(RuntimeError):
                wifi.apply_files(root)
            self.assertEqual(target.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
