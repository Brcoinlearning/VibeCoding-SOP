#!/usr/bin/env python3
"""
测试修复验证
验证三个硬问题是否已修复
"""
import sys
from pathlib import Path

# 添加skill目录到路径 - 需要添加父目录以便导入skill模块
skill_dir = Path(__file__).parent.parent
sys.path.insert(0, str(skill_dir))


def test_fix_1_archive_import():
    """测试问题1: archive_review_artifact 导入错误"""
    print("\n=== 测试1: archive_review_artifact 导入 ===")
    try:
        from skill.archive_review_artifact.scripts import archiver

        # 测试基本导入
        assert hasattr(archiver, 'archive_review_artifact')
        assert hasattr(archiver, 'determine_archive_path')
        assert hasattr(archiver, 'format_review_as_markdown_inline')

        # 测试format_review_as_markdown_inline函数
        test_report = {
            "task_id": "TEST-001",
            "timestamp": "2025-04-12T10:00:00Z",
            "reviewer_id": "test-reviewer",
            "review": {
                "severity": "minor",
                "lethal_flaw": "Test flaw",
                "exploit_path": "N/A",
                "evidence": {"test_case": "test_case.py"},
                "recommendation": "go"
            },
            "evidence_metadata": {}
        }

        md_content = archiver.format_review_as_markdown_inline(test_report)
        assert "Code Review Report" in md_content
        assert "TEST-001" in md_content
        assert "APPROVED" in md_content

        print("✅ 测试1通过: archive_review_artifact导入正常，format_review_as_markdown_inline工作正常")
        return True
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fix_2_coverage_none():
    """测试问题2: test_parser coverage None值处理"""
    print("\n=== 测试2: test_parser None值处理 ===")
    try:
        from skill.fetch_and_trim_evidence.scripts import test_parser

        # 测试None值
        test_cases = [
            {"percent_covered": None},
            {"coverage": {}},
            {"coverage": {"percent": None}},
            {"percent_covered": 85.5},
            {}  # 完全缺失
        ]

        for i, case in enumerate(test_cases, 1):
            result = test_parser.parse_coverage_json(case)
            assert "coverage_percent" in result
            assert "test_summary" in result

            # 验证不会崩溃
            if result["coverage_percent"] is None:
                assert "N/A" in result["test_summary"]
                print(f"  ✅ 用例{i}: None值正确处理 → {result['test_summary']}")
            else:
                assert "Coverage:" in result["test_summary"]
                print(f"  ✅ 用例{i}: 正常值 → {result['test_summary']}")

        print("✅ 测试2通过: coverage None值处理正常，不会崩溃")
        return True
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fix_3_file_pattern_matching():
    """测试问题3: flaw_detector 文件类型匹配"""
    print("\n=== 测试3: flaw_detector 文件类型匹配 ===")
    try:
        from skill.execute_structured_review.scripts.flaw_detector import (
            matches_file_pattern,
            detect_flaws_in_code
        )

        # 测试matches_file_pattern函数
        test_cases = [
            # (file_path, file_ext, file_name, patterns, should_match)
            ("auth/login.py", ".py", "login.py", ["*.py"], True),
            ("auth/login.py", ".py", "login.py", ["*.js", "*.ts"], False),
            ("src/index.js", ".js", "index.js", ["*.py", "*.js"], True),
            ("README.md", ".md", "readme.md", ["*"], True),
            ("test.go", ".go", "test.go", ["*.py", "*.js"], False),
        ]

        for i, (fp, ext, name, patterns, expected) in enumerate(test_cases, 1):
            result = matches_file_pattern(fp, ext, name, patterns)
            if result == expected:
                print(f"  ✅ 用例{i}: {fp} vs {patterns} → {result} (预期: {expected})")
            else:
                print(f"  ❌ 用例{i}: {fp} vs {patterns} → {result} (预期: {expected})")
                return False

        # 测试detect_flaws_in_code使用正确的模式匹配
        test_code = "query = f\"SELECT * FROM users WHERE username='{username}'\""
        flaws = detect_flaws_in_code(test_code, "auth/login.py")
        assert len(flaws) > 0, "应该检测到SQL注入漏洞"
        assert any(f["name"] == "SQL注入" for f in flaws), "应该有SQL注入缺陷"
        print(f"  ✅ 实际检测: 在auth/login.py中检测到{len(flaws)}个缺陷")

        print("✅ 测试3通过: 文件类型匹配逻辑正确，缺陷检测有效")
        return True
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """集成测试: 完整流程"""
    print("\n=== 集成测试: 完整流程 ===")
    try:
        from skill.fetch_and_trim_evidence.scripts.evidence_packager import package_reviewer_input
        from skill.execute_structured_review.scripts.report_generator import execute_structured_review
        from skill.archive_review_artifact.scripts.archiver import archive_review_artifact

        # 模拟完整流程
        git_info = {
            "commit_hash": "abc123",
            "branch": "main",
            "changed_files": ["test.py"],
            "diff_summary": "1 file changed",
            "full_diff": "+ query = f\"SELECT * FROM users\""
        }

        test_results = {
            "passed": False,
            "total_tests": 10,
            "failed_tests": 2,
            "test_summary": "2 failed",
            "coverage_percent": None,  # 测试None值
            "failed_test_cases": []
        }

        # 步骤1: 封装证据
        evidence = package_reviewer_input(
            task_id="INTEGRATION-001",
            git_info=git_info,
            test_results=test_results,
            trimmed_diff="+ query",
            trimmed_log=""
        )

        # 步骤2: 执行审查
        review_data = {
            "severity": "critical",
            "lethal_flaw": "SQL注入",
            "exploit_path": "步骤1: 注入",
            "evidence": {"test_case": "test.py"},
            "recommendation": "no-go"
        }

        report = execute_structured_review(evidence, review_data, "tester")

        # 步骤3: 归档 (使用临时路径)
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            result = archive_review_artifact(
                report,
                "no-go",
                base_path=Path(tmpdir)
            )

            if result["success"]:
                # 验证文件存在
                archive_file = Path(result["filepath"])
                assert archive_file.exists(), "归档文件应该存在"

                # 验证内容
                content = archive_file.read_text(encoding='utf-8')
                assert "INTEGRATION-001" in content
                assert "SQL注入" in content

                print(f"  ✅ 完整流程成功，文件已归档: {archive_file.name}")
            else:
                print(f"  ❌ 归档失败: {result.get('error')}")
                return False

        print("✅ 集成测试通过: 三个技能协作正常")
        return True
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Skill修复验证测试")
    print("=" * 60)

    results = []
    results.append(test_fix_1_archive_import())
    results.append(test_fix_2_coverage_none())
    results.append(test_fix_3_file_pattern_matching())
    results.append(test_integration())

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    total = len(results)
    passed = sum(results)

    print(f"\n通过: {passed}/{total}")

    if all(results):
        print("\n✅ 所有测试通过！修复验证成功。")
        return 0
    else:
        print("\n❌ 部分测试失败，需要进一步修复。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
