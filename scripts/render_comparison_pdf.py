import argparse
import subprocess
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def markdown_table_to_html(md_table: str) -> str:
    lines = [line.strip() for line in md_table.strip().split("\n")]
    if len(lines) < 2:
        return ""
    
    html = '<table style="width:100%; border-collapse: collapse; margin: 20px 0; font-size: 14px;">'
    
    # Header
    header_cols = [col.strip() for col in lines[0].split("|") if col.strip()]
    html += '<thead style="background-color: #f3f4f6;"><tr>'
    for col in header_cols:
        html += f'<th style="border: 1px solid #e5e7eb; padding: 12px; text-align: left; font-weight: bold;">{col}</th>'
    html += "</tr></thead>"
    
    # Body
    html += "<tbody>"
    for line in lines[2:]:  # Skip header and separator
        cols = [col.strip() for col in line.split("|") if col.strip()]
        if not cols: continue
        html += "<tr>"
        for i, col in enumerate(cols):
            # Bold the first column (Dimension)
            style = "border: 1px solid #e5e7eb; padding: 12px; vertical-align: top;"
            if i == 0:
                style += " font-weight: bold; background-color: #f9fafb;"
            html += f'<td style="{style}">{col}</td>'
        html += "</tr>"
    html += "</tbody></table>"
    return html

def render_comparison_pdf(md_path: Path, pdf_path: Path):
    content = md_path.read_text(encoding="utf-8")
    
    # Extract table and sections
    parts = content.split("---")
    
    html_body = ""
    for part in parts:
        part = part.strip()
        if not part: continue
        
        # Simple markdown parsing
        lines = part.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                html_body += f'<h1 style="color: #111827; border-bottom: 2px solid #2563eb; padding-bottom: 10px;">{line[2:]}</h1>'
            elif line.startswith("## "):
                html_body += f'<h2 style="color: #1f2937; margin-top: 30px;">{line[3:]}</h2>'
            elif line.startswith("### "):
                html_body += f'<h3 style="color: #2563eb; margin-top: 25px; border-bottom: 1px solid #e5e7eb; padding-bottom: 5px;">{line[4:]}</h3>'
            elif line.startswith("|"):
                # Collect full table
                table_lines = []
                for l in lines[lines.index(line):]:
                    if l.strip().startswith("|"):
                        table_lines.append(l)
                    else:
                        break
                html_body += markdown_table_to_html("\n".join(table_lines))
                # Skip the lines we just processed
                for _ in range(len(table_lines) - 1):
                    next(iter(lines), None) 
                break # Simplified
            elif line.startswith("- "):
                # Handle bold in list items
                item_text = line[2:]
                while "**" in item_text:
                    item_text = item_text.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
                html_body += f'<li style="margin-bottom: 10px; line-height: 1.6; color: #374151;">{item_text}</li>'
            elif line:
                # Handle bold in paragraphs
                while "**" in line:
                    line = line.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
                html_body += f'<p style="line-height: 1.6; color: #374151;">{line}</p>'

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: "Apple SD Gothic Neo", sans-serif; padding: 40px; color: #111827; max-width: 1000px; margin: auto; }}
            h1 {{ font-size: 28px; }}
            h2 {{ font-size: 22px; border-left: 5px solid #2563eb; padding-left: 15px; }}
            table {{ margin-bottom: 40px; }}
            p, li {{ font-size: 16px; }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """
    
    html_path = pdf_path.with_suffix(".html")
    html_path.write_text(full_html, encoding="utf-8")
    
    subprocess.run([
        CHROME, "--headless", "--disable-gpu", "--no-sandbox", 
        "--print-to-pdf-no-header", f"--print-to-pdf={pdf_path}", 
        html_path.resolve().as_uri()
    ], check=True)
    print(f"Generated PDF: {pdf_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render_comparison_pdf(args.input, args.output)
