import sys
import json,sys
from playwright.sync_api import sync_playwright
import pathlib, urllib.parse, urllib.request
# the page to test: given on the command line, or the player built next to this folder (works on any computer)
_DEFAULT = (pathlib.Path(__file__).resolve().parent.parent / "player" / "player.html").as_uri()
def _path(u): return urllib.request.url2pathname(urllib.parse.urlparse(u).path) if u.startswith("file:") else u
URL=sys.argv[1] if len(sys.argv)>1 and sys.argv[1] else _DEFAULT
errs=[];res=[]
def ok(n,c,x=""): res.append(("✅" if c else "❌")+" "+n+" "+str(x))
html=open(_path(URL),encoding="utf-8").read(); data=json.loads(html.split("const DATA = ")[1].split(";\nconst $")[0]); g=data["graphs"][0]; names=g["names"]
def eng(pg):
    if "وضع المهندس" in pg.inner_text("#modeBtn"): pg.click("#modeBtn")
def goto(pg,li,ci,qi):
    pg.click(f'.les[data-l="{li}"]'); pg.click(f'.station[data-c="{ci}"]'); pg.click(f'.qtab[data-i="{qi}"]'); pg.wait_for_timeout(60)
def wait_sol(pg,t=15000): pg.wait_for_function("document.querySelector('#sol')!==null",timeout=t)
def solve(pg,q):
    t=q["template"]
    if t=="meaning": pg.locator(".fcard").filter(has_text=q["answer"]).first.click(force=True)
    elif t=="match":
        for term,d in q["pairs"]: pg.click(f'.mterm[data-t="{term}"]'); pg.locator(".mdef").filter(has_text=d).first.click()
        wait_sol(pg)
    elif t=="memory":
        pg.wait_for_timeout(3150); cards=pg.locator(".mc"); n=cards.count()
        texts=[pg.locator(".mc .side-b").nth(i).inner_text().strip() for i in range(n)]
        isname=[pg.locator(".mc").nth(i).locator(".mi").count()==1 for i in range(n)]
        for cid,m in q["pairs"]:
            i=[k for k,tx in enumerate(texts) if isname[k] and tx.endswith(names[cid])][0]; j=[k for k,tx in enumerate(texts) if not isname[k] and tx==m][0]
            cards.nth(i).click(); cards.nth(j).click(); pg.wait_for_timeout(150)
        wait_sol(pg)
    elif t=="spell":
        for ch in [c for c in q["word"] if not c.isspace()]: pg.locator(".tile:not(.used)").filter(has_text=ch).first.click()
    elif t=="true_false":
        for s in q["statements"]: pg.click("#myes" if s["answer"] else "#mno"); pg.wait_for_timeout(1450)
        wait_sol(pg)
    elif t=="sequence":
        for cid in q["order"]: pg.click(f'#pool .chip[data-id="{cid}"]')
        pg.click("#chk"); wait_sol(pg,25000)
    elif t=="fix_chain":
        pg.click(f'.wagon[data-i="{q["wrong_index"]}"]'); pg.wait_for_timeout(800); pg.click(f'#opts .chip[data-id="{q["chain"][q["wrong_index"]]}"]'); wait_sol(pg)
    elif t=="prereq":
        for cid in q["correct"]: pg.click(f'.keys .chip[data-id="{cid}"]')
        wait_sol(pg)
    elif t=="unlocks":
        for nxt in q["route"][1:]: pg.click(f'.road[data-id="{nxt}"]'); pg.wait_for_timeout(2400)
        wait_sol(pg)
    elif t=="sort":
        for cid in q["before"]+q["after"]:
            side="before" if cid in q["before"] else "after"
            pg.click(f'#pool .chip[data-id="{cid}"]'); pg.locator(f'.building .floor[data-side="{side}"]:not(.taken)').first.click()
        pg.click("#lock"); wait_sol(pg,30000)
    elif t=="odd_one_out": pg.click(f'.buddy[data-id="{q["intruder"]}"]'); wait_sol(pg)
    elif t=="who_am_i": pg.click(f'.sus[data-id="{q["target"]}"]'); wait_sol(pg)
    elif t=="adjust": pg.locator("#sl").fill(str(q["factor"]["ok_min"])); pg.click("#try")
    elif t=="predict": pg.click(f'#popts .opt[data-i="{q["answer"]}"]'); wait_sol(pg)
def find(t):
    for li,l in enumerate(g["lessons"]):
        for ci,c in enumerate(l["concepts"]):
            for qi,q in enumerate(c["questions"]):
                if q["template"]==t: return li,ci,qi,q
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1250,"height":1150})
    pg.route("**/fonts.*/**",lambda r:r.abort()); pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(300)
    # ---- student (kid) mode first ----
    ok("kid mode by default: welcome + no engineer tabs", pg.locator("#welcome").is_visible() and not pg.locator(".hero").is_visible() and not pg.locator("#below").is_visible())
    ok("lessons in learning order, first open", pg.locator(".kplace").nth(0).get_attribute("class").find("locked")<0)
    locked=pg.locator('.kplace[data-g="0"].locked').count(); ok("later lessons locked by prerequisites", locked==2, locked)
    pg.locator(".kplace").nth(1).click(); ok("locked lesson does not open", "حاجات" in pg.inner_text("#lesson h2"))
    pg.locator(".unlockbtn").first.click(); ok("unlock button opens it", "أجزاء" in pg.inner_text("#lesson h2"))
    ok("kid path, challenge cards, plant pot", pg.locator(".kstone").count()==6 and pg.locator(".kcard").count()>=2 and pg.locator(".potplant").count()==1)
    pg.screenshot(path=str(pathlib.Path(__file__).resolve().parent / "shots" / "k_home.png"))
    # ---- engineer mode: solve everything ----
    eng(pg); ok("engineer mode shows the technical view", pg.locator(".hero").is_visible() and pg.locator("#below").is_visible())
    MODE=sys.argv[2] if len(sys.argv)>2 else "all"
    solved=total=0; failed=[]
    for li,l in enumerate(g["lessons"] if MODE in ("all","solve") else []):
        for ci,c in enumerate(l["concepts"]):
            for qi,q in enumerate(c["questions"]):
                total+=1; goto(pg,li,ci,qi)
                try: solve(pg,q)
                except Exception as e: failed.append((c["concept_id"],q["template"],str(e)[:80])); continue
                if pg.locator("#sol").count()==1: solved+=1
                else: failed.append((c["concept_id"],q["template"]))
    if MODE in ("all","solve"): ok("every challenge solvable", solved==total, f"{solved}/{total} {failed[:4]}")
    if MODE=="solve":
        print("\n".join(res)); print("JS errors:",errs or "none"); b.close(); sys.exit(0)
    # ---- new checks (this round) ----
    li,ci,qi,q=find("odd_one_out"); goto(pg,li,ci,qi)
    anim=pg.evaluate("[...document.querySelectorAll('#q .alive, #q .char')].map(e=>getComputedStyle(e).animationName)")
    ok("B/H: every picture is alive (animated)", len(anim)>0 and all(a!="none" for a in anim), anim[:4])
    li,ci,qi,q=find("meaning"); goto(pg,li,ci,qi)
    hn=pg.locator("#hn").bounding_box(); pg.mouse.move(hn["x"]+20,hn["y"]+10); pg.mouse.down(); pg.mouse.move(hn["x"]+60,hn["y"]-40,steps=4); pg.mouse.move(hn["x"]+200,hn["y"]-120,steps=4); pg.mouse.up()
    pg.wait_for_timeout(500); flying=pg.locator(".drag-ghost").count()==1 and pg.evaluate("document.querySelector('#hn').style.visibility")=="hidden"
    back=False
    for _ in range(40):          # tumbling comes back in ~2s; falling to the ground comes back after 7s
        pg.wait_for_timeout(300)
        if pg.locator(".drag-ghost").count()==0 and pg.evaluate("document.querySelector('#hn').style.visibility")=="": back=True; break
    ok("C: let go in the air -> flies, tumbles, comes back", flying and back, (flying,back))
    li,ci,qi,q=find("who_am_i"); goto(pg,li,ci,qi)
    ok("B: who-am-I suspects are living characters", pg.locator(".sus .char .seye").count()==2*len(q["options"]))
    li,ci,qi,q=find("prereq"); goto(pg,li,ci,qi); pg.click(f'.keys .chip[data-id="{q["correct"][0]}"]')
    ok("E: the door smiles on a right key", "smile" in (pg.get_attribute("#door","class") or ""))
    li,ci,qi,q=find("sort"); goto(pg,li,ci,qi); pg.wait_for_timeout(200)
    car=pg.locator("#car").bounding_box(); fl=pg.locator(".building .floor").first.bounding_box()
    ok("F: the elevator runs on the LEFT", car["x"]+car["width"]<=fl["x"]+2, (car["x"],fl["x"]))
    swap={q["before"][0]:"after",q["after"][0]:"before"}
    for cid in q["before"]+q["after"]:
        side=swap.get(cid,"before" if cid in q["before"] else "after")
        pg.click(f'#pool .chip[data-id="{cid}"]'); pg.locator(f'.building .floor[data-side="{side}"]:not(.taken)').first.click()
    pg.click("#lock"); seen=False
    for _ in range(25):
        pg.wait_for_timeout(300)
        if pg.locator(".catpop .cat2 .eye").count()==2 and pg.locator(".catpop .ctail").count()==1: seen=True; break
    ok("G: the cat has eyes, a tail and shakes its head", seen)
    ok("D: sound is on by default (🔊)", "🔊" in pg.inner_text("#soundBtn"))
    # ---- batch 10 ----
    li,ci,qi,q=find("true_false"); goto(pg,li,ci,qi)
    ok("35: two hungry monsters + the concept says the sentence", pg.locator(".monster").count()==2 and pg.locator("#spk .char").count()==1 and len(pg.inner_text("#tfc"))>5)
    c0=q["statements"][0]; pg.click("#mno" if c0["answer"] else "#myes"); pg.wait_for_timeout(300)
    ok("35: wrong -> the monster spits it out", "spit" in (pg.get_attribute("#mno" if c0["answer"] else "#myes","class") or ""))
    ok("30: no number slider in a science (memorise/understand) book", all(q2["template"]!="adjust" for l in g["lessons"] for c in l["concepts"] for q2 in c["questions"]))
    li,ci,qi,q=find("predict"); goto(pg,li,ci,qi)
    ok("39: 'what happens if…' shows a village of characters, no hints", pg.locator(".villager").count()==1+len(q["affected"])+len(q["unaffected"]) and pg.locator(".villager .droop, .villager.tired").count()==0)
    wrong=[i for i in range(len(q["options"])) if i!=q["answer"]][0]; pg.click(f'#popts .opt[data-i="{wrong}"]')
    ok("39: a wrong guess is disabled, try again", pg.locator(f'#popts .opt[data-i="{wrong}"]').is_disabled())
    pg.click(f'#popts .opt[data-i="{q["answer"]}"]'); pg.wait_for_timeout(1000+700*len(q["affected"]))
    ok("39: dominoes: it disappears, who needs it gets tired, the others are fine", pg.locator(f'.villager[data-id="{q["target"]}"].poof').count()==1 and pg.locator(".villager.tired").count()==len(q["affected"]) and pg.locator(f'.villager[data-id="{q["unaffected"][0]}"] .char[data-mood="laugh"]').count()==1)
    pg.screenshot(path=str(pathlib.Path(__file__).resolve().parent / "shots" / "k_predict.png"))
    li,ci,qi,q=find("who_am_i"); goto(pg,li,ci,qi)
    ok("38: the masked character says the clue", q["clues"][0] in pg.inner_text("#say") and "؟؟؟" not in pg.inner_text("#q"))
    li,ci,qi,q=find("odd_one_out"); goto(pg,li,ci,qi)
    ok("32: the group has a name from the lesson", "كلهم من «" in pg.inner_text(".qtext"))
    li,ci,qi,q=find("fix_chain"); goto(pg,li,ci,qi); pg.click(f'.wagon[data-i="{q["wrong_index"]}"]'); pg.wait_for_timeout(250)
    ok("29: the caught wagon blushes and sweats", pg.locator(".wagon.busted .sweatdrop").count()==1)
    li,ci,qi,q=find("odd_one_out"); goto(pg,li,ci,qi)
    emoji_left=pg.evaluate("[...document.querySelectorAll('#q .buddy .alive, #lesson .alive')].filter(e=>!e.classList.contains('art')).length")
    ok("M: concept pictures are drawn (no emoji left on characters)", pg.locator("#q .buddy svg.ch").count()>=4 and emoji_left==0, emoji_left)
    pg.mouse.move(5,5); pg.wait_for_timeout(120); t1=pg.evaluate("document.querySelector('#q .buddy .spupil').getAttribute('transform')")
    pg.mouse.move(1100,900); pg.wait_for_timeout(120); t2=pg.evaluate("document.querySelector('#q .buddy .spupil').getAttribute('transform')")
    ok("M: drawn characters' eyes follow the mouse/finger", t1!=t2, (t1,t2))
    li,ci,qi,q=find("odd_one_out"); goto(pg,li,ci,qi); pg.hover(f'.buddy[data-id="{q["intruder"]}"]'); pg.wait_for_timeout(200)
    ok("I: the intro is a complete sentence", "…" not in pg.inner_text(f'.buddy[data-id="{q["intruder"]}"] .bsay') and len(pg.inner_text(f'.buddy[data-id="{q["intruder"]}"] .bsay'))>8)
    ok("I: faces are all the same design (round face + picture hat)", pg.locator(".buddy .char svg.ch.big").count()==4)
    # ---- throwing: heavy things fall (10 s), light things float like in space and can be caught in the air ----
    li,ci,qi,q=find("sequence"); goto(pg,li,ci,qi)
    c=pg.locator("#pool .chip:not(.used)").first; bb=c.bounding_box()
    pg.mouse.move(bb["x"]+10,bb["y"]+10); pg.mouse.down(); pg.mouse.move(bb["x"]+60,bb["y"]-40,steps=3); pg.mouse.move(bb["x"]+160,bb["y"]-140,steps=3); pg.mouse.up()
    pg.wait_for_timeout(1800); r1=pg.locator(".drag-ghost.resting").count()==1
    pg.wait_for_timeout(7000); r2=pg.locator(".drag-ghost.resting").count()==1
    pg.wait_for_timeout(4800); r3=pg.locator(".drag-ghost").count()==0
    ok("J: a stone (heavy) falls to the ground, stays 10 s, then goes home", r1 and r2 and r3, (r1,r2,r3))
    c=pg.locator("#pool .chip:not(.used)").first; bb=c.bounding_box()
    pg.mouse.move(bb["x"]+10,bb["y"]+10); pg.mouse.down(); pg.mouse.move(bb["x"]+60,bb["y"]-40,steps=3); pg.mouse.move(bb["x"]+160,bb["y"]-140,steps=3); pg.mouse.up()
    for _ in range(20):
        pg.wait_for_timeout(250)
        if pg.locator(".drag-ghost.resting").count(): break
    g2=pg.locator(".drag-ghost.resting").first.bounding_box(timeout=2000); pk=pg.locator(".plank").first.locator(".slab").bounding_box()
    pg.mouse.move(g2["x"]+g2["width"]/2,g2["y"]+g2["height"]/2); pg.mouse.down(); pg.mouse.move(g2["x"]+30,g2["y"]-20,steps=4); pg.mouse.move(pk["x"]+pk["width"]/2,pk["y"]+pk["height"]/2,steps=12); pg.mouse.up(); pg.wait_for_timeout(300)
    ok("J: picked up from the ground and used on the bridge", pg.locator("#pool .chip.used").count()==1)
    li,ci,qi,q=find("meaning"); goto(pg,li,ci,qi); pg.evaluate("document.querySelectorAll('.face').forEach(f=>f.style.animation='none')")
    hn=pg.locator("#hn").bounding_box(); pg.mouse.move(hn["x"]+20,hn["y"]+10); pg.mouse.down(); pg.mouse.move(hn["x"]+70,hn["y"]-30,steps=3); pg.mouse.move(hn["x"]+190,hn["y"]-110,steps=3); pg.mouse.up()
    pg.wait_for_timeout(700); p1=pg.locator(".drag-ghost").bounding_box(); fl=pg.locator(".drag-ghost.floating").count()==1
    pg.wait_for_timeout(900); p2=pg.locator(".drag-ghost").bounding_box()
    vh=pg.evaluate("innerHeight")
    ok("K: a name (light) floats in the air like in space (moving, not on the ground)", fl and p1 and p2 and (abs(p1["x"]-p2["x"])+abs(p1["y"]-p2["y"]))>10 and p2["y"]<vh-60, (fl,))
    # it keeps moving, so "catch" it exactly where it is right now (a real finger has to aim, a test cannot)
    face=pg.locator(".fcard").filter(has_text=q["answer"]).first.bounding_box()
    xy=pg.evaluate("(()=>{const g=document.querySelector('.drag-ghost.floating');const r=g.getBoundingClientRect();const x=r.left+r.width/2,y=r.top+r.height/2;g.dispatchEvent(new PointerEvent('pointerdown',{clientX:x,clientY:y,bubbles:true,pointerId:1}));return [x,y];})()")
    pg.mouse.move(xy[0],xy[1]); pg.mouse.down(); pg.mouse.move(xy[0]+20,xy[1]+20,steps=3); pg.mouse.move(face["x"]+face["width"]/2,face["y"]+face["height"]/2,steps=12); pg.mouse.up(); pg.wait_for_timeout(400)
    ok("K: caught in the air and dropped on the right face", pg.locator("#sol").count()==1)
    # ---- the 🔓 demo switch ----
    pg.click("#modeBtn"); pg.wait_for_timeout(200)          # back to student mode
    before=pg.locator(".kstone.locked").count()+pg.locator(".kplace.locked").count()
    pg.click("#openAll"); pg.wait_for_timeout(200)
    after=pg.locator(".kstone.locked").count()+pg.locator(".kplace.locked").count()+pg.locator(".kcard.locked").count()
    ok("L: 🔓 opens every lesson, station and challenge for a demo", before>0 and after==0, (before,after))
    pg.click("#openAll"); pg.wait_for_timeout(200); ok("L: 🔒 locks them again", pg.locator(".kstone.locked").count()+pg.locator(".kplace.locked").count()+pg.locator(".kcard.locked").count()>0)
    pg.click("#modeBtn"); pg.wait_for_timeout(200)          # engineer mode for the rest
    # ---- the notes, one by one ----
    li,ci,qi,q=find("match"); goto(pg,li,ci,qi)
    ok("21: each concept has its own picture", len({pg.locator(".mterm .ic").nth(i).inner_html() for i in range(pg.locator(".mterm").count())})==pg.locator(".mterm").count())
    for term,d in q["pairs"]: pg.click(f'.mterm[data-t="{term}"]'); pg.locator(".mdef").filter(has_text=d).first.click()
    pg.wait_for_timeout(500); ok("21: the garden wakes up (sun + butterflies)", pg.locator("#party .sun").count()==1 and pg.locator("#party .flyer").count()>=4); pg.screenshot(path=str(pathlib.Path(__file__).resolve().parent / "shots" / "k_match.png"))
    li,ci,qi,q=find("memory"); goto(pg,li,ci,qi); ok("26: 3-second peek first", pg.locator(".mc.open").count()==len(q["pairs"])*2)
    pg.wait_for_timeout(3200); cards=pg.locator(".mc"); texts=[pg.locator(".mc .side-b").nth(i).inner_text().strip() for i in range(cards.count())]
    isname=[pg.locator(".mc").nth(i).locator(".mi").count()==1 for i in range(cards.count())]
    a=[k for k,tx in enumerate(texts) if isname[k] and tx.endswith(names[q["pairs"][0][0]])][0]; bm=[k for k,tx in enumerate(texts) if not isname[k] and tx==q["pairs"][1][1]][0]
    cards.nth(a).click(); cards.nth(bm).click(); pg.wait_for_timeout(2500)
    ok("26: a wrong pair stays open (time to read)", pg.locator(".mc.open:not(.done)").count()==2); pg.screenshot(path=str(pathlib.Path(__file__).resolve().parent / "shots" / "k_mem.png"))
    li,ci,qi,q=find("fix_chain"); goto(pg,li,ci,qi)
    ok("19: story + numbers + arrows + first/last", pg.locator(".story").count()==1 and pg.locator(".wagon .wn").count()==len(q["chain"]) and pg.locator(".tarrow").count()==len(q["chain"]) and pg.locator(".wtag").count()==2)
    pg.screenshot(path=str(pathlib.Path(__file__).resolve().parent / "shots" / "k_train.png"))
    li,ci,qi,q=find("odd_one_out"); goto(pg,li,ci,qi); pg.hover(f'.buddy[data-id="{q["family"][0]}"]'); pg.wait_for_timeout(150)
    ok("20: everyone sad (living faces) + introduces itself", pg.locator('.buddy .char[data-mood="sad"]').count()>=len(q["family"]) and pg.locator(".buddy .char .seye").count()==2*(len(q["family"])+1) and len(pg.locator(f'.buddy[data-id="{q["family"][0]}"] .bsay').inner_text())>3)
    pg.click(f'.buddy[data-id="{q["family"][1]}"]'); ok("20: wrong pull -> 'أنا من العيلة'", "من العيلة" in pg.inner_text("#q"))
    pg.wait_for_timeout(1300); pg.click(f'.buddy[data-id="{q["intruder"]}"]'); pg.wait_for_timeout(1300)
    ok("20: weed flies, family celebrates differently", pg.locator(".buddy.pulled").count()==1 and len({c for i in range(pg.locator(".buddy").count()) for c in (pg.locator(".buddy").nth(i).get_attribute("class") or "").split() if c in ("laugh","jump","dance","clap")})>=3)
    ok("new: family smiles after the weed is gone", pg.locator('.buddy .char[data-mood="happy"]').count()==len(q["family"]))
    pg.screenshot(path=str(pathlib.Path(__file__).resolve().parent / "shots" / "k_odd.png"))
    anims=pg.evaluate("[...document.querySelectorAll('.alive, .char')].map(e=>getComputedStyle(e).animationName).filter(n=>n&&n!=='none').length")
    ok("new: pictures are alive (animated)", anims>=3, anims)
    li,ci,qi,q=find("meaning"); goto(pg,li,ci,qi); pg.evaluate("document.querySelectorAll('.face').forEach(f=>f.style.animation='none')")
    a=pg.locator("#hn").bounding_box(); pg.mouse.move(a["x"]+a["width"]/2,a["y"]+a["height"]/2); pg.mouse.down()
    pg.mouse.move(a["x"]+60,a["y"]-40,steps=4); pg.mouse.move(a["x"]+160,a["y"]-140,steps=4); pg.mouse.up()
    pg.wait_for_timeout(400); flying=pg.locator(".drag-ghost").count()==1 and pg.evaluate("getComputedStyle(document.querySelector('#hn')).visibility")=="hidden"
    back=False
    for _ in range(40):          # tumbling: back in ~2s · falling to the ground: back after 7s
        pg.wait_for_timeout(300)
        if pg.locator(".drag-ghost").count()==0 and pg.evaluate("getComputedStyle(document.querySelector('#hn')).visibility")=="visible": back=True; break
    ok("new: the name flies & tumbles when let go in the air, then comes back", flying and back, (flying,back))
    li,ci,qi,q=find("who_am_i"); goto(pg,li,ci,qi)
    ok("18: clear intro + 'if you guess now'", "اقرأ التلميح" in pg.inner_text(".how") and "لو حزرت هلأ" in pg.inner_text("#now"))
    pg.click(f'.sus[data-id="{q["target"]}"]'); wait_sol(pg)
    ok("18: solution shows only the clues seen", pg.locator("#sol li").count()==1+len(q["solution"])); pg.screenshot(path=str(pathlib.Path(__file__).resolve().parent / "shots" / "k_who.png"))
    li,ci,qi,q=find("unlocks"); goto(pg,li,ci,qi); ok("25/33: the fox stands on a WRONG road (4 roads)", pg.locator(".road .fox").count()==1 and pg.locator(".road").count()==4 and pg.locator(".road:has(.fox)").get_attribute("data-id")!=q["route"][1])
    pg.click("#owl"); ok("25: the owl hints (not answers)", pg.inner_text("#owlsay").startswith("🦉") and names[q["route"][1]] not in pg.inner_text("#owlsay"))
    wrong=[o for o in q["junctions"][0] if o!=q["route"][1]][0]; pg.click(f'.road[data-id="{wrong}"]')
    ok("24/25: wrong road crumbles, fox laughs", pg.locator(".road.broken").count()==1 and "هههه" in pg.inner_text("#cross")); pg.screenshot(path=str(pathlib.Path(__file__).resolve().parent / "shots" / "k_road.png"))
    pg.click(f'.road[data-id="{q["route"][1]}"]'); pg.wait_for_timeout(300)
    ok("A: each crossroads asks 'مين بيحتاج' and shows WHY", "مين بيحتاج" in pg.inner_text("#cross") and pg.locator("#cross .why").count()==1)
    pg.wait_for_timeout(2200)
    for nxt in q["route"][2:]: pg.click(f'.road[data-id="{nxt}"]'); pg.wait_for_timeout(2400)
    ok("24: the journey reaches the end 🏁", "وصلت" in pg.inner_text("#cross"))
    li,ci,qi,q=find("sort"); goto(pg,li,ci,qi)
    swap={q["before"][0]:"after",q["after"][0]:"before"}           # two on purpose on the wrong side
    for cid in q["before"]+q["after"]:
        side=swap.get(cid,"before" if cid in q["before"] else "after")
        pg.click(f'#pool .chip[data-id="{cid}"]'); pg.locator(f'.building .floor[data-side="{side}"]:not(.taken)').first.click()
    ok("23: free placement, confirm enabled only when all placed", not pg.locator("#lock").is_disabled())
    tops=[]
    pg.click("#lock")
    for _ in range(14): pg.wait_for_timeout(400); tops.append(pg.evaluate("parseFloat(document.querySelector('#car').style.top)"))
    bh=pg.evaluate("document.querySelector('#bld').offsetHeight")
    ok("22: the elevator stays inside the building", max(tops)<=bh and min(tops)>=0, (min(tops),max(tops),bh))
    cats=0
    for _ in range(30):
        pg.wait_for_timeout(300); cats=max(cats,pg.locator(".catpop").count())
        if not pg.locator("#lock").is_disabled() or pg.locator("#sol").count(): break
    ok("22: the cat pops out on the wrong floor", cats>=1)
    pg.wait_for_timeout(600)
    back=pg.locator("#pool .chip:not(.used)").count(); stay=pg.locator(".building .floor.taken").count()
    ok("23: the 2 wrong ones back to the lobby, the right ones stay", back==2 and stay==len(q["before"])+len(q["after"])-2, (back,stay))
    pg.screenshot(path=str(pathlib.Path(__file__).resolve().parent / "shots" / "k_lift.png"))
    li,ci,qi,q=find("sequence"); goto(pg,li,ci,qi)
    for cid in reversed(q["order"]): pg.click(f'#pool .chip[data-id="{cid}"]')
    pg.click("#chk"); ys=[]
    scared=False;cracked=False;fell=False;carfell=False
    for _ in range(60):
        pg.wait_for_timeout(100)
        scared=scared or (pg.get_attribute("#driver","data-mood")=="o" and pg.get_attribute("#sweat","opacity")=="1")
        cracked=cracked or pg.get_attribute('.plank[data-i="0"] .crack',"opacity")=="1"
        fell=fell or "translateY(80px)" in (pg.get_attribute('.plank[data-i="0"]',"style") or "")
        t=pg.get_attribute("#car","transform") or ""
        try: carfell=carfell or float(t.split("translate(")[1].split(")")[0].split()[1])>90
        except Exception: pass
        if fell and carfell: break
    ok("37: the seed gets scared near the weak part", scared)
    ok("37: the weak part turns red and cracks", cracked)
    ok("37: the part breaks and the car falls with it", fell and carfell, (fell,carfell))
    pg.screenshot(path=str(pathlib.Path(__file__).resolve().parent / "shots" / "k_bridge.png"))
    # ---- new: everything alive, buddies with eyes, the name card flies ----
    li,ci,qi,q=find("odd_one_out"); goto(pg,li,ci,qi)
    ok("alive: buddies have eyes and a moving picture hat", pg.locator(".buddy .char .seye").count()==2*(len(q["family"])+1) and pg.locator(".buddy .char svg.ch.big").count()==len(q["family"])+1)
    ok("alive: every concept picture moves", pg.evaluate("[...document.querySelectorAll('#q .alive, #q .char')].every(a=>getComputedStyle(a).animationName!=='none')") and pg.locator("#q .alive, #q .char").count()>=4)
    li,ci,qi,q=find("meaning"); goto(pg,li,ci,qi); pg.evaluate("document.querySelectorAll('.face').forEach(f=>f.style.animation='none')")
    a=pg.locator("#hn").bounding_box(); pg.mouse.move(a["x"]+a["width"]/2,a["y"]+a["height"]/2); pg.mouse.down()
    for k in range(1,8): pg.mouse.move(a["x"]+a["width"]/2+k*25,a["y"]+a["height"]/2-k*30,steps=2)
    pg.mouse.up(); pg.wait_for_timeout(500)
    ok("fly: let go in the air -> the card tumbles around", pg.locator(".drag-ghost").count()==1 and "rotate(" in (pg.locator(".drag-ghost").get_attribute("style") or ""))
    home=False
    for _ in range(40):
        pg.wait_for_timeout(300)
        if pg.locator(".drag-ghost").count()==0 and pg.evaluate("document.querySelector('#hn').style.visibility")=="": home=True; break
    ok("fly: then it comes back home (tumble ~2s, ground 7s)", home)
    # ---- kid mode after finishing: stickers + plant ----
    pg.click("#modeBtn"); pg.wait_for_timeout(200)
    if MODE!="notes": ok("28: stickers + growing plant in student mode", pg.locator(".album .stk").count()>=1 and pg.locator(".kplace.done").count()>=1)
    pg.screenshot(path=str(pathlib.Path(__file__).resolve().parent / "shots" / "k_home2.png"))
    # ---- phone ----
    ctx=b.new_context(viewport={"width":390,"height":844},has_touch=True,is_mobile=True,color_scheme="dark"); m=ctx.new_page()
    m.route("**/fonts.*/**",lambda r:r.abort()); m.on("pageerror",lambda e:errs.append(str(e))); m.goto(URL); m.wait_for_timeout(300)
    ok("phone: student home fits", m.evaluate("document.documentElement.scrollWidth")<=392); m.screenshot(path=str(pathlib.Path(__file__).resolve().parent / "shots" / "k_phone.png"),full_page=True)
    eng(m); overflow=[]
    for t in ["meaning","match","memory","spell","true_false","sequence","fix_chain","prereq","unlocks","sort","odd_one_out","who_am_i","predict"]:
        li,ci,qi,q=find(t); goto(m,li,ci,qi); w=m.evaluate("document.documentElement.scrollWidth")
        if w>392: overflow.append((t,w))
    ok("phone: no sideways scroll in any game", not overflow, overflow)
    b.close()
print("\n".join(res)); print("JS errors:",errs or "none")
