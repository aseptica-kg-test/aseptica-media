# Сборщик Reels Aseptica: тема → текст (Gemini) → голос (Gemini TTS, Nika) → видео 1080×1920 с музыкой.
# Запускается на GitHub Actions. Локальная проверка без интернета: python3 make_reel.py --mock
import os, sys, json, base64, math, random, re, subprocess, datetime, wave, struct, urllib.request, urllib.error
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"..",".."))
HERE=os.path.dirname(os.path.abspath(__file__))
MOCK="--mock" in sys.argv
KEY=os.environ.get("GEMINI_API_KEY","")
TEXT_MODEL=os.environ.get("REEL_TEXT_MODEL","gemini-3.1-flash-lite")
TTS_MODELS=[m for m in os.environ.get("REEL_TTS_MODEL","gemini-3.8-flash-tts,gemini-3.1-flash-tts-preview").split(",") if m]
VOICE=os.environ.get("REEL_VOICE","Nika")
W,H,FPS=1080,1920,25
RAW="https://raw.githubusercontent.com/aseptica-kg-test/aseptica-media/main/"
def F(w,s): return ImageFont.truetype(os.path.join(HERE,"fonts","Inter-%s.otf"%w),s)
pack=json.load(open(os.path.join(ROOT,"agent","pack.json"),encoding="utf-8"))
R=pack["rules"]
statef=os.path.join(ROOT,"reels","state.json")
state=json.load(open(statef)) if os.path.exists(statef) else {"counter":0,"history":[]}
n=state["counter"]; isP=(n%2==0); k=n//2
# ---------- тема ----------
if isP:
    p=pack["products"][k%len(pack["products"])]; key=p["key"]
    angle=p["angles"][(k//len(pack["products"]))%len(p["angles"])]
    img_rel="posts/products/%s.jpg"%key; footer=p["footer"]; title="Reels: "+p["name"]+" — "+angle
    color={"vitolin":(240,130,40),"forte":(46,160,90),"oftalron":(220,40,130),"oftalron_p":(225,45,50),"keraton":(110,90,200),"dakrocin":(240,165,10)}[key]
    task=("Тема ролика: продукт «%s», %s.\n"%(p["name"],angle)+("Только информационно: название, состав, применение, хранение.\n" if p.get("info_only") else "")+
          "ФАКТЫ (только они):\n- "+"\n- ".join(p["facts"]+R["common_allowed"])+"\nДля продукта ЗАПРЕЩЕНО: "+"; ".join(p["no"])+".")
else:
    i=k%len(pack["tips"]); t=pack["tips"][i]; pkey=t["product"]; p=next(x for x in pack["products"] if x["key"]==pkey)
    img_rel="posts/tips/tip%02d.jpg"%(i+1); footer=p["footer"]; title="Reels: совет — "+t["title"]; color=(0,115,187)
    task=("Тема ролика: совет для глаз «%s. %s» (источник: %s). %s\n"%(t["title"],t["body"],t["source"],t.get("note",""))+
          "Раскрой совет простыми словами, без новых медицинских фактов, не связывай с каплями.")
system=("Ты пишешь сценарии коротких вертикальных видео (Reels) для компании Aseptica (глазные капли, медицинские изделия), Кыргызстан. Язык: русский.\n"
        "Стиль: "+R["style"]+"\nСтрого запрещено: "+"; ".join(R["common_forbidden"])+".\n"
        'Ответ — JSON: {"voice": текст для озвучки 35–50 слов, спокойно и понятно, без хэштегов и эмодзи; '
        '"lines": [3 коротких надписи на экран, каждая не длиннее 6 слов]; "caption": подпись к посту 250–450 знаков, можно 1–2 эмодзи, без хэштегов и юр. строки}.')
BAD=re.compile(r"нейропротек|лечит|лечени|излеч|устраня|синдром|глауком|диабет|катаракт|ретинопат|кератокону|дет(и|ей|ям|ск)|подрост|беремен|гарант|лучш|№ ?1|скидк|цен[аы]",re.I)
def post(url,body,timeout=180):
    req=urllib.request.Request(url+("&" if "?" in url else "?")+"key="+KEY,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    last=None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            last="HTTP %s: %s"%(e.code,e.read()[:300].decode("utf-8","ignore"))
            if e.code in (429,500,502,503,504): import time; time.sleep(20*(attempt+1)); continue
            raise RuntimeError(last)
        except Exception as e:
            last=str(e); import time; time.sleep(15)
    raise RuntimeError(last)
GAPI="https://generativelanguage.googleapis.com/v1beta/models/"
def write_text():
    if MOCK:
        return {"voice":"Глазные капли Витолин сохраняют поверхность глаза смазанной, увлажнённой и защищённой. Ветер, кондиционер, долгая работа за экраном — Витолин рядом. По одной капле два-три раза в сутки. Перед применением прочитайте инструкцию.",
                "lines":["Увлажнение и защита","Ветер, кондиционер, экран","1 капля 2–3 раза в сутки"],"caption":"Витолин — глазные капли для комфорта в течение дня 💧"}
    body={"systemInstruction":{"parts":[{"text":system}]},"contents":[{"role":"user","parts":[{"text":task}]}],
          "generationConfig":{"temperature":0.8,"responseMimeType":"application/json","responseSchema":{"type":"OBJECT","properties":{
            "voice":{"type":"STRING"},"lines":{"type":"ARRAY","items":{"type":"STRING"}},"caption":{"type":"STRING"}},"required":["voice","lines","caption"]}}}
    for _ in range(3):
        r=post(GAPI+TEXT_MODEL+":generateContent",body)
        o=json.loads("".join(x.get("text","") for x in r["candidates"][0]["content"]["parts"]))
        if not BAD.search(o["voice"]+" "+" ".join(o["lines"])+" "+o["caption"]): return o
    o["warning"]="Проверьте текст: найдено запрещённое слово"; return o
def tts(text):
    if MOCK:
        sr=24000; t=np.arange(int(sr*14))/sr; return (np.sin(2*np.pi*220*t)*0.0).astype(np.float32),sr
    err=[]
    for m in TTS_MODELS:
        try:
            r=post(GAPI+m+":generateContent",{"contents":[{"parts":[{"text":"Прочитай спокойно, дружелюбно и чётко, в умеренном темпе: "+text}]}],
                "generationConfig":{"responseModalities":["AUDIO"],"speechConfig":{"languageCode":"ru-RU","voiceConfig":{"prebuiltVoiceConfig":{"voiceName":VOICE}}}}})
            part=next(x for x in r["candidates"][0]["content"]["parts"] if "inlineData" in x)["inlineData"]
            sr=int(re.search(r"rate=(\d+)",part.get("mimeType","rate=24000")).group(1))
            pcm=np.frombuffer(base64.b64decode(part["data"]),dtype="<i2").astype(np.float32)/32768
            return pcm,sr
        except Exception as e: err.append("%s: %s"%(m,e))
    raise RuntimeError("Озвучка не удалась — "+" || ".join(err))
def music(sec,sr=48000):
    # своя спокойная фоновая музыка: мягкие аккорды C–Am–F–G
    t=np.arange(int(sec*sr))/sr; out=np.zeros_like(t)
    chords=[(261.6,329.6,392.0),(220.0,261.6,329.6),(174.6,220.0,261.6),(196.0,246.9,293.7)]
    bar=3.2
    for i in range(int(sec/bar)+1):
        s=int(i*bar*sr); e=min(len(t),int((i+1)*bar*sr)+int(0.8*sr))
        if s>=len(t): break
        tt=t[s:e]-t[s]; env=np.minimum(1,tt/1.2)*np.exp(-np.maximum(0,tt-bar)/0.5)
        for f in chords[i%4]:
            out[s:e]+=env*(0.5*np.sin(2*np.pi*f*tt)+0.2*np.sin(2*np.pi*2*f*tt))/3
        arp=chords[i%4][(i//1)%3]*2  # лёгкая «капля» в начале такта
        a=np.exp(-tt/0.35)*np.sin(2*np.pi*arp*tt)*0.25; out[s:e]+=a
    fade=np.minimum(1,np.minimum(t/1.5,(sec-t)/1.5)); out*=fade
    return out/ (np.max(np.abs(out))+1e-9),sr
def wrap(d,txt,f,mw):
    L=[];cur=""
    for w in txt.split():
        s=(cur+" "+w).strip()
        if d.textlength(s,font=f)<=mw: cur=s
        else: L.append(cur);cur=w
    if cur:L.append(cur)
    return L
def ease(x): x=max(0,min(1,x)); return 1-(1-x)**3
def main():
    o=write_text(); voice,vsr=tts(o["voice"])
    # аудио 48 кГц
    if vsr!=48000: voice=np.interp(np.arange(int(len(voice)*48000/vsr))*vsr/48000,np.arange(len(voice)),voice)
    vdur=len(voice)/48000; dur=max(12.0,min(55.0,vdur+3.0)); sr=48000
    m,_=music(dur); mix=m*0.10; st=int(0.6*sr); mix[st:st+len(voice)]+=voice[:max(0,len(mix)-st)]*0.95
    mix=np.clip(mix,-1,1)
    os.makedirs("/tmp/reel",exist_ok=True)
    with wave.open("/tmp/reel/a.wav","wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((mix*32767).astype("<i2").tobytes())
    # картинки
    card=Image.open(os.path.join(ROOT,img_rel)).convert("RGB")
    logo=Image.open(os.path.join(ROOT,"brand","aseptica_logo_white.png"))
    lw=420; logo=logo.resize((lw,int(logo.height*lw/logo.width)),Image.LANCZOS)
    bg=Image.new("RGB",(1,256))
    c1=tuple(min(255,int(v*1.0+40)) for v in color); c2=tuple(int(v*0.55) for v in color)
    for y in range(256): bg.putpixel((0,y),tuple(int(a+(b-a)*y/255) for a,b in zip(c1,c2)))
    bg=bg.resize((W,H)).convert("RGBA")
    lines=(o["lines"]+["","",""])[:3]; nfr=int(dur*FPS); segs=[0.0,0.30,0.62,0.86]  # доли: надпись 1, 2, 3, финал
    tf=F("Black",76); fpath="/tmp/reel/f%05d.jpg"
    for fi in range(nfr):
        tt=fi/FPS; x=tt/dur; im=bg.copy(); d=ImageDraw.Draw(im)
        im.alpha_composite(logo,((W-lw)//2,90))
        # карточка поста с медленным приближением
        z=1.0+0.06*x; cw=int(900*z); ch=int(cw*card.height/card.width)
        c=card.resize((cw,ch),Image.BILINEAR)
        top=760-int(40*z); sh=Image.new("RGBA",(cw+60,ch+60),(0,0,0,0)); ImageDraw.Draw(sh).rounded_rectangle([30,40,cw+30,ch+30],40,fill=(0,0,0,90))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)),((W-cw)//2-30,top-30))
        m_=Image.new("L",(cw,ch),0); ImageDraw.Draw(m_).rounded_rectangle([0,0,cw-1,ch-1],36,fill=255)
        im.paste(c,((W-cw)//2,top),m_)
        # надписи
        idx=0 if x<segs[1] else 1 if x<segs[2] else 2 if x<segs[3] else 3
        if idx<3 and lines[idx]:
            a=ease((x-segs[idx])/0.05); off=int((1-a)*60)
            L=wrap(d,lines[idx],tf,W-140); y0=300+off
            for ln in L:
                tw=d.textlength(ln,font=tf); d.text(((W-tw)/2,y0),ln,font=tf,fill=(255,255,255,int(255*a))); y0+=92
        else:
            a=ease((x-segs[3])/0.05); txt="Aseptica — забота о глазах"; f2=F("Bold",58); tw=d.textlength(txt,font=f2)
            d.text(((W-tw)/2,330),txt,font=f2,fill=(255,255,255,int(255*a)))
            f3=F("Medium",36); s="Перед применением прочитайте инструкцию"; tw=d.textlength(s,font=f3); d.text(((W-tw)/2,430),s,font=f3,fill=(255,255,255,int(235*a)))
        im.convert("RGB").save(fpath%fi,quality=88)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M"); rel="reels/reel_%s.mp4"%stamp
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",fpath,"-i","/tmp/reel/a.wav","-c:v","libx264","-preset","veryfast","-crf","21",
                    "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-ar","48000","-shortest","-movflags","+faststart",os.path.join(ROOT,rel)],check=True)
    for f in os.listdir("/tmp/reel"):
        if f.startswith("f"): os.remove("/tmp/reel/"+f)
    ik=img_rel; tags=(pack.get("hashtags_ru","")+" "+pack.get("hashtags_extra",{}).get("/".join(ik.split("/")[-2:]),"")).strip()
    caption=o["caption"].strip()+"\n\n"+footer+"\n\n"+tags
    info={"created":stamp,"title":title,"video_url":RAW+rel,"caption":caption,"voice_text":o["voice"],"lines":o["lines"],
          "warning":o.get("warning",""),"used":False,"slot":n}
    json.dump(info,open(os.path.join(ROOT,"reels","latest.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    state["counter"]=n+1; state["history"]=(state.get("history",[])+[{"slot":n,"file":rel,"title":title}])[-30:]
    json.dump(state,open(statef,"w"),ensure_ascii=False,indent=1)
    # храним последние 12 роликов
    vids=sorted(f for f in os.listdir(os.path.join(ROOT,"reels")) if f.endswith(".mp4"))
    for f in vids[:-12]: os.remove(os.path.join(ROOT,"reels",f))
    print("OK",rel,round(dur,1),"сек")
if __name__=="__main__":
    try: main()
    except Exception as e:
        json.dump({"error":str(e)[:800],"time":datetime.datetime.now(datetime.timezone.utc).isoformat()},open(os.path.join(ROOT,"reels","last_error.json"),"w"),ensure_ascii=False,indent=1)
        print("ERROR",e); sys.exit(1)
