import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_review_comment_slicer.classifier import (
    classify_comment,
    highest_severity,
    infer_category_from_path,
    match_keywords,
    normalize_state,
    severity_score,
    text_similarity,
    tokenize,
    top_category,
)
from agent_review_comment_slicer.cli import main, parse_formats
from agent_review_comment_slicer.config import explain_config, load_config, validate_config
from agent_review_comment_slicer.models import ReviewComment, SlicerConfig
from agent_review_comment_slicer.parser import flatten_review_threads, parse_csv, parse_json, parse_jsonl
from agent_review_comment_slicer.planner import build_review_plan, build_slices, cluster_comments, summarize_comment
from agent_review_comment_slicer.reports import render_agent_prompt, render_junit, render_markdown, render_prompt_index, render_sarif, write_reports


class TempWorkspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


def sample_comments():
    return [
        ReviewComment("1", "Blocking: token is stored in plain text", "src/auth.py", 10),
        ReviewComment("2", "Security issue: token is stored in plain text", "src/auth.py", 11),
        ReviewComment("3", "Missing test for retry edge case", "tests/test_retry.py", 8),
        ReviewComment("4", "Nit: rename helper", "", None, severity="low"),
    ]


class ConfigTests(TempWorkspace):
    def test_default_config(self):
        self.assertTrue(SlicerConfig().fail_on_blocker)

    def test_config_to_dict(self):
        self.assertIn("duplicate_similarity", SlicerConfig().to_dict())

    def test_load_config(self):
        path = self.write("config.json", '{"duplicate_similarity":0.7,"default_owner":"bot"}')
        config = load_config(str(path))
        self.assertEqual(config.default_owner, "bot")

    def test_load_config_rejects_unknown(self):
        path = self.write("config.json", '{"nope": true}')
        with self.assertRaises(ValueError):
            load_config(str(path))

    def test_load_config_rejects_array(self):
        path = self.write("config.json", "[]")
        with self.assertRaises(ValueError):
            load_config(str(path))

    def test_validate_similarity(self):
        with self.assertRaises(ValueError):
            validate_config(SlicerConfig(duplicate_similarity=2))

    def test_validate_slice_comments(self):
        with self.assertRaises(ValueError):
            validate_config(SlicerConfig(max_slice_comments=0))

    def test_validate_slice_files(self):
        with self.assertRaises(ValueError):
            validate_config(SlicerConfig(max_slice_files=0))

    def test_validate_ratios(self):
        with self.assertRaises(ValueError):
            validate_config(SlicerConfig(max_duplicate_ratio=-1))

    def test_validate_owner(self):
        with self.assertRaises(ValueError):
            validate_config(SlicerConfig(default_owner=""))

    def test_explain_config_json(self):
        data = json.loads(explain_config(SlicerConfig()))
        self.assertIn("category_keywords", data)


class ParserTests(unittest.TestCase):
    def test_parse_jsonl(self):
        comments = parse_jsonl('{"id":"a","body":"hello","path":"x.py"}\n')
        self.assertEqual(comments[0].id, "a")

    def test_parse_jsonl_rejects_non_object(self):
        with self.assertRaises(ValueError):
            parse_jsonl('["bad"]\n')

    def test_parse_json_array(self):
        comments = parse_json('[{"body":"hello"}]')
        self.assertEqual(comments[0].body, "hello")

    def test_parse_json_comments_object(self):
        comments = parse_json('{"comments":[{"body":"hello"}]}')
        self.assertEqual(len(comments), 1)

    def test_parse_json_single_object(self):
        comments = parse_json('{"body":"hello"}')
        self.assertEqual(comments[0].id, "comment-1")

    def test_parse_json_threads(self):
        comments = parse_json('{"reviewThreads":[{"id":"t1","path":"a.py","comments":[{"body":"hello"}]}]}')
        self.assertEqual(comments[0].thread_id, "t1")

    def test_flatten_threads_rejects_non_list(self):
        with self.assertRaises(ValueError):
            flatten_review_threads({})

    def test_flatten_threads_rejects_bad_comment(self):
        with self.assertRaises(ValueError):
            flatten_review_threads([{"id": "t", "comments": ["bad"]}])

    def test_parse_csv(self):
        comments = parse_csv("body,path,line\nhello,a.py,3\n")
        self.assertEqual(comments[0].line, 3)

    def test_missing_body_rejected(self):
        with self.assertRaises(ValueError):
            parse_json('[{"path":"a.py"}]')

    def test_field_aliases(self):
        comments = parse_json('[{"comment":"hi","file":"a.py","position":"2","user":"me","priority":"high","kind":"tests"}]')
        self.assertEqual(comments[0].path, "a.py")
        self.assertEqual(comments[0].line, 2)
        self.assertEqual(comments[0].severity, "high")


class ClassifierTests(unittest.TestCase):
    def test_tokenize(self):
        self.assertIn("hello", tokenize("Hello, 世界"))

    def test_match_keywords(self):
        self.assertEqual(match_keywords("must fix this", {"blocker": ["must fix"]}), "blocker")

    def test_normalize_state_resolved(self):
        self.assertEqual(normalize_state("closed"), "resolved")

    def test_normalize_state_open(self):
        self.assertEqual(normalize_state("pending"), "open")

    def test_infer_docs(self):
        self.assertEqual(infer_category_from_path("docs/readme.md"), "docs")

    def test_infer_tests(self):
        self.assertEqual(infer_category_from_path("tests/test_app.py"), "tests")

    def test_infer_security(self):
        self.assertEqual(infer_category_from_path("src/auth.py"), "security")

    def test_classify_blocker(self):
        comment = classify_comment(ReviewComment("1", "must fix security issue", "x.py"), SlicerConfig())
        self.assertEqual(comment.severity, "blocker")

    def test_classify_preserves_explicit(self):
        comment = classify_comment(ReviewComment("1", "small thing", "x.py", severity="low", category="docs"), SlicerConfig())
        self.assertEqual(comment.category, "docs")

    def test_similarity_same_path(self):
        left = classify_comment(ReviewComment("1", "token stored in plain text", "a.py", 1), SlicerConfig())
        right = classify_comment(ReviewComment("2", "token stored in plain text", "a.py", 2), SlicerConfig())
        self.assertGreater(text_similarity(left, right), 0.9)

    def test_highest_severity(self):
        self.assertEqual(highest_severity(["low", "high", "medium"]), "high")

    def test_top_category(self):
        self.assertEqual(top_category(["tests", "docs", "tests"]), "tests")

    def test_severity_score(self):
        self.assertGreater(severity_score("blocker"), severity_score("low"))


class PlannerTests(unittest.TestCase):
    def test_cluster_comments_merges_duplicates(self):
        config = SlicerConfig(duplicate_similarity=0.75)
        comments = [classify_comment(comment, config) for comment in sample_comments()[:2]]
        clusters = cluster_comments(comments, config)
        self.assertEqual(len(clusters), 1)

    def test_cluster_comments_keeps_different_categories(self):
        config = SlicerConfig(duplicate_similarity=0.1)
        comments = [
            classify_comment(ReviewComment("1", "test this", "a.py", category="tests"), config),
            classify_comment(ReviewComment("2", "test this", "a.py", category="docs"), config),
        ]
        clusters = cluster_comments(comments, config)
        self.assertEqual(len(clusters), 2)

    def test_build_plan(self):
        plan = build_review_plan(sample_comments(), SlicerConfig(duplicate_similarity=0.75, max_untriaged_ratio=1))
        self.assertGreaterEqual(len(plan.clusters), 3)
        self.assertGreaterEqual(len(plan.slices), 1)

    def test_build_plan_counts_open_only(self):
        comments = [ReviewComment("1", "hello", state="resolved"), ReviewComment("2", "hello")]
        plan = build_review_plan(comments, SlicerConfig(max_untriaged_ratio=1))
        self.assertEqual(plan.open_count, 1)

    def test_build_plan_fails_on_blocker(self):
        plan = build_review_plan([ReviewComment("1", "must fix security", "a.py")], SlicerConfig())
        self.assertEqual(plan.exit_code, 1)

    def test_build_plan_no_fail_without_warnings(self):
        config = SlicerConfig(fail_on_blocker=False, max_untriaged_ratio=1)
        plan = build_review_plan([ReviewComment("1", "nit rename", "a.py", severity="low")], config)
        self.assertEqual(plan.exit_code, 0)

    def test_duplicate_ratio_warning(self):
        comments = [ReviewComment(str(i), "same review comment", "a.py", i) for i in range(1, 5)]
        plan = build_review_plan(comments, SlicerConfig(duplicate_similarity=0.5, max_duplicate_ratio=0.1, fail_on_blocker=False))
        self.assertTrue(any("duplicate" in warning for warning in plan.warnings))

    def test_untriaged_warning(self):
        plan = build_review_plan([ReviewComment("1", "hello")], SlicerConfig(fail_on_blocker=False, max_untriaged_ratio=0))
        self.assertTrue(any("missing path" in warning or "unassigned" in warning or "untriaged" in warning for warning in plan.warnings))

    def test_build_slices_respects_comment_limit(self):
        config = SlicerConfig(max_slice_comments=1, fail_on_blocker=False, max_untriaged_ratio=1)
        comments = [
            ReviewComment("1", "rename helper for clarity", "a.py", 10, severity="low", category="maintainability"),
            ReviewComment("2", "add boundary test for zero input", "a.py", 100, severity="low", category="tests"),
            ReviewComment("3", "document retry timeout behavior", "a.py", 200, severity="low", category="docs"),
        ]
        plan = build_review_plan(comments, config)
        self.assertGreaterEqual(len(plan.slices), 2)

    def test_summarize_comment_shortens(self):
        self.assertLessEqual(len(summarize_comment(ReviewComment("1", "x" * 100))), 72)

    def test_plan_to_dict(self):
        plan = build_review_plan([], SlicerConfig())
        self.assertIn("summary", plan.to_dict())


class ReportTests(TempWorkspace):
    def make_plan(self):
        return build_review_plan(sample_comments(), SlicerConfig(duplicate_similarity=0.75, max_untriaged_ratio=1))

    def test_render_markdown(self):
        self.assertIn("Agent Review Comment Plan", render_markdown(self.make_plan()))

    def test_render_markdown_contains_slice(self):
        self.assertIn("Work Slices", render_markdown(self.make_plan()))

    def test_render_markdown_escapes_pipe(self):
        plan = self.make_plan()
        plan.clusters[0].title = "left | right"
        self.assertIn("left \\| right", render_markdown(plan))

    def test_render_junit_xml(self):
        ET.fromstring(render_junit(self.make_plan()))

    def test_render_junit_failure(self):
        plan = build_review_plan([ReviewComment("1", "must fix security", "a.py")], SlicerConfig())
        self.assertIn("failure", render_junit(plan))

    def test_render_sarif_maps_clusters_to_results(self):
        data = json.loads(render_sarif(self.make_plan()))
        run = data["runs"][0]
        results = run["results"]

        self.assertEqual(data["version"], "2.1.0")
        self.assertEqual(run["tool"]["driver"]["name"], "agent-review-comment-slicer")
        self.assertTrue(any(result["ruleId"] == "review.security" for result in results))
        security = next(result for result in results if result["ruleId"] == "review.security")
        self.assertEqual(security["level"], "error")
        self.assertEqual(security["locations"][0]["physicalLocation"]["artifactLocation"]["uri"], "src/auth.py")
        self.assertEqual(security["locations"][0]["physicalLocation"]["region"]["startLine"], 10)
        self.assertIn("primaryLocationLineHash", security["partialFingerprints"])

    def test_render_sarif_includes_gate_warnings(self):
        plan = build_review_plan([ReviewComment("1", "must fix security", "a.py")], SlicerConfig())
        data = json.loads(render_sarif(plan))
        self.assertTrue(any(result["ruleId"] == "review.gate" for result in data["runs"][0]["results"]))

    def test_render_prompt_index(self):
        text = render_prompt_index(self.make_plan())
        self.assertIn("Agent Review Fix Prompts", text)
        self.assertIn("Use one prompt file per agent session", text)

    def test_render_agent_prompt(self):
        plan = self.make_plan()
        text = render_agent_prompt(plan, plan.slices[0])
        self.assertIn("Review Fix Prompt", text)
        self.assertIn("Completion Rules", text)
        self.assertIn("Review Comments", text)

    def test_write_reports_all(self):
        outputs = write_reports(self.make_plan(), self.root / "reports", ["all"])
        self.assertTrue((self.root / "reports" / "review-plan.json").exists())
        self.assertTrue((self.root / "reports" / "review-plan.sarif").exists())
        self.assertTrue((self.root / "reports" / "agent-prompts" / "index.md").exists())
        self.assertIn("markdown", outputs)
        self.assertIn("sarif", outputs)
        self.assertIn("prompts", outputs)

    def test_write_reports_selected(self):
        outputs = write_reports(self.make_plan(), self.root / "reports", ["json"])
        self.assertEqual(list(outputs), ["json"])

    def test_write_reports_md_alias(self):
        outputs = write_reports(self.make_plan(), self.root / "reports", ["md"])
        self.assertTrue((self.root / "reports" / "review-plan.md").exists())
        self.assertIn("markdown", outputs)


class CliTests(TempWorkspace):
    def run_main(self, argv):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            return main(argv)

    def test_parse_formats(self):
        self.assertEqual(parse_formats("json,markdown"), ["json", "markdown"])

    def test_parse_formats_prompts(self):
        self.assertEqual(parse_formats("prompts"), ["prompts"])

    def test_parse_formats_sarif(self):
        self.assertEqual(parse_formats("sarif"), ["sarif"])

    def test_parse_formats_default(self):
        self.assertEqual(parse_formats(" , "), ["markdown", "json", "junit"])

    def test_parse_formats_unknown(self):
        with self.assertRaises(ValueError):
            parse_formats("html")

    def test_main_print_config(self):
        self.assertEqual(self.run_main(["--print-config"]), 0)

    def test_main_requires_input(self):
        self.assertEqual(self.run_main([]), 2)

    def test_main_no_fail(self):
        input_path = self.write("comments.jsonl", '{"body":"must fix security","path":"a.py"}\n')
        code = self.run_main(["--input", str(input_path), "--out", str(self.root / "reports"), "--no-fail"])
        self.assertEqual(code, 0)

    def test_main_gate_failure(self):
        input_path = self.write("comments.jsonl", '{"body":"must fix security","path":"a.py"}\n')
        code = self.run_main(["--input", str(input_path), "--out", str(self.root / "reports")])
        self.assertEqual(code, 1)

    def test_main_bad_format_returns_two(self):
        input_path = self.write("comments.jsonl", '{"body":"hello"}\n')
        self.assertEqual(self.run_main(["--input", str(input_path), "--formats", "html"]), 2)

    def test_main_missing_file_returns_two(self):
        self.assertEqual(self.run_main(["--input", str(self.root / "missing.jsonl")]), 2)

    def test_main_writes_reports(self):
        input_path = self.write("comments.jsonl", '{"body":"nit rename","path":"a.py","severity":"low"}\n')
        code = self.run_main(["--input", str(input_path), "--out", str(self.root / "reports"), "--formats", "markdown,json,junit,sarif,prompts", "--no-fail"])
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "reports" / "junit.xml").exists())
        self.assertTrue((self.root / "reports" / "review-plan.sarif").exists())
        self.assertTrue((self.root / "reports" / "agent-prompts" / "index.md").exists())

    def test_module_version(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        result = subprocess.run([sys.executable, "-m", "agent_review_comment_slicer", "--version"], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)


class FixtureTests(unittest.TestCase):
    def test_examples_exist(self):
        self.assertTrue((ROOT / "examples" / "review-comments.jsonl").exists())
        self.assertTrue((ROOT / "examples" / "slicer.config.json").exists())

    def test_docs_exist(self):
        self.assertTrue((ROOT / "docs" / "input-formats.md").exists())
        self.assertTrue((ROOT / "docs" / "ci.md").exists())

    def test_readme_exists(self):
        self.assertTrue((ROOT / "README.md").exists())

    def test_ci_exists(self):
        self.assertTrue((ROOT / ".github" / "workflows" / "ci.yml").exists())

    def test_license_exists(self):
        self.assertTrue((ROOT / "LICENSE").exists())


if __name__ == "__main__":
    unittest.main()
