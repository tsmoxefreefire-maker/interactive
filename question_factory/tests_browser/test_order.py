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
rank={"easy":0,"mid":1,"hard":2}
ok("data: challenges easy -> hard in every concept", all([rank[q["difficulty"]] for q in c["questions"]]==sorted(rank[q["difficulty"]] for q in c["questions"]) for l in g["lessons"] for c in l["concepts"]))
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1250,"height":1100}); pg.route("**/fonts.*/**",lambda r:r.abort()); pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(300)
    l=g["lessons"][0]; c=l["concepts"][0]; q=c["questions"][0]
    ok("student: 2nd station locked at the start", "locked" in (pg.locator(".kstone").nth(1).get_attribute("class") or ""))
    ok("student: 2nd challenge locked at the start", "locked" in (pg.locator(".kcard").nth(1).get_attribute("class") or ""))
    pg.locator(".kcard").nth(1).click(); ok("student: a locked challenge does not open (and says why)", pg.locator('.kcard[aria-selected="true"]').get_attribute("data-i")=="0" and "خلّص" in pg.inner_text("#fb"))
    # solve the first challenge (whatever kind it is) quickly via the engine's own data
    t=q["template"]
    if t=="meaning": pg.locator(".fcard").filter(has_text=q["answer"]).first.click(force=True)
    elif t=="match":
        for term,d in q["pairs"]: pg.click(f'.mterm[data-t="{term}"]'); pg.locator(".mdef").filter(has_text=d).first.click()
    elif t=="spell":
        for ch in [x for x in q["word"] if not x.isspace()]: pg.locator(".tile:not(.used)").filter(has_text=ch).first.click()
    elif t=="true_false":
        for s in q["statements"]: pg.click("#myes" if s["answer"] else "#mno"); pg.wait_for_timeout(1450)
    elif t=="memory":
        pg.wait_for_timeout(3150); n=pg.locator(".mc").count(); names=g["names"]
        texts=[pg.locator(".mc .side-b").nth(i).inner_text().strip() for i in range(n)]; isn=[pg.locator(".mc").nth(i).locator(".mi").count()==1 for i in range(n)]
        for cid,m in q["pairs"]:
            i=[k for k,tx in enumerate(texts) if isn[k] and tx.endswith(names[cid])][0]; j=[k for k,tx in enumerate(texts) if not isn[k] and tx==m][0]
            pg.locator(".mc").nth(i).click(); pg.locator(".mc").nth(j).click(); pg.wait_for_timeout(150)
    pg.wait_for_function("document.querySelector('#sol')!==null",timeout=15000)
    ok("student: after finishing, a countdown + 'wait' button", "بننتقل لحالنا" in pg.inner_text("#auto") and pg.locator("#wait").count()==1)
    pg.wait_for_timeout(6500)
    ok("student: it moves on to the next challenge by itself", pg.locator('.kcard[aria-selected="true"]').get_attribute("data-i")=="1", pg.locator('.kcard[aria-selected="true"]').get_attribute("data-i"))
    ok("student: the 2nd challenge is open now", "locked" not in (pg.locator(".kcard").nth(1).get_attribute("class") or ""))
    # 'wait' stops the auto move
    pg.click("#modeBtn"); pg.click("#modeBtn")   # reset view, still student mode
    b.close()
print("\n".join(res)); print("JS errors:",errs or "none")
