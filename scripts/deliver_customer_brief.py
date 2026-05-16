import argparse
import subprocess
from pathlib import Path

from scripts.send_slack_file import upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RENDER_SCRIPT = PROJECT_ROOT / "scripts" / "render_markdown_pdf.py"
DEFAULT_ROUTE = "exec_president_decisions"


def render_pdf(markdown_path: Path, pdf_path: Path) -> None:
    subprocess.run(
        [".venv/bin/python", str(RENDER_SCRIPT), str(markdown_path), str(pdf_path)],
        cwd=PROJECT_ROOT,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a customer brief markdown file to PDF and upload it to Slack.")
    parser.add_argument("markdown", type=Path, help="Markdown source path")
    parser.add_argument("--pdf", type=Path, default=None, help="Output PDF path")
    parser.add_argument("--route", default=DEFAULT_ROUTE, help="Slack route name")
    parser.add_argument("--title", default=None, help="Slack file title")
    parser.add_argument("--comment", default=None, help="Slack initial comment")
    args = parser.parse_args()

    markdown_path = args.markdown.resolve()
    pdf_path = args.pdf.resolve() if args.pdf else markdown_path.with_suffix(".pdf")
    title = args.title or pdf_path.name

    render_pdf(markdown_path, pdf_path)
    upload_file(pdf_path, args.route, title=title, comment=args.comment)
    print(f"Delivered: {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
