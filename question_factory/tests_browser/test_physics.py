import sys
import json,sys
from playwright.sync_api import sync_playwright
import pathlib, urllib.parse, urllib.request
# the page to test: given on the command line, or the player built next to this folder (works on any computer)
_DEFAULT = (pathlib.Path(__file__).resolve().parent.parent / "player" / "player.html").as_uri()
def _path(u): return urllib.request.url2pathname(urllib.parse.urlparse(u).path) if u.startswith("file:") else u
URL=sys.argv[1] if len(sys.argv)>1 else _DEFAULT
html=open(_path(URL),encoding="utf-8").read(); data=json.loads(html.split("const DATA = ")[1].split(";\nconst $")[0]); g=data["graphs"][0]
res=[];errs=[]
def ok(n,c,x=""): res.append(("✅" if c else "❌")+" "+n+" "+str(x))
def find(t,pred=lambda q:True):
    for li,l in enumerate(g["lessons"]):
        for ci,c in enumerate(l["concepts"]):
            for qi,q in enumerate(c["questions"]):
                if q["template"]==t and pred(q): return li,ci,qi,q
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1150,"height":1000}); pg.route("**/fonts.*/**",lambda r:r.abort()); pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.goto(URL); pg.click("#modeBtn")
    def go(t,pred=lambda q:True):
        li,ci,qi,q=find(t,pred); pg.click(f'.les[data-l="{li}"]'); pg.click(f'.station[data-c="{ci}"]'); pg.click(f'.qtab[data-i="{qi}"]'); pg.wait_for_timeout(250); return q
    # ---- bridge: first part wrong -> the car goes ONTO it and falls into the WATER (not on the start bank) ----
    q=go("sequence",lambda q:len(q["order"])>=3); n=len(q["order"]); W=120*n+80
    order=q["order"][1:2]+q["order"][:1]+q["order"][2:]            # first two swapped: the first part is wrong
    for cid in order: pg.click(f'#pool .chip[data-id="{cid}"]')
    pg.click("#chk"); xs=[];ys=[];wob=False
    for _ in range(90):
        pg.wait_for_timeout(60)
        t=pg.get_attribute("#car","transform") or ""
        try: x,y=map(float,t.split("translate(")[1].split(")")[0].split()); xs.append(x); ys.append(y)
        except Exception: pass
        wob=wob or "wobble" in (pg.get_attribute('.plank[data-i="0"]',"class") or "")
        if ys and ys[-1]>120: break
    fall_x=xs[-1] if xs else None
    ok("bridge: the weak part wobbles while the car is ON it", wob)
    ok("bridge: the car falls from the middle of the weak part, over the water", fall_x is not None and 40 < fall_x < W-40 and abs(fall_x-(W-40-60)) < 40, (round(fall_x or 0), W))
    ok("bridge: the car ends up in the water", ys and max(ys)>110, round(max(ys or [0])))
    pg.wait_for_timeout(3500)
    # ---- holding things: the piece leaves its place while held; dropped on its slot it settles there ----
    q=go("spell"); ch=[c for c in q["word"] if not c.isspace()][0]
    tile=pg.locator(".tile").filter(has_text=ch).first; slot=pg.locator(".lslot").first; a=tile.bounding_box(); s=slot.bounding_box()
    pg.mouse.move(a["x"]+a["width"]/2,a["y"]+a["height"]/2); pg.mouse.down(); pg.mouse.move(a["x"]+30,a["y"]-20,steps=4)
    hidden=tile.evaluate("e=>getComputedStyle(e).visibility")=="hidden"; ghosts=pg.locator(".drag-ghost").count()
    ok("holding a letter: it leaves its place (only ONE letter visible)", hidden and ghosts==1, (hidden,ghosts))
    pg.mouse.move(s["x"]+s["width"]/2,s["y"]+s["height"]/2,steps=10); pg.mouse.up(); pg.wait_for_timeout(60)
    snapping=pg.locator(".drag-ghost").count()==1; pg.wait_for_timeout(250)
    ok("dropped on its slot: it settles into it (not vanishing)", snapping and pg.locator(".drag-ghost").count()==0 and pg.locator(".lslot.filled").count()==1)
    ok("after dropping, nothing stays hidden by mistake", tile.evaluate("e=>getComputedStyle(e).visibility")=="visible")
    # let go in the air: the letter (heavy) falls to the ground; picking it up hides it again from its place
    tile2=pg.locator(".tile:not(.used)").first; a=tile2.bounding_box()
    pg.mouse.move(a["x"]+a["width"]/2,a["y"]+a["height"]/2); pg.mouse.down(); pg.mouse.move(a["x"]+40,a["y"]-60,steps=3); pg.mouse.move(a["x"]+160,a["y"]-160,steps=3); pg.mouse.up(); pg.wait_for_timeout(1600)
    ok("a letter let go in the air falls to the ground (heavy)", pg.locator(".drag-ghost.resting").count()==1)
    q=go("match"); term=pg.locator(".mterm").first; a=term.bounding_box()
    pg.mouse.move(a["x"]+a["width"]/2,a["y"]+a["height"]/2); pg.mouse.down(); pg.mouse.move(a["x"]-60,a["y"]+10,steps=5)
    ok("match: drawing a stem keeps the seed in its place", term.evaluate("e=>getComputedStyle(e).visibility")=="visible" and pg.locator("#ln path").count()>=1)
    pg.mouse.move(5,5,steps=4); pg.mouse.up(); pg.wait_for_timeout(300)
    ok("match: letting the stem go in the air does not throw the seed", pg.locator(".drag-ghost").count()==0)
    b.close()
print("\n".join(res)); print("JS errors:",errs or "none")
