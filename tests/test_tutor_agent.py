import asyncio
import json
import sys
import types
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from tutor_agent import (
    CoursePassage,
    TutorCurriculum,
    TutorCurriculumSession,
    curriculum_to_dict,
    curriculum_to_hidden_context,
    generate_tutor_curriculum,
    is_substantive_student_topic,
    normalize_course_search_results,
)


def sample_curriculum():
    return TutorCurriculum(
        session_goal="Understand how fractions with unlike denominators are added.",
        estimated_minutes=4,
        steps=[
            {
                "order": 1,
                "title": "Name the pieces",
                "teaching_point": (
                    "A denominator names the size of each piece, so unlike "
                    "denominators describe different-sized pieces."
                ),
                "check_question": "What does the denominator tell us?",
                "expected_answer_signals": ["piece size", "how many equal parts"],
            },
            {
                "order": 2,
                "title": "Find a shared size",
                "teaching_point": (
                    "Before adding, rename both fractions with a common denominator "
                    "so the pieces are the same size."
                ),
                "check_question": "Why do we need a common denominator?",
                "expected_answer_signals": ["same size", "same kind of pieces"],
            },
            {
                "order": 3,
                "title": "Add and simplify",
                "teaching_point": (
                    "Once denominators match, add the numerators and keep the "
                    "denominator, then simplify if possible."
                ),
                "check_question": "What changes when denominators already match?",
                "expected_answer_signals": ["add numerators", "denominator stays"],
            },
        ],
        wrap_up="The student should be ready to add a simple unlike-denominator pair.",
    )


def sample_passages():
    return [
        CoursePassage(
            text=(
                "Buffer overflows happen when a program writes more data into "
                "a fixed-size memory buffer than it can hold."
            ),
            filename="Software Vulnerabilities.pdf",
            page_number=18,
            document_id="doc-1",
            score=0.91,
        )
    ]


class TutorCurriculumModelTest(unittest.TestCase):
    def test_curriculum_contract_is_json_schema_valid(self):
        curriculum = sample_curriculum()

        self.assertGreaterEqual(curriculum.estimated_minutes, 2)
        self.assertLessEqual(curriculum.estimated_minutes, 7)
        self.assertGreaterEqual(len(curriculum.steps), 3)
        self.assertLessEqual(len(curriculum.steps), 5)
        self.assertEqual([step.order for step in curriculum.steps], [1, 2, 3])
        self.assertTrue(all(step.check_question for step in curriculum.steps))

        payload = curriculum_to_dict(curriculum)
        encoded = curriculum.model_dump_json()
        self.assertEqual(json.loads(encoded)["session_goal"], payload["session_goal"])

    def test_curriculum_rejects_too_few_steps(self):
        payload = curriculum_to_dict(sample_curriculum())
        payload["steps"] = payload["steps"][:2]

        with self.assertRaises(ValidationError):
            TutorCurriculum.model_validate(payload)

    def test_hidden_context_includes_checks(self):
        hidden_context = curriculum_to_hidden_context(sample_curriculum())

        self.assertIn("Hidden tutor curriculum context", hidden_context)
        self.assertIn("Understanding check:", hidden_context)
        self.assertIn("wait for the student", hidden_context)

    def test_topic_filter_skips_kickoff_and_greetings(self):
        self.assertFalse(is_substantive_student_topic("hello"))
        self.assertFalse(is_substantive_student_topic("Greet the student as their tutor"))
        self.assertTrue(is_substantive_student_topic("adding fractions"))

    def test_course_search_result_normalization(self):
        response = {
            "result": {
                "hits": [
                    {
                        "_score": 0.88,
                        "fields": {
                            "text": "  Format string bugs leak stack values.  ",
                            "filename": "Slide7.pdf",
                            "page_number": "12",
                            "document_id": "doc-7",
                        },
                    },
                    {"_score": 0.1, "fields": {"text": ""}},
                ]
            }
        }

        passages = normalize_course_search_results(response, "text")

        self.assertEqual(len(passages), 1)
        self.assertEqual(passages[0].text, "Format string bugs leak stack values.")
        self.assertEqual(passages[0].filename, "Slide7.pdf")
        self.assertEqual(passages[0].page_number, 12)
        self.assertEqual(passages[0].document_id, "doc-7")
        self.assertEqual(passages[0].score, 0.88)

    def test_generate_curriculum_prompt_includes_course_passages(self):
        captured = {}

        class FakeAgent:
            async def ainvoke(self, payload):
                captured["payload"] = payload
                return {"structured_response": sample_curriculum()}

        def fake_create_agent(**kwargs):
            captured["system_prompt"] = kwargs["system_prompt"]
            return FakeAgent()

        fake_langchain = types.ModuleType("langchain")
        fake_langchain_agents = types.ModuleType("langchain.agents")
        fake_langchain_agents.create_agent = fake_create_agent
        fake_google_genai = types.ModuleType("langchain_google_genai")
        fake_google_genai.ChatGoogleGenerativeAI = lambda **kwargs: object()

        with patch.dict(
            sys.modules,
            {
                "langchain": fake_langchain,
                "langchain.agents": fake_langchain_agents,
                "langchain_google_genai": fake_google_genai,
            },
        ):
            curriculum = asyncio.run(
                generate_tutor_curriculum(
                    "buffer overflows",
                    username="student-1",
                    course_passages=sample_passages(),
                )
            )

        message = captured["payload"]["messages"][0]["content"]
        self.assertEqual(curriculum.session_goal, sample_curriculum().session_goal)
        self.assertIn("Relevant uploaded course excerpts", message)
        self.assertIn("Buffer overflows happen", message)
        self.assertIn("Software Vulnerabilities.pdf", message)
        self.assertIn("Base the plan on the supplied course excerpts", captured["system_prompt"])

    def test_generate_curriculum_falls_back_without_langchain(self):
        with patch.dict(sys.modules, {"langchain": None, "langchain_google_genai": None}):
            curriculum = asyncio.run(
                generate_tutor_curriculum(
                    "buffer overflows",
                    username="student-1",
                    course_passages=sample_passages(),
                )
            )

        self.assertEqual(curriculum.estimated_minutes, 3)
        self.assertEqual(len(curriculum.steps), 3)
        self.assertIn("buffer overflows", curriculum.session_goal.lower())
        self.assertIn("Buffer overflows happen", curriculum.steps[0].teaching_point)
        self.assertIn("main idea", curriculum.steps[0].check_question.lower())

    def test_generate_curriculum_requires_course_passages(self):
        with self.assertRaisesRegex(ValueError, "course content"):
            asyncio.run(generate_tutor_curriculum("buffer overflows", course_passages=[]))


class TutorCurriculumSessionTest(unittest.IsolatedAsyncioTestCase):
    async def test_session_generates_only_once(self):
        calls = []

        async def fake_generator(topic, username, course_passages):
            calls.append((topic, username, course_passages))
            await asyncio.sleep(0)
            return sample_curriculum()

        session = TutorCurriculumSession(username="student-1", generator=fake_generator)

        empty_result = await session.maybe_generate("hi")
        first_result = await session.maybe_generate(
            "  adding   fractions  ",
            sample_passages(),
        )
        second_result = await session.maybe_generate(
            "multiplying decimals",
            sample_passages(),
        )

        self.assertIsNone(empty_result)
        self.assertIsNotNone(first_result)
        self.assertIsNone(second_result)
        self.assertEqual(calls, [("adding fractions", "student-1", sample_passages())])

    async def test_concurrent_topic_events_generate_once(self):
        calls = []

        async def fake_generator(topic, username, course_passages):
            calls.append((topic, username, course_passages))
            await asyncio.sleep(0.01)
            return sample_curriculum()

        session = TutorCurriculumSession(username="student-2", generator=fake_generator)
        results = await asyncio.gather(
            session.maybe_generate("linear equations", sample_passages()),
            session.maybe_generate("linear equations", sample_passages()),
            session.maybe_generate("linear equations", sample_passages()),
        )

        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(calls, [("linear equations", "student-2", sample_passages())])

    async def test_session_requires_course_passages_for_substantive_topic(self):
        async def fake_generator(topic, username, course_passages):
            return sample_curriculum()

        session = TutorCurriculumSession(username="student-3", generator=fake_generator)

        with self.assertRaisesRegex(ValueError, "No relevant uploaded course content"):
            await session.maybe_generate("buffer overflows", [])


if __name__ == "__main__":
    unittest.main()
