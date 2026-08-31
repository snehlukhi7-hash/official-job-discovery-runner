from discovery_runner.cli import build_parser


def test_cli_exposes_discovery_and_qa_only():
    help_text = build_parser().format_help().lower()
    assert "run-batch" in help_text
    assert "final-qa" in help_text
    assert "application" not in help_text
    assert "submission" not in help_text

