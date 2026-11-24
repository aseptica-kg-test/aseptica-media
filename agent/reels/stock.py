# Реалистичные ролики: настоящие видео с Pixabay + голос + надписи + упаковка в финале (решение владельца 24.11.2026)
import os, json, random, subprocess, urllib.request, urllib.parse, urllib.error, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import styles
from styles import F, wrap, ease, back, tint, shade, paste_a, grad, W, H
PEOPLE=("woman","man","person","people","girl","boy","face","portrait","model","businesswoman","businessman","female","male","eye","hand","finger","lady","guy","student")
OBJ_FALLBACK=["laptop desk","snow window","cup tea window","houseplant window","water drops"]
FALLBACK=["woman working laptop office","winter window home","man computer screen night","woman drinking tea window","city wind street","air conditioner office"]
BANNED=("child","kid","baby","girl","boy","hospital","surgery","injection","syringe","blood","doctor","nurse","pill","medicine",
        "fire","flame","fireplace","burn","headache","stress","pain","sad","cry","tired","depress","sick","ill","migraine","covid","mask","quarantine","pandemic","massage","spa","therapy","treatment","eyeball","macro","iris","pupil","apple","macbook","iphone","ipad","samsung","logo","brand","nike","coca")
def search(q,key,used,nopeople=False):
    url="https://pixabay.com/api/videos/?"+urllib.parse.urlencode({"key":key,"q":q[:90],"safesearch":"true","per_page":30,"video_type":"film","lang":"en"})
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AsepticaReels/1.0","Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=60) as r: hits=json.load(r).get("hits",[])
    except urllib.error.HTTPError as e: raise RuntimeError("HTTP %s: %s"%(e.code,e.read()[:200].decode("utf-8","ignore")))
    ok=[]
    for h in hits:
        tags=h.get("tags","").lower()
        if h["id"] in used or any(b in tags for b in BANNED) or h.get("duration",0)<4: continue
        if nopeople and any(p in tags for p in PEOPLE): continue
        v=h["videos"].get("large") or {}
        if not v.get("url") or v.get("width",0)<1280: v=h["videos"].get("medium") or {}
        if not v.get("url"): continue
        words=[w for w in q.lower().split() if len(w)>3 and w not in ("person","people","close","with","near","at","the","modern","cozy","home","indoor","indoors","interior","young","happy","calm")]
        score=sum(1 for w in words if w[:5] in tags)   # blinking ≈ blink
        if words and score<len(words): continue   # видео должно подходить по ВСЕМ значимым словам запроса
        ok.append((score,h["id"],v["url"],tags))
    ok.sort(key=lambda x:-x[0]); return [x[1:] for x in ok]
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"..",".."))
GENERIC=("person","people","close","with","near","at","the","modern","cozy","home","indoor","indoors","interior","young","happy","calm")
def lib_match(q,used,people=True):
    lf=os.path.join(ROOT,"reels","stock_lib","lib.json")
    if not os.path.exists(lf): return []
    words=[w for w in q.lower().split() if len(w)>3 and w not in GENERIC]
    LL=[x for x in json.load(open(lf,encoding="utf-8")) if x.get("people",True)==people]
    return [x for x in LL if x["file"] not in used and words and any(w[:5] in x["tags"].lower() for w in words if w[:5] in ("radia","heate","batte"))] or \
           [x for x in LL if x["file"] not in used and words and all(w[:5] in x["tags"].lower() for w in words)]
def fetch(q,key,used,rnd,idx,nopeople=False):
    if True:
        lib=lib_match(q,used,people=not nopeople)   # сначала свои видео (папка reels/stock_lib)
        if lib:
            pick=rnd.choice(lib); print("Своё видео:",q,"→",pick["file"]); return (pick["file"],os.path.join(ROOT,pick["file"]),q)
    ws=q.split()
    tries=[q]+[" ".join(w for w in ws if w!=x) for x in ws if len(ws)>2 and x!=max(ws,key=len)]   # упрощаем запрос, главное слово оставляем
    for qq in tries:
        try: c=search(qq,key,used,nopeople)
        except Exception as e: print("Pixabay:",qq,e); c=[]
        if c:
            pick=rnd.choice(c[:3]); fn="/tmp/reel/clip%d.mp4"%idx
            req=urllib.request.Request(pick[1],headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req,timeout=120) as r, open(fn,"wb") as f: f.write(r.read())
            print("Видео:",qq,"→",pick[0],pick[2]); return (pick[0],fn,qq)
    print("Pixabay: нет видео для",q); return None
def get_clips(queries,key,used,seed=0,theme=""):
    """2 видео: 1) один человек в жизненной ситуации (начало и середина), 2) спокойный кадр БЕЗ людей (конец) — решение владельца 24.11.2026"""
    rnd=random.Random(seed); q=list(queries)+["",""]
    a=None; b=None
    lf=os.path.join(ROOT,"reels","stock_lib","lib.json")
    def own(people):   # свои видео по теме ролика (решение владельца 24.11.2026) — всегда в приоритете
        if not (theme and os.path.exists(lf)): return None
        L=[x for x in json.load(open(lf,encoding="utf-8")) if x.get("people",True)==people and any(k in theme.lower() for k in x.get("themes",[]))]
        fresh=[x for x in L if x["file"] not in used] or L
        if not fresh: return None
        p=rnd.choice(fresh); print("Своё видео по теме:",p["file"]); return (p["file"],os.path.join(ROOT,p["file"]),"тема")
    a=own(True); b=own(False)
    for qq in ([] if a else [q[0]]+FALLBACK):
        if qq and (a:=fetch(qq,key,used,rnd,0)): break
    for qq in ([] if b else [q[1]]+OBJ_FALLBACK):
        if qq and (b:=fetch(qq,key,used|{a[0] if a else 0},rnd,1,nopeople=True)): break
    if not a or not b: raise RuntimeError("Pixabay: не удалось подобрать видео")
    return [a,b]
def frames(fn,nfr,fps,slow=1.0):
    """кадры клипа 1080x1920 (обрезка по центру + медленное приближение), цикл если клип короче"""
    vf="setpts=%.3f*PTS,scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,fps=%d"%(slow,int(W*1.12),int(H*1.12),int(W*1.12),int(H*1.12),fps)
    p=subprocess.Popen(["ffmpeg","-loglevel","error","-stream_loop","-1","-i",fn,"-an","-vf",vf,"-frames:v",str(nfr),"-f","rawvideo","-pix_fmt","rgb24","-"],stdout=subprocess.PIPE)
    bw,bh=int(W*1.12),int(H*1.12); sz=bw*bh*3
    for i in range(nfr):
        buf=p.stdout.read(sz)
        if len(buf)<sz: break
        im=Image.frombuffer("RGB",(bw,bh),buf,"raw","RGB",0,1)
        z=1.12-0.10*(i/max(1,nfr-1)); cw,ch=int(W*z),int(H*z); x0=(bw-cw)//2; y0=(bh-ch)//2
        yield im.crop((x0,y0,x0+cw,y0+ch)).resize((W,H),Image.BILINEAR)
    p.stdout.close(); p.wait()
SHADE=None
def shade_layer():
    global SHADE
    if SHADE is None:
        a=np.zeros((H,1),np.float32); y=np.arange(H)[:,None]
        a=np.maximum(np.clip(1-y/700,0,1)*150,np.clip((y-1250)/670,0,1)*170)
        A=np.repeat(a,W,axis=1).astype(np.uint8); SHADE=Image.fromarray(np.dstack([np.zeros((H,W,3),np.uint8),A]),"RGBA")
    return SHADE
def subs(im,ctx,t):
    """субтитры без плашки: белые буквы с тенью и тонкой обводкой (решение владельца 24.11.2026)"""
    d=ImageDraw.Draw(im,"RGBA")
    for st,e,txt in ctx["sentences"]:
        if st<=t<e:
            f=F("Bold",44); L=wrap(d,txt,f,W-160)
            if len(L)>3:
                parts=[L[i:i+2] for i in range(0,len(L),2)]; L=parts[min(len(parts)-1,int((t-st)/(e-st)*len(parts)))]
            yy=1700-len(L)*58
            for ln in L:
                x=(W-d.textlength(ln,font=f))/2
                d.text((x+2,yy+3),ln,font=f,fill=(0,0,0,150))
                d.text((x,yy),ln,font=f,fill=(255,255,255),stroke_width=2,stroke_fill=(0,0,0,110)); yy+=58
def overlay(im,ctx,t,line,lt):
    im=im.convert("RGBA"); im.alpha_composite(shade_layer()); d=ImageDraw.Draw(im,"RGBA")
    lw=ctx["logo"].width; paste_a(im,ctx["logo"],((W-lw)//2,70)); d=ImageDraw.Draw(im,"RGBA")
    if line:
        a=ease((lt-0.2)/0.5); off=int((1-a)*50); f=F("Black",88); L=wrap(d,line,f,W-140); y=250+off
        for ln in L:
            x=(W-d.textlength(ln,font=f))/2
            d.text((x+3,y+4),ln,font=f,fill=(0,0,0,int(120*a))); d.text((x,y),ln,font=f,fill=(255,255,255,int(255*a))); y+=104
    subs(im,ctx,t); styles.footer(im,ctx); return im
def final_frame(ctx,t,lt):
    c=ctx["color"]; im=grad(tint(c,0.15),shade(c,0.35)).convert("RGBA"); d=ImageDraw.Draw(im,"RGBA")
    lw=ctx["logo"].width; paste_a(im,ctx["logo"],((W-lw)//2,70)); d=ImageDraw.Draw(im,"RGBA")
    k=back(lt/0.8); ang=math.sin(lt*2.0)*3; b=ctx["box"].rotate(ang,resample=Image.BICUBIC,expand=True)
    d.ellipse([W/2-380,640,W/2+380,1400],fill=tint(c,0.35)+(120,))
    sh=Image.new("RGBA",(W,H),(0,0,0,0)); ImageDraw.Draw(sh).ellipse([W/2-260,1410,W/2+260,1480],fill=(0,0,0,90)); im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(20)))
    bx=W/2+(1-k)*900; paste_a(im,b,(int(bx-b.width/2),int(1440-b.height))); d=ImageDraw.Draw(im,"RGBA")
    a=ease((lt-0.4)/0.4); f=F("Black",96); tw=d.textlength(ctx["name"],font=f)
    d.rounded_rectangle([(W-tw)/2-40,300,(W+tw)/2+40,430],65,fill=(255,255,255,int(255*a))); d.text(((W-tw)/2,312),ctx["name"],font=f,fill=c+(int(255*a),))
    f2=F("Bold",50); s="Aseptica — забота о глазах"; d.text(((W-d.textlength(s,font=f2))/2,470),s,font=f2,fill=(255,255,255,int(255*a)))
    talking=any(st<=t<e for st,e,_ in ctx["sentences"])
    f3=F("SemiBold",40); s3="Перед применением прочитайте инструкцию"
    if not talking: d.text(((W-d.textlength(s3,font=f3))/2,1530),s3,font=f3,fill=(255,255,255,int(255*a)))
    if talking: subs(im,ctx,t)   # если голос ещё звучит — субтитры поверх упаковки
    styles.footer(im,ctx); return im
def clip_len(fn):
    try: return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",fn],capture_output=True,text=True).stdout.strip())
    except Exception: return 0
def render(ctx,clips,fpath,fps):
    """ctx['scene_ends']: [смена надписи 1→2, конец видео с человеком, конец видео без людей, финал]"""
    ends=ctx["scene_ends"]; dur=ctx["dur"]; nfr=int(dur*fps); fi=0; XF=int(0.4*fps); prev=None; prev_raw=None
    parts=[(0,ends[1],clips[0]),(ends[1],ends[2],clips[1]),(ends[2],dur,None)]
    for pi,(a,b,clip) in enumerate(parts):
        n=(int(round(b*fps)) if pi<2 else nfr)-fi
        gen=None
        if clip:
            need=b-a; L=clip_len(clip[1]); slow=min(2.0,max(1.0,need/L)) if L>0 else 1.0
            gen=frames(clip[1],n,fps,slow)
        for j in range(n):
            t=fi/fps
            if clip:
                raw=next(gen,None) or prev_raw; prev_raw=raw
                li=0 if t<ends[0] else 1 if t<ends[1] else 2; ls=[0,ends[0],ends[1]][li]
                fr=overlay(raw,ctx,t,ctx["lines"][li],t-ls)
            else: fr=final_frame(ctx,t,t-a)
            if prev is not None and j<XF: fr=Image.blend(prev,fr,(j+1)/(XF+1))   # плавный переход
            if j==n-1: prev=fr
            fr.convert("RGB").save(fpath%fi,quality=88); fi+=1
        if gen: gen.close()
