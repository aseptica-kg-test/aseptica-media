# Стили роликов: «infographic» (анимированная инфографика) и «mascot» (мультик с талисманом-капелькой)
import math, random, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H=1080,1920
HERE=os.path.dirname(os.path.abspath(__file__))
def F(w,s): return ImageFont.truetype(os.path.join(HERE,"fonts","Inter-%s.otf"%w),int(s))
def paste_a(im,src,pos):
    pos=(int(pos[0]),int(pos[1])); im.paste(src,pos,src)
def ease(x): x=max(0.0,min(1.0,x)); return 1-(1-x)**3
def back(x):  # выезд с лёгким «отскоком»
    x=max(0.0,min(1.0,x)); c=1.7; return 1+(c+1)*(x-1)**3+c*(x-1)**2
def tint(c,k): return tuple(int(v+(255-v)*k) for v in c[:3])
def shade(c,k): return tuple(int(v*(1-k)) for v in c[:3])
def wrap(d,t,f,mw):
    L=[];cur=""
    for w in t.split():
        s=(cur+" "+w).strip()
        if d.textlength(s,font=f)<=mw: cur=s
        else: L.append(cur);cur=w
    if cur:L.append(cur)
    return L
def grad(c1,c2):
    g=Image.new("RGB",(1,256))
    for y in range(256): g.putpixel((0,y),tuple(int(a+(b-a)*y/255) for a,b in zip(c1,c2)))
    return g.resize((W,H)).convert("RGB")
def drop(d,x,y,s,c):
    d.ellipse([x-s,y-s*0.6,x+s,y+s*1.4],fill=c); d.polygon([(x-s*0.88,y),(x+s*0.88,y),(x,y-s*1.9)],fill=c)
# ---------- иконки (белые линии) ----------
def icon(d,kind,cx,cy,s,c=(255,255,255),w=10):
    if kind=="wind":
        for i,(a,b) in enumerate([(-0.5,0.7),(0,1.0),(0.5,0.5)]):
            y=cy+a*s; d.line([(cx-s,y),(cx+s*b,y)],fill=c,width=w); d.arc([cx+s*b-s*0.3,y-s*0.6,cx+s*b+s*0.3,y],270,90,fill=c,width=w)
    elif kind=="screen":
        d.rounded_rectangle([cx-s,cy-s*0.65,cx+s,cy+s*0.5],16,outline=c,width=w); d.line([(cx,cy+s*0.5),(cx,cy+s*0.8)],fill=c,width=w); d.line([(cx-s*0.45,cy+s*0.82),(cx+s*0.45,cy+s*0.82)],fill=c,width=w)
    elif kind=="lens":
        d.arc([cx-s,cy-s*0.6,cx+s,cy+s*0.9],190,350,fill=c,width=w+4); d.line([(cx-s*0.98,cy+s*0.05),(cx+s*0.98,cy+s*0.05)],fill=c,width=w-2)
    elif kind=="clock":
        d.ellipse([cx-s,cy-s,cx+s,cy+s],outline=c,width=w); d.line([(cx,cy),(cx,cy-s*0.6)],fill=c,width=w); d.line([(cx,cy),(cx+s*0.45,cy)],fill=c,width=w)
    elif kind=="cal":
        d.rounded_rectangle([cx-s,cy-s*0.8,cx+s,cy+s],14,outline=c,width=w); d.line([(cx-s,cy-s*0.3),(cx+s,cy-s*0.3)],fill=c,width=w)
    elif kind=="sun":
        for i in range(10):
            a=i*math.pi/5; d.line([(cx+math.cos(a)*s*0.7,cy+math.sin(a)*s*0.7),(cx+math.cos(a)*s,cy+math.sin(a)*s)],fill=c,width=w)
        d.ellipse([cx-s*0.45,cy-s*0.45,cx+s*0.45,cy+s*0.45],fill=c)
    else:  # drop
        drop(d,cx,cy,s*0.6,c)
def pick_icon(t):
    t=t.lower()
    for k,v in [("ветер","wind"),("кондиц","wind"),("экран","screen"),("компьют","screen"),("монитор","screen"),("линз","lens"),
                ("раз","clock"),("капл","drop"),("минут","clock"),("месяц","cal"),("вскрыт","cal"),("солн","sun"),("очк","sun")]:
        if k in t: return v
    return "drop"
# ============ 1. АНИМИРОВАННАЯ ИНФОГРАФИКА ============
def infographic_frame(ctx,t):
    """ctx: color, lines, sentences[(start,end,text)], dur, box(RGBA), name, sub, logo, footer"""
    c=ctx["color"]; dur=ctx["dur"]; im=grad(tint(c,0.15),shade(c,0.35)); d=ImageDraw.Draw(im,"RGBA")
    # фон: плывущие капли
    r=random.Random(7)
    for i in range(16):
        x=r.randint(0,W); sp=r.uniform(60,160); y=(r.randint(0,H)+t*sp)%(H+200)-100; s=r.randint(10,26)
        drop(d,x,y,s,tint(c,0.45)+(110,))
    d=ImageDraw.Draw(im,"RGBA")
    # сцены по долям ролика
    ends=ctx["scene_ends"]; sc=0
    while sc<len(ends)-1 and t>=ends[sc]: sc+=1
    st=0 if sc==0 else ends[sc-1]; lt=t-st
    lw=ctx["logo"].width; paste_a(im,ctx["logo"],((W-lw)//2,70)); d=ImageDraw.Draw(im,"RGBA")
    if sc==0:   # крупные слова появляются по одному
        words=ctx["lines"][0].split(); f=F("Black",118); y=420
        rows=wrap(d,ctx["lines"][0],f,W-140); wi=0
        for row in rows:
            x=(W-d.textlength(row,font=f))/2
            for wd in row.split():
                a=ease((lt-0.25*wi)/0.35); sz=back((lt-0.25*wi)/0.45)
                if a>0:
                    ff=F("Black",max(10,118*max(0.2,sz))); ww=d.textlength(wd+" ",font=f)
                    d.text((x+(ww-d.textlength(wd,font=ff))/2,y+(118-118*max(0.2,sz))/2),wd,font=ff,fill=(255,255,255,int(255*a)))
                x+=d.textlength(wd+" ",font=f); wi+=1
            y+=140
        # большая капля, падающая в центр
        p=ease(lt/1.2); dy=-300+p*(1100+300); drop(d,W/2,dy+300,70,(255,255,255,220))
        if lt>1.2:
            k=ease((lt-1.2)/0.6); rr=60+300*k; d.ellipse([W/2-rr,1400-rr*0.25,W/2+rr,1400+rr*0.25],outline=(255,255,255,int(200*(1-k))),width=8)
    elif sc==1:  # иконки выскакивают с подписями
        labs=ctx["lines"][1:3]+[ctx["lines"][0]]; labs=[x for x in labs if x][:3]
        for i,lab in enumerate(labs):
            k=back((lt-0.35*i)/0.5); a=ease((lt-0.35*i)/0.3)
            if a<=0: continue
            y=460+i*360; r_=int(110*max(0.01,k))
            d.ellipse([170-r_,y-r_,170+r_,y+r_],fill=(255,255,255,int(60*a)))
            icon(d,pick_icon(lab),170,y,62*max(0.05,k),(255,255,255,int(255*a)),9)
            f=F("Bold",58); L=wrap(d,lab,f,700); yy=y-len(L)*36
            for ln in L: d.text((320+int((1-a)*60),yy),ln,font=f,fill=(255,255,255,int(255*a))); yy+=72
    elif sc==2:  # упаковка выезжает и покачивается
        k=back(lt/0.8); bx=W/2+(1-k)*900; ang=math.sin(lt*2.2)*4
        b=ctx["box"].rotate(ang,resample=Image.BICUBIC,expand=True)
        sh=Image.new("RGBA",(W,H),(0,0,0,0)); ImageDraw.Draw(sh).ellipse([bx-260,1330,bx+260,1400],fill=(0,0,0,90)); paste_a(im,sh.filter(ImageFilter.GaussianBlur(20)),(0,0))
        d=ImageDraw.Draw(im,"RGBA"); d.ellipse([W/2-380,560,W/2+380,1320],fill=tint(c,0.35)+(120,))
        paste_a(im,b,(int(bx-b.width/2),int(1360-b.height))); d=ImageDraw.Draw(im,"RGBA")
        a=ease((lt-0.5)/0.4); f=F("Black",96); tw=d.textlength(ctx["name"],font=f)
        d.rounded_rectangle([(W-tw)/2-40,300,(W+tw)/2+40,430],65,fill=(255,255,255,int(255*a)))
        d.text(((W-tw)/2,312),ctx["name"],font=f,fill=c+(int(255*a),))
        f2=F("Medium",40); L=wrap(d,ctx["sub"],f2,W-200); yy=455
        for ln in L: d.text(((W-d.textlength(ln,font=f2))/2,yy),ln,font=f2,fill=(255,255,255,int(255*a))); yy+=52
    else:        # финал
        a=ease(lt/0.5); f=F("Black",80); s="Aseptica"; d.text(((W-d.textlength(s,font=f))/2,520),s,font=f,fill=(255,255,255,int(255*a)))
        f2=F("Bold",56); s2="забота о глазах"; d.text(((W-d.textlength(s2,font=f2))/2,620),s2,font=f2,fill=(255,255,255,int(255*a)))
        f3=F("SemiBold",44); s3="Перед применением прочитайте инструкцию"; L=wrap(d,s3,f3,W-160); yy=820
        for ln in L: d.text(((W-d.textlength(ln,font=f3))/2,yy),ln,font=f3,fill=(255,255,255,int(255*a))); yy+=58
        b=ctx["box"]; bb=b.resize((int(b.width*0.7),int(b.height*0.7))); paste_a(im,bb,(int((W-bb.width)/2),int(1450-bb.height+(1-a)*200)))
    subtitles(im,ctx,t); footer(im,ctx); return im.convert("RGB")
def subtitles(im,ctx,t):
    d=ImageDraw.Draw(im,"RGBA")
    for s,e,txt in ctx["sentences"]:
        if s<=t<e:
            f=F("SemiBold",40); L=wrap(d,txt,f,W-160)[:3]; h=len(L)*52+36; y0=1520
            d.rounded_rectangle([60,y0,W-60,y0+h],28,fill=(0,0,0,110)); yy=y0+18
            for ln in L: d.text(((W-d.textlength(ln,font=f))/2,yy),ln,font=f,fill=(255,255,255)); yy+=52
def footer(im,ctx):
    if not ctx.get("footer"): return
    d=ImageDraw.Draw(im,"RGBA"); f=F("Regular",24); L=wrap(d,ctx["footer"],f,W-120); y=H-40-len(L)*30
    d.rectangle([0,y-20,W,H],fill=(255,255,255,235))
    for ln in L: d.text((60,y),ln,font=f,fill=(80,90,105)); y+=30
# ============ 2. МУЛЬТИК: ТАЛИСМАН-КАПЕЛЬКА ============
def mascot(d,cx,cy,s,t,talk,look=(0,0),blink=False,wave=0):
    body=(120,200,245); dark=(30,100,170)
    # тело-капля
    d.ellipse([cx-s,cy-s*0.8,cx+s,cy+s*1.2],fill=body); d.polygon([(cx-s*0.86,cy-s*0.2),(cx+s*0.86,cy-s*0.2),(cx,cy-s*1.9)],fill=body)
    d.ellipse([cx-s*0.6,cy-s*0.5,cx-s*0.2,cy-s*0.05],fill=(200,235,255))   # блик
    # глаза
    for ex in (-0.35,0.35):
        x=cx+ex*s; y=cy+0.1*s
        if blink: d.line([(x-s*0.17,y),(x+s*0.17,y)],fill=dark,width=int(s*0.06))
        else:
            d.ellipse([x-s*0.2,y-s*0.24,x+s*0.2,y+s*0.24],fill=(255,255,255))
            px=x+look[0]*s*0.09; py=y+look[1]*s*0.09; d.ellipse([px-s*0.1,py-s*0.1,px+s*0.1,py+s*0.1],fill=dark)
            d.ellipse([px+s*0.02,py-s*0.07,px+s*0.06,py-s*0.03],fill=(255,255,255))
    # рот: открывается по громкости голоса
    mo=s*0.05+s*0.2*talk; d.ellipse([cx-s*0.2,cy+s*0.5,cx+s*0.2,cy+s*0.5+mo],fill=dark)
    d.ellipse([cx-s*0.55,cy+s*0.42,cx-s*0.38,cy+s*0.55],fill=(255,170,190)); d.ellipse([cx+s*0.38,cy+s*0.42,cx+s*0.55,cy+s*0.55],fill=(255,170,190))
    # ручка машет
    a=-0.6+math.sin(t*6)*0.5*wave; hx=cx+s*1.0; hy=cy+s*0.5
    d.line([(cx+s*0.9,cy+s*0.6),(hx+math.cos(a)*s*0.55,hy+math.sin(a)*s*0.55)],fill=body,width=int(s*0.16))
    d.line([(cx-s*0.9,cy+s*0.6),(cx-s*1.25,cy+s*0.95)],fill=body,width=int(s*0.16))
def scene_bg(kind,t,im):
    d=ImageDraw.Draw(im,"RGBA")
    if kind=="office":
        d.rectangle([0,0,W,H],fill=(232,242,250)); d.rectangle([0,1250,W,H],fill=(200,170,140))
        d.rectangle([0,1210,W,1260],fill=(170,135,105))
        d.rounded_rectangle([520,640,1000,960],24,fill=(40,50,70)); d.rounded_rectangle([540,660,980,940],14,fill=(140,200,240))
        for i in range(5): d.rounded_rectangle([570,690+i*45,570+((i*97)%300)+80,712+i*45],8,fill=(255,255,255))
        d.rectangle([740,960,780,1100],fill=(40,50,70)); d.rounded_rectangle([660,1100,860,1130],10,fill=(40,50,70))
    elif kind=="window":
        d.rectangle([0,0,W,H],fill=(240,236,228))
        # вид из окна рисуем отдельно и обрезаем по раме
        X0,Y0,X1,Y1=120,300,960,1100; v=Image.new("RGB",(X1-X0,Y1-Y0),(150,205,245)); vd=ImageDraw.Draw(v)
        sx=680+math.sin(t*0.5)*20; vd.ellipse([sx-60,80,sx+60,200],fill=(255,215,100))
        for x0,h0,c in [(-80,300,(120,160,200)),(230,220,(100,140,185)),(520,280,(130,170,210))]:
            pk=(x0+230,h0); vd.polygon([(x0-60,Y1-Y0),pk,(x0+520,Y1-Y0)],fill=c)
            vd.polygon([(pk[0]-50,pk[1]+80),pk,(pk[0]+50,pk[1]+80)],fill=(255,255,255))
        im.paste(v,(X0,Y0)); d=ImageDraw.Draw(im,"RGBA")
        d.rectangle([X0-14,Y0-14,X1+14,Y0+6],fill=(255,255,255)); d.rectangle([X0-14,Y1-6,X1+14,Y1+14],fill=(255,255,255))
        d.rectangle([X0-14,Y0-14,X0+6,Y1+14],fill=(255,255,255)); d.rectangle([X1-6,Y0-14,X1+14,Y1+14],fill=(255,255,255))
        d.rectangle([(X0+X1)//2-10,Y0,(X0+X1)//2+10,Y1],fill=(255,255,255)); d.rectangle([X0,(Y0+Y1)//2-10,X1,(Y0+Y1)//2+10],fill=(255,255,255))
        d.rectangle([0,1250,W,H],fill=(210,190,165))
    else:  # brand
        im.paste(grad((40,150,215),(0,95,165)),(0,0))
def mascot_frame(ctx,t):
    ends=ctx["scene_ends"]; sc=0
    while sc<len(ends)-1 and t>=ends[sc]: sc+=1
    st=0 if sc==0 else ends[sc-1]; lt=t-st
    kinds=ctx.get("kinds",["office","window","brand","brand"]); kind=kinds[min(sc,len(kinds)-1)]
    im=Image.new("RGB",(W,H),(255,255,255)); scene_bg(kind,t,im); d=ImageDraw.Draw(im,"RGBA")
    if kind!="brand": paste_a(im,ctx["logo_blue"],((W-ctx["logo_blue"].width)//2,80))
    else: paste_a(im,ctx["logo"],((W-ctx["logo"].width)//2,80))
    d=ImageDraw.Draw(im,"RGBA")
    talk=ctx["env"](t); blink=(t%3.2)<0.12
    look={"office":(1,0.2),"window":(0.6,-0.8)}.get(kind,(0,0))
    bob=math.sin(t*3)*12; enter=back(t/0.8); cx=300-(1-enter)*500 if kind!="brand" else W/2
    mascot(d,cx,1250+bob-200,170,t,talk,look,blink,wave=1 if sc==len(ends)-1 or (sc==0 and lt<1.5) else 0)
    # облачко с надписью
    lines=ctx["lines"]; txt=lines[sc] if sc<len(lines) else "Aseptica — забота о глазах"
    if kind=="brand": txt="Aseptica — забота о глазах"
    a=ease(lt/0.4); f=F("Black",64); L=wrap(d,txt,f,640) if kind!="brand" else wrap(d,txt,f,900)
    bw=max(d.textlength(x,font=f) for x in L)+80; bh=len(L)*78+60
    bx=W-bw-60 if kind!="brand" else (W-bw)/2; by=300 if kind!="brand" else 420
    if kind=="window": by=1150-bh-40 if False else 1130; bx=W-bw-40
    d.rounded_rectangle([bx,by,bx+bw,by+bh],40,fill=(0,115,187,int(235*a)))
    d.rounded_rectangle([bx+10,by+10,bx+bw-10,by+bh-10],32,outline=(255,255,255,int(90*a)),width=3)
    yy=by+30
    for ln in L: d.text((bx+40,yy),ln,font=f,fill=(255,255,255,int(255*a))); yy+=78
    if kind=="brand":
        f3=F("SemiBold",42); s3="Перед применением прочитайте инструкцию"; L3=wrap(d,s3,f3,W-160); y3=by+bh+40
        for ln in L3: d.text(((W-d.textlength(ln,font=f3))/2,y3),ln,font=f3,fill=(255,255,255)); y3+=56
    subtitles(im,ctx,t); footer(im,ctx); return im.convert("RGB")
