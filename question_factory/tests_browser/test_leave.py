import sys
import json
from playwright.sync_api import sync_playwright
import pathlib, urllib.parse, urllib.request
# the page to test: given on the command line, or the player built next to this folder (works on any computer)
_DEFAULT = (pathlib.Path(__file__).resolve().parent.parent / "player" / "player.html").as_uri()
def _path(u): return urllib.request.url2pathname(urllib.parse.urlparse(u).path) if u.startswith("file:") else u
URL=sys.argv[1] if len(sys.argv)>1 else _DEFAULT
html=open(_path(URL),encoding="utf-8").read(); data=json.loads(html.split("const DATA = ")[1].split(";\nconst $")[0])
errs=[]; checked=0
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1200,"height":1000}); pg.route("**/fonts.*/**",lambda r:r.abort()); pg.on("pageerror",lambda e:errs.append(str(e)[:100]))
    pg.goto(URL); pg.click("#modeBtn")
    # every game: start it, answer WRONG (so animations run), then leave at once — nothing may break
    for gi,g in enumerate(data["graphs"]):
        for li,l in enumerate(g["lessons"]):
            for ci,c in enumerate(l["concepts"]):
                for qi,q in enumerate(c["questions"]):
                    pg.click(f'.les[data-g="{gi}"][data-l="{li}"]'); pg.click(f'.station[data-c="{ci}"]'); pg.click(f'.qtab[data-i="{qi}"]')
                    t=q["template"]
                    try:
                        if t=="sequence":
                            for cid in reversed(q["order"]): pg.click(f'#pool .chip[data-id="{cid}"]')
                            pg.click("#chk")
                        elif t=="meaning": pg.locator(".fcard").first.click(force=True)
                        elif t=="true_false": pg.click("#myes")
                        elif t=="predict": pg.click('#popts .opt[data-i="0"]')
                        elif t=="odd_one_out": pg.locator(".buddy").first.click()
                        elif t=="who_am_i": pg.locator(".sus").first.click()
                        elif t=="fix_chain": pg.locator(".wagon[data-i]").first.click()
                        elif t=="prereq": pg.locator(".keys .chip").first.click()
                        elif t=="unlocks": pg.locator(".road").first.click()
                    except Exception: pass
                    pg.wait_for_timeout(350); checked+=1
                    other=(qi+1)%len(c["questions"]); pg.click(f'.qtab[data-i="{other}"]'); pg.wait_for_timeout(120)
    pg.wait_for_timeout(3000); b.close()
print("games started and left in the middle:",checked,"| JS errors:",errs[:3] or "none")
