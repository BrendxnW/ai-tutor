import sys
import types
import unittest
from unittest.mock import patch

import main


class CourseSearchTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
