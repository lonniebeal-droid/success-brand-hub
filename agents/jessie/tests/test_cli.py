from agents.jessie.cli import build_parser


def test_cli_parser_supports_demo_and_reports():
    parser = build_parser()
    args = parser.parse_args(["run-demo"])
    assert args.command == "run-demo"

    report_args = parser.parse_args(["daily-report"])
    assert report_args.command == "daily-report"
