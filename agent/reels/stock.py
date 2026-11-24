# Реалистичные ролики: настоящие видео с Pixabay + голос + надписи + упаковка в финале (решение владельца 24.11.2026)
import os, json, random, subprocess, urllib.request, urllib.parse, urllib.error, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import styles
from styles import F, wrap, ease, back, tint, shade, paste_a, grad, W, H
FALLBACK=["woman working laptop office","winter window home","man computer screen night","woman drinking tea window","city wind street","air conditioner office"]
BANNED=("child","kid","baby","girl","boy","hospital","surgery","injection","syringe","blood","doctor","nurse","pill","medicine")
def search(q,key,used):
    url="https://pixabay.com/api/videos/?"+urllib.parse.urlencode({"key":key,"q":q[:90],"safesearch":"true","per_page":30,"video_type":"film","lang":"en"})
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AsepticaReels/1.0","Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=60) as r: hits=json.load(r).get("hits",[])
    except urllib.error.HTTPError as e: raise RuntimeError("HTTP %s: %s"%(e.code,e.read()[:200].decode("utf-8","ignore")))
    ok=[]
    for h in hits:
        tags=h.get("tags","").lower()
        if h["id"] in used or any(b in tags for b in BANNED) or h.get("duration",0)<4: continue
        v=h["videos"].get("large") or {}
        if not v.get("url") or v.get("width",0)<1280: v=h["videos"].get("medium") or {}
        if not v.get("url"): continue
        words=[w for w in q.lower().split() if len(w)>3 and w not in ("person","woman","people","close","with","near","at","the")]
        score=sum(1 for w in words if w[:5] in tags)   # blinking ≈ blink
        if words and score==0: continue          # видео должно подходить по смыслу хотя бы одним словом
        ok.append((score,h["id"],v["url"],tags))
    ok.sort(key=lambda x:-x[0]); return [x[1:] for x in ok]
def get_clips(queries,key,used,n=3,seed=0):
    rnd=random.Random(seed); out=[]
    qs=list(queries[:n])+FALLBACK
    for q in qs:
        if len(out)>=n: break
        try: c=search(q,key,used|{x[0] for x in out})
        except Exception as e: print("Pixabay:",q,e); continue
        if not c: print("Pixabay: нет видео для",q); continue
        pick=rnd.choice(c[:3]); fn="/tmp/reel/clip%d.mp4"%len(out)
        req=urllib.request.Request(pick[1],headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req,timeout=120) as r, open(fn,"wb") as f: f.write(r.read())
        print("Видео:",q,"→",pick[0],pick[2]); out.append((pick[0],fn,q))
    if len(out)<n: raise RuntimeError("Pixabay: не удалось найти %d видео"%n)
    return out
def frames(fn,nfr,fps):
    """кадры клипа 1080x1920 (обрезка по центру + медленное приближение), цикл если клип короче"""
    vf="scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,fps=%d"%(int(W*1.12),int(H*1.12),int(W*1.12),int(H*1.12),fps)
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
def overlay(im,ctx,t,line,lt):
    im=im.convert("RGBA"); im.alpha_composite(shade_layer()); d=ImageDraw.Draw(im,"RGBA")
    lw=ctx["logo"].width; paste_a(im,ctx["logo"],((W-lw)//2,70)); d=ImageDraw.Draw(im,"RGBA")
    if line:
        a=ease((lt-0.2)/0.5); off=int((1-a)*50); f=F("Black",88); L=wrap(d,line,f,W-140); y=250+off
        for ln in L:
            x=(W-d.textlength(ln,font=f))/2
            d.text((x+3,y+4),ln,font=f,fill=(0,0,0,int(120*a))); d.text((x,y),ln,font=f,fill=(255,255,255,int(255*a))); y+=104
    styles.subtitles(im,ctx,t); styles.footer(im,ctx); return im
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
    f3=F("SemiBold",40); s3="Перед применением прочитайте инструкцию"; d.text(((W-d.textlength(s3,font=f3))/2,1530),s3,font=f3,fill=(255,255,255,int(255*a)))
    styles.footer(im,ctx); return im
def render(ctx,clips,fpath,fps):
    """ctx['scene_ends']: конец сцены 1, 2, 3, финал"""
    ends=ctx["scene_ends"]; dur=ctx["dur"]; nfr=int(dur*fps); starts=[0]+ends[:-1]; fi=0; XF=int(0.35*fps); prev=None; prev_raw=None
    for sc in range(4):
        n=int(round(ends[sc]*fps))-fi if sc<3 else nfr-fi
        gen=frames(clips[sc][1],n,fps) if sc<3 else None
        for j in range(n):
            t=fi/fps; lt=t-starts[sc]
            if sc<3:
                raw=next(gen,None) or prev_raw; prev_raw=raw
                fr=overlay(raw,ctx,t,ctx["lines"][sc],lt)
            else: fr=final_frame(ctx,t,lt)
            if prev is not None and j<XF: fr=Image.blend(prev,fr,(j+1)/(XF+1))   # плавный переход
            if j==n-1: prev=fr
            fr.convert("RGB").save(fpath%fi,quality=88); fi+=1
        if sc<3 and gen: gen.close()
