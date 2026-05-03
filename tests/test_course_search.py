import sys
import types
import unittest
from unittest.mock import patch

import main


class CourseSearchTest(unittest.TestCase):
    def test_canvas_course_namespace_slug_uses_username_and_canvas_id(self):
        namespace = main.build_canvas_course_namespace(
            "Student One!",
            {"id": 42, "name": "Biology 101!", "course_code": "BIO-101"}
        )

        self.assertEqual(namespace, "student-one-42")

    def test_pinecone_namespace_has_records_uses_index_stats(self):
        calls = {}

        class FakeIndex:
            def describe_index_stats(self):
                return {
                    "namespaces": {
                        "biology-101-42": {"vector_count": 8},
                        "empty-course-7": {"vector_count": 0},
                    }
                }

        class FakeDescription:
            status = {"ready": True}

        class FakePinecone:
            def __init__(self, api_key):
                calls["api_key"] = api_key

            def has_index(self, name):
                calls["has_index"] = name
                return True

            def describe_index(self, name):
                calls["describe_index"] = name
                return FakeDescription()

            def Index(self, index_name):
                calls["index_name"] = index_name
                return FakeIndex()

        fake_pinecone = types.ModuleType("pinecone")
        fake_pinecone.Pinecone = FakePinecone

        with patch.dict(sys.modules, {"pinecone": fake_pinecone}), patch.object(
            main, "PINECONE_API_KEY", "test-key"
        ):
            self.assertTrue(main.pinecone_namespace_has_records("biology-101-42"))
            self.assertFalse(main.pinecone_namespace_has_records("empty-course-7"))
            self.assertFalse(main.pinecone_namespace_has_records("missing-course-9"))

        self.assertEqual(calls["api_key"], "test-key")
        self.assertEqual(calls["has_index"], main.PINECONE_INDEX_NAME)
        self.assertEqual(calls["index_name"], main.PINECONE_INDEX_NAME)

    def test_search_uploaded_course_passages_uses_namespace_and_topic(self):
        calls = {}

        class FakeSearchQuery:
            def __init__(self, inputs, top_k):
                self.inputs = inputs
                self.top_k = top_k

        class FakeIndex:
            def search_records(self, namespace, query, fields):
                calls["namespace"] = namespace
                calls["query"] = query
                calls["fields"] = fields
                return {
                    "result": {
                        "hits": [
                            {
                                "_score": 0.94,
                                "fields": {
                                    "text": "Integer overflow can wrap values.",
                                    "filename": "Slide7.pdf",
                                    "page_number": 8,
                                    "document_id": "doc-1",
                                },
                            }
                        ]
                    }
                }

        class FakePinecone:
            def __init__(self, api_key):
                calls["api_key"] = api_key

            def Index(self, index_name):
                calls["index_name"] = index_name
                return FakeIndex()

        fake_pinecone = types.ModuleType("pinecone")
        fake_pinecone.Pinecone = FakePinecone
        fake_pinecone.SearchQuery = FakeSearchQuery

        with patch.dict(sys.modules, {"pinecone": fake_pinecone}), patch.object(
            main, "PINECONE_API_KEY", "test-key"
        ):
            passages = main.search_uploaded_course_passages(
                " integer overflow ",
                "student-1",
                top_k=5,
            )

        self.assertEqual(calls["api_key"], "test-key")
        self.assertEqual(calls["index_name"], main.PINECONE_INDEX_NAME)
        self.assertEqual(calls["namespace"], "student-1")
        self.assertEqual(calls["query"].inputs, {"text": "integer overflow"})
        self.assertEqual(calls["query"].top_k, 5)
        self.assertIn(main.PINECONE_TEXT_FIELD, calls["fields"])
        self.assertEqual(passages[0].text, "Integer overflow can wrap values.")

    def test_search_uploaded_course_passages_returns_empty_when_no_hits(self):
        class FakeSearchQuery:
            def __init__(self, inputs, top_k):
                self.inputs = inputs
                self.top_k = top_k

        class FakeIndex:
            def search_records(self, namespace, query, fields):
                return {"result": {"hits": []}}

        class FakePinecone:
            def __init__(self, api_key):
                pass

            def Index(self, index_name):
                return FakeIndex()

        fake_pinecone = types.ModuleType("pinecone")
        fake_pinecone.Pinecone = FakePinecone
        fake_pinecone.SearchQuery = FakeSearchQuery

        with patch.dict(sys.modules, {"pinecone": fake_pinecone}), patch.object(
            main, "PINECONE_API_KEY", "test-key"
        ):
            passages = main.search_uploaded_course_passages("format strings", "student-1")

        self.assertEqual(passages, [])

    def test_build_canvas_module_item_records_includes_description_and_metadata(self):
        records = main.build_canvas_module_item_records(
            {"id": 42, "name": "Biology", "course_code": "BIO-101"},
            [
                {
                    "id": 5,
                    "name": "Week 1",
                    "position": 1,
                    "published": True,
                    "items": [
                        {
                            "id": 91,
                            "title": "Lab Report",
                            "type": "Assignment",
                            "position": 2,
                            "content_id": 77,
                            "url": "https://school.instructure.com/api/v1/courses/42/assignments/77",
                            "html_url": "https://school.instructure.com/courses/42/assignments/77",
                            "published": True,
                            "locked_for_user": False,
                            "details": {"description": "<p>Explain the experiment.</p>"},
                        }
                    ],
                }
            ],
        )

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["_id"], "canvas-42-module-5-item-91")
        self.assertEqual(record["source"], "canvas")
        self.assertEqual(record["canvas_record_type"], "module_item")
        self.assertEqual(record["module_name"], "Week 1")
        self.assertEqual(record["module_item_title"], "Lab Report")
        self.assertEqual(record["module_item_content_id"], 77)
        self.assertIn("Explain the experiment.", record[main.PINECONE_TEXT_FIELD])

    def test_assignment_context_combines_assignment_and_custom_topic(self):
        assignment = main.normalize_selected_assignment_payload(
            {
                "id": 101,
                "name": "Lab Report",
                "description": "<p>Explain the experiment.</p>",
                "due_at": "2026-06-01T00:00:00Z",
                "points_possible": 10,
                "html_url": "https://school.instructure.com/courses/42/assignments/101",
            }
        )

        search_topic = main.build_tutor_search_topic("I need help with the graph", assignment)
        context = main.format_selected_assignment_context(assignment)

        self.assertIn("Lab Report", search_topic)
        self.assertIn("Explain the experiment.", search_topic)
        self.assertIn("I need help with the graph", search_topic)
        self.assertIn("Selected Canvas assignment", context)
        self.assertIn("10", context)

    def test_sanitize_pinecone_record_removes_null_metadata(self):
        sanitized = main.sanitize_pinecone_record(
            {
                "_id": "canvas-42-module-5-item-91",
                main.PINECONE_TEXT_FIELD: "Lab Report",
                "module_item_content_id": None,
                "module_item_id": 91,
                "tags": ["lab", None, 42],
                "raw": {"kind": "assignment"},
            }
        )

        self.assertNotIn("module_item_content_id", sanitized)
        self.assertEqual(sanitized["module_item_id"], 91)
        self.assertEqual(sanitized["tags"], ["lab", "42"])
        self.assertEqual(sanitized["raw"], '{"kind": "assignment"}')


if __name__ == "__main__":
    unittest.main()
