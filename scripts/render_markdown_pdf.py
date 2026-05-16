import argparse
import html
import os
import re
import subprocess
import base64
import sys
from pathlib import Path

# ARK-GRADE RENDERING ENGINE (v8.0 - COLLISION-FREE & STANDARDIZED)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def get_b64(filename: str) -> str:
    base_path = Path("/Users/juntae.park/projects/harness-platform/docs/issues")
    search_paths = [Path(filename), base_path / filename, base_path / f"{filename}.b64", base_path / f"{filename}"]
    for p in search_paths:
        if p.exists():
            content = p.read_text().strip() if p.suffix == '.b64' else base64.b64encode(p.read_bytes()).decode('utf-8')
            if content: return content
    return ""

def strip_emoji(text: str) -> str:
    return re.sub(r'[^\x00-\x7F가-힣\s\.,!?\(\)\[\]:;%-]', '', text).strip()

def clean_content(text: str) -> str:
    text = strip_emoji(text)
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[\^(\d+)\]", r'<span class="fn-ref">\1</span>', escaped)
    return escaped

def markdown_to_html(markdown: str) -> str:
    footnote_map = {num: text for num, text in re.findall(r"^\[\^(\d+)\]:\s*(.*)$", markdown, re.MULTILINE)}
    slides_raw = re.split(r'\n---\s*\n', markdown)
    slides_html = []

    for i, chunk in enumerate(slides_raw):
        lines = chunk.strip().splitlines()
        if not lines: continue
        layout = "default"
        if lines[0].startswith(":::"):
            m = re.match(r":::\s*(.+?)\s*:::", lines[0])
            if m:
                layout = m.group(1).strip().removeprefix("layout-")
                lines = lines[1:]

        title, content, img_src, slide_fns = "", [], "", []
        for line in lines:
            line = line.strip()
            if not line: continue
            refs = re.findall(r"\[\^(\d+)\]", line)
            for r in refs:
                if r in footnote_map and r not in [f[0] for f in slide_fns]: slide_fns.append((r, footnote_map[r]))
            if line.startswith("# "): title = line[2:]
            elif line.startswith("### "): content.append(f'<div class="section-h3">{clean_content(line[4:])}</div>')
            elif line.startswith("## "): content.append(f'<div class="section-h2">{clean_content(line[3:])}</div>')
            elif line.startswith("!["):
                m = re.match(r"^!\[.*\]\((.*)\)$", line); 
                if m: img_src = m.group(1)
            elif not line.startswith("[^"): content.append(line)

        visual_html = ""
        if img_src:
            b64 = get_b64(img_src)
            if b64:
                mime = "image/jpeg" if "robot" in img_src else "image/png"
                visual_html = f'<div class="visual-pane"><img src="data:{mime};base64,{b64}"></div>'

        list_items = "".join([f"<li>{clean_content(c[2:] if c.startswith('- ') else c)}</li>" if not c.startswith('<div') else c for c in content])
        fn_html = f'<div class="footer-safe-zone"><div class="footnotes">{" ".join([f"<span><b>[{f[0]}]</b> {clean_content(f[1])}</span>" for f in slide_fns])}</div></div>' if slide_fns else ""

        if layout == "cover":
            body = f'<div class="cover-center"><h1>{clean_content(title)}</h1><div class="subtitle">ARK-Style Premium Market Intelligence</div><div class="line"></div></div>'
        elif layout == "split":
            body = f'<h1 class="slide-title">{clean_content(title)}</h1><div class="split-grid"><div class="text-pane"><ul>{list_items}</ul></div>{visual_html}</div>'
        else:
            body = f'<h1 class="slide-title">{clean_content(title)}</h1><div class="full-pane"><ul>{list_items}</ul></div>'

        slides_html.append(f'<div class="slide layout-{layout}">{body}{fn_html}<div class="meta">ISSUE #002 | PAGE {i+1}</div></div>')

    css = """
    @page { size: 1920px 1080px; margin: 0; }
    * { box-sizing: border-box; -webkit-print-color-adjust: exact; }
    body { margin: 0; padding: 0; background: #111; font-family: "Apple SD Gothic Neo", sans-serif; }
    .slide { 
        width: 1920px; height: 1080px; background: #fff; margin: 0 auto; 
        page-break-after: always; position: relative; padding: 80px 120px 120px; 
        display: flex; flex-direction: column; overflow: hidden; 
    }
    
    h1.slide-title { font-size: 50pt; font-weight: 900; color: #111827; margin: 0 0 50px; letter-spacing: -0.05em; border-left: 18px solid #2563eb; padding-left: 35px; }
    .layout-cover { background: #111827; color: white; display: flex; align-items: center; justify-content: center; }
    .layout-cover h1 { font-size: 85pt; border: none; margin: 0; font-weight: 900; line-height: 1.0; }
    .layout-cover .subtitle { font-size: 25pt; color: #3b82f6; margin-top: 40px; font-weight: 700; letter-spacing: 0.1em; }

    /* GRID CONSTRAINTS TO PREVENT OVERLAP */
    .split-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 80px; height: 580px; margin-bottom: 20px; }
    .full-pane { flex: 1; min-height: 0; overflow: hidden; margin-bottom: 0; }

    .text-pane li, .full-pane li { font-size: 24pt; line-height: 1.45; margin-bottom: 28px; color: #374151; padding-left: 50px; position: relative; list-style: none; }
    .text-pane li::before, .full-pane li::before { content: ""; position: absolute; left: 0; top: 10pt; width: 20pt; height: 20pt; background: #2563eb; border-radius: 4px; }

    .visual-pane { background: #f9fafb; border: 3px solid #e5e7eb; border-radius: 35px; display: flex; align-items: center; justify-content: center; padding: 40px; height: 100%; }
    .visual-pane img { max-width: 100%; max-height: 100%; object-fit: contain; filter: drop-shadow(0 20px 40px rgba(0,0,0,0.12)); }

    /* FOOTER SAFE ZONE - RIGID SEPARATION */
    .footer-safe-zone { margin-top: auto; padding-top: 20px; min-height: 120px; }
    .footnotes { border-top: 2px solid #f3f4f6; padding-top: 20px; display: flex; gap: 35px; flex-wrap: wrap; }
    .footnotes span { font-size: 14pt; color: #6b7280; line-height: 1.3; }
    .fn-num { color: #2563eb; font-weight: 800; margin-right: 5px; }
    .fn-ref { vertical-align: super; font-size: 16pt; color: #2563eb; font-weight: 900; }
    
    .meta { position: absolute; bottom: 40px; left: 120px; font-size: 16pt; color: #9ca3af; font-weight: 900; }
    .section-h3 { font-size: 28pt; color: #2563eb; font-weight: 800; margin: 30px 0 20px; border-bottom: 4px solid #f3f4f6; padding-bottom: 12px; }
    .section-h2 { font-size: 32pt; color: #111827; font-weight: 800; margin: 25px 0 20px; }
    """
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(slides_html)}</body></html>"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path); parser.add_argument("output", type=Path)
    args = parser.parse_args()
    html_content = markdown_to_html(args.input.read_text(encoding="utf-8"))
    html_path = args.output.with_suffix(".html")
    html_path.write_text(html_content, encoding="utf-8")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--print-to-pdf-no-header", "--window-size=1920,1080", "--run-all-compositor-stages-before-draw", f"--print-to-pdf={args.output}", html_path.resolve().as_uri()], check=True)
    print(f"v8.0 SUCCESS: {args.output}")

if __name__ == "__main__": main()
