import sys
import json,sys
from playwright.sync_api import sync_playwright
import pathlib, urllib.parse, urllib.request
# the page to test: given on the command line, or the player built next to this folder (works on any computer)
_DEFAULT = (pathlib.Path(__file__).resolve().parent.parent / "player" / "player.html").as_uri()
def _path(u): return urllib.request.url2pathname(urllib.parse.urlparse(u).path) if u.startswith("file:") else u
URL=sys.argv[1] if len(sys.argv)>1 else _DEFAULT
html=open(_path(URL),encoding="utf-8").read(); data=json.loads(html.split("const DATA = ")[1].split(";\nconst $")[0]); g=data["graphs"][0]
def find(t):
    for li,l in enumerate(g["lessons"]):
        for ci,c in enumerate(l["concepts"]):
            for qi,q in enumerate(c["questions"]):
                if q["template"]==t: return li,ci,qi,q
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={"width":390,"height":844},has_touch=True,is_mobile=True); m=ctx.new_page()
    m.route("**/fonts.*/**",lambda r:r.abort()); errs=[]; m.on("pageerror",lambda e:errs.append(str(e)))
    m.goto(URL); m.wait_for_timeout(300); cdp=ctx.new_cdp_session(m)
    def finger(src,dst):
        src.scroll_into_view_if_needed(); a=src.bounding_box()
        x0,y0=a["x"]+a["width"]/2,a["y"]+a["height"]/2; vh=m.evaluate("innerHeight")
        cdp.send("Input.dispatchTouchEvent",{"type":"touchStart","touchPoints":[{"x":x0,"y":y0}]})
        cdp.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{"x":x0+8,"y":y0+8}]})
        for _ in range(60):                       # if the target is under the screen, hold near the edge: the page scrolls by itself
            bb=dst.bounding_box()
            if bb["y"]+bb["height"] < vh-20 and bb["y"]>0: break
            cdp.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{"x":x0,"y":vh-12 if bb["y"]>vh/2 else 12}]}); m.wait_for_timeout(40)
        cdp.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{"x":x0,"y":vh/2}]}); m.wait_for_timeout(120)   # leave the edge: scrolling stops
        bb=dst.bounding_box(); x1,y1=bb["x"]+bb["width"]/2,bb["y"]+bb["height"]/2
        for k in range(1,14): cdp.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{"x":x0+(x1-x0)*k/13,"y":vh/2+(y1-vh/2)*k/13}]})
        cdp.send("Input.dispatchTouchEvent",{"type":"touchEnd","touchPoints":[]}); m.wait_for_timeout(150)
    if "وضع المهندس" in m.inner_text("#modeBtn"): m.click("#modeBtn")
    def go(t):
        li,ci,qi,q=find(t); m.click(f'.les[data-l="{li}"]'); m.click(f'.station[data-c="{ci}"]'); m.click(f'.qtab[data-i="{qi}"]'); m.wait_for_timeout(100); return q
    q=go("unlocks"); finger(m.locator(f'.road[data-id="{q["route"][1]}"]'),m.locator(f'.road[data-id="{q["route"][1]}"]')); print("finger: tap a road on the journey:", m.locator(".road.lit").count()==1)
    q=go("prereq")
    for cid in q["correct"]: finger(m.locator(f'.keys .chip[data-id="{cid}"]'),m.locator("#door"))
    try: m.wait_for_function("document.querySelector('#sol')!==null",timeout=7000)
    except Exception: pass
    print("finger: keys to the door:", m.locator("#sol").count()==1)
    q=go("sequence"); finger(m.locator(f'#pool .chip[data-id="{q["order"][0]}"]'),m.locator('.plank[data-i="0"] .slab')); print("finger: stone to the bridge:", m.locator("#pool .chip.used").count()==1)
    q=go("sort"); cid=q["before"][0]; finger(m.locator(f'#pool .chip[data-id="{cid}"]'),m.locator('.building .floor[data-side="before"]').first); print("finger: concept onto an elevator floor:", m.locator(".building .floor.taken").count()==1)
    q=go("spell"); ch=[c for c in q["word"] if not c.isspace()][0]; finger(m.locator(".tile").filter(has_text=ch).first,m.locator(".lslot").first); print("finger: letter to its slot:", m.locator(".lslot.filled").count()==1)
    q=go("true_false"); target="#myes" if q["statements"][0]["answer"] else "#mno"
    finger(m.locator("#tfc"),m.locator(target)); m.wait_for_timeout(500)
    print("finger: feed the card to the right monster:", "chew" in (m.get_attribute(target,"class") or ""))
    print("errors:",errs or "none"); b.close()
