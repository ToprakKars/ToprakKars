"""Takes the screenshots used in my READMEs and on my portfolio.

Run by .github/workflows/screenshots.yml. Web projects are captured from their
live GitHub Pages; the two command-line tools are run for real and their output
is rendered as a terminal window.
"""
import asyncio, html, os, subprocess, sys
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path("assets")
SITE = os.environ.get("SITE", "https://toprakkars.github.io")
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")


def run(cmd, cwd, ok=(0,)):
    # "check" exits with 1 when it finds problems - that is the output we want to show
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode not in ok:
        sys.exit(f"{cmd} failed:\n{r.stderr}")
    return r.stdout


def terminal_html(title, cmd, output):
    body = f'<span class="p">$</span> {html.escape(cmd)}\n{html.escape(output.rstrip())}'
    return f"""<!doctype html><meta charset=utf-8><style>
body{{margin:0;background:#0d1117;padding:28px;display:inline-block}}
.w{{background:#161b22;border:1px solid #30363d;border-radius:10px;overflow:hidden}}
.b{{height:34px;background:#21262d;display:flex;align-items:center;padding:0 14px;gap:8px;color:#8b949e;font:13px sans-serif}}
.d{{width:12px;height:12px;border-radius:50%}}
pre{{margin:0;padding:18px 22px;color:#e6edf3;font:14px/1.5 "DejaVu Sans Mono",monospace}}
.p{{color:#3fb950}}</style>
<div class=w><div class=b><i class=d style="background:#ff5f57"></i><i class=d style="background:#febc2e"></i>
<i class=d style="background:#28c840"></i><span style="margin-left:10px">{title}</span></div><pre>{body}</pre></div>"""


async def main(work):
    OUT.mkdir(exist_ok=True)
    bf_cmd = "java -jar target/breakfast-buffet-planner-1.0.0.jar --adults 180 --children 25 --menu menu.csv --stock stock.csv"
    bf_dir = work / "breakfast-buffet-planner"
    run(["mvn", "-B", "-q", "package", "-DskipTests"], bf_dir)
    terminals = {
        "breakfast-cli": ("breakfast-buffet-planner", bf_cmd, run(bf_cmd.split(), bf_dir)),
        "transcript-check": ("turkish-transcript-tools", "python -m transcript_tools check example.txt",
                             run([sys.executable, "-m", "transcript_tools", "check", "example.txt"],
                                 work / "turkish-transcript-tools", ok=(0, 1))),
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME)

        async def new_page(scale=1):
            ctx = await browser.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=scale)
            return await ctx.new_page()

        page = await new_page()
        await page.goto(f"{SITE}/barbershop-booking-app/")
        await page.wait_for_selector("#service-list button")
        await page.screenshot(path=OUT / "booking-service.png")
        await page.click("#service-list button")
        await page.click("#barber-list button")
        await page.wait_for_timeout(500)
        await page.screenshot(path=OUT / "booking-time.png")

        page = await new_page()
        await page.goto(f"{SITE}/gate-0/")
        await page.wait_for_timeout(5000)  # let the typewriter finish
        await page.screenshot(path=OUT / "gate-0.png")

        page = await new_page()
        await page.goto(f"{SITE}/cafe-website-concept/")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=OUT / "cafe-hero.png")
        await page.evaluate("document.getElementById('menu').scrollIntoView()")
        await page.wait_for_timeout(800)
        await page.screenshot(path=OUT / "cafe-menu.png")

        page = await new_page()
        await page.goto(SITE)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=OUT / "portfolio.png")

        page = await new_page(scale=2)
        for name, (title, cmd, output) in terminals.items():
            await page.set_content(terminal_html(title, cmd, output))
            await page.locator("body").screenshot(path=OUT / f"{name}.png")
        await browser.close()

    # keep the files small: max 1400 px wide, JPEG for pages, PNG for terminals
    from PIL import Image
    for png in OUT.glob("*.png"):
        im = Image.open(png).convert("RGB")
        if im.width > 1400:
            im = im.resize((1400, round(im.height * 1400 / im.width)), Image.LANCZOS)
        if png.stem in terminals:
            im.quantize(64).save(png, optimize=True)
        else:
            im.save(png.with_suffix(".jpg"), quality=82, optimize=True, progressive=True)
            png.unlink()
    for f in sorted(OUT.iterdir()):
        print(f, f.stat().st_size)


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1] if len(sys.argv) > 1 else "..")))
