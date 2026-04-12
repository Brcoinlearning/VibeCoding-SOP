"""
Fetch and Trim Evidence Scripts
证据采集与裁剪工具集
"""
from .git_capture import (
    capture_git_status,
    get_file_diff,
    get_commit_message,
    get_author_info
)
from .test_parser import (
    parse_test_reports,
    parse_json_report,
    parse_xml_report,
    extract_error_stack
)
from .log_trimmer import (
    trim_logs_and_diffs,
    trim_build_log,
    trim_code_diff,
    extract_test_failures,
    extract_error_summary
)
from .evidence_packager import (
    package_reviewer_input,
    format_reviewer_input_markdown,
    save_evidence_to_file,
    load_evidence_from_file
)

__all__ = [
    # Git capture
    "capture_git_status",
    "get_file_diff",
    "get_commit_message",
    "get_author_info",
    # Test parser
    "parse_test_reports",
    "parse_json_report",
    "parse_xml_report",
    "extract_error_stack",
    # Log trimmer
    "trim_logs_and_diffs",
    "trim_build_log",
    "trim_code_diff",
    "extract_test_failures",
    "extract_error_summary",
    # Evidence packager
    "package_reviewer_input",
    "format_reviewer_input_markdown",
    "save_evidence_to_file",
    "load_evidence_from_file"
]
