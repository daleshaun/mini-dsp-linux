"""Exercise the patched installer probes without executing any disk wizard."""
import ast
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ISO = Path(__file__).resolve().parents[1] / "upstream-iso"


@unittest.skipUnless(ISO.exists(), "Pinned upstream checkout required")
class BootSelectionTests(unittest.TestCase):
    def test_interactive_mini_uses_lts(self):
        text = (ISO / "configs/airootfs/root/configurator").read_text()
        probe = re.search(r"^detect_kernel\(\) \{\n.*?^\}", text, re.M | re.S).group()
        result = subprocess.run(["bash", "-c", 'lspci() { printf "%s\\n" "$TEST_PCI"; }\n'
                                 + probe + "\ndetect_kernel"],
                                env={**os.environ, "TEST_PCI": "Network controller [0280]: Broadcom [14e4:432b]"},
                                check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "linux-lts")

    def test_unattended_mini_uses_same_kernel(self):
        source = ISO / "configs/airootfs/usr/share/omarchy-iso/orchestrator/context.py"
        tree = ast.parse(source.read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_default_kernel")
        scope = {"Path": Path}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), "exec"), scope)
        with tempfile.TemporaryDirectory() as d:
            pci = Path(d)
            card = pci / "0000:02:00.0"
            card.mkdir()
            (card / "vendor").write_text("0x14e4\n")
            (card / "device").write_text("0x432b\n")
            self.assertEqual(scope["_default_kernel"](pci), "linux-lts")

    def test_boot_entries_have_matching_live_preset(self):
        config = ISO / "configs"
        preset = config / "airootfs/etc/mkinitcpio.d/linux-lts.preset"
        self.assertIn("/boot/vmlinuz-linux-lts", preset.read_text())
        for p in [config / "grub/grub.cfg", config / "syslinux/archiso_sys-linux.cfg"]:
            text = p.read_text()
            self.assertIn("vmlinuz-linux-lts", text)
            self.assertIn("initramfs-linux-lts.img", text)
            self.assertNotIn("linux-t2", text)


if __name__ == "__main__":
    unittest.main()
