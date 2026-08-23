import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "detect_sidepanel_opencode.py"
SPEC = importlib.util.spec_from_file_location("detector", SCRIPT)
detector = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = detector
SPEC.loader.exec_module(detector)


class DetectorTests(unittest.TestCase):
    def find(self, process_table: str):
        return detector.find_sidepanel_processes(detector.parse_processes(process_table))

    def test_finds_tui_beneath_chatgpt(self):
        processes = self.find(
            """
            100 1 ?? /Applications/ChatGPT.app/Contents/MacOS/ChatGPT
            110 100 ttys002 /bin/zsh
            120 110 ttys002 /opt/homebrew/bin/opencode
            """
        )
        self.assertEqual([120], [process.pid for process in processes])

    def test_rejects_headless_mcp_server(self):
        processes = self.find(
            """
            100 1 ?? /Applications/ChatGPT.app/Contents/MacOS/ChatGPT
            110 100 ?? node opencode-mcp
            120 110 ?? opencode serve --port 4096
            """
        )
        self.assertEqual([], processes)

    def test_rejects_opencode_in_external_terminal(self):
        processes = self.find(
            """
            200 1 ?? /Applications/Terminal.app/Contents/MacOS/Terminal
            210 200 ttys004 /bin/zsh
            220 210 ttys004 opencode
            """
        )
        self.assertEqual([], processes)

    def test_rejects_noninteractive_run_command(self):
        processes = self.find(
            """
            100 1 ?? /Applications/ChatGPT.app/Contents/MacOS/ChatGPT
            110 100 ttys002 /bin/zsh
            120 110 ttys002 opencode run do-the-work
            """
        )
        self.assertEqual([], processes)

    def test_handles_broken_ancestry_without_looping(self):
        processes = self.find("300 301 ttys005 opencode\n301 300 ttys005 /bin/zsh\n")
        self.assertEqual([], processes)


if __name__ == "__main__":
    unittest.main()
