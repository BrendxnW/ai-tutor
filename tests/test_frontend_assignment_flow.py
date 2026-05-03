from pathlib import Path
import unittest


BASE_DIR = Path(__file__).resolve().parents[1]


class FrontendAssignmentFlowTest(unittest.TestCase):
    def test_upload_content_links_to_tutor(self):
        upload_html = (BASE_DIR / "frontend" / "upload-content.html").read_text(
            encoding="utf-8"
        )
        upload_js = (BASE_DIR / "frontend" / "upload-content.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('href="/tutor"', upload_html)
        self.assertIn('tutorLink.href = "/tutor"', upload_js)
        self.assertIn('tutorLink.textContent = "Open Tutor"', upload_js)

    def test_tutor_page_has_assignment_selector(self):
        tutor_html = (BASE_DIR / "frontend" / "tutor.html").read_text(encoding="utf-8")

        self.assertIn('id="assignment-picker"', tutor_html)
        self.assertIn('id="assignmentSelect"', tutor_html)
        self.assertIn('id="assignment-summary"', tutor_html)

    def test_session_start_payload_includes_assignment(self):
        gemini_client = (BASE_DIR / "frontend" / "gemini-client.js").read_text(
            encoding="utf-8"
        )
        main_js = (BASE_DIR / "frontend" / "main.js").read_text(encoding="utf-8")

        self.assertIn("assignment = null", gemini_client)
        self.assertIn("assignment: assignment", gemini_client)
        self.assertIn("pendingAssignment", main_js)
        self.assertIn("getSelectedAssignment()", main_js)
        self.assertIn("/assignments", main_js)


if __name__ == "__main__":
    unittest.main()
