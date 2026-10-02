from pathlib import Path
import cv2
from PIL import Image,ImageDraw
import sys
ROOT=Path(__file__).resolve().parents[1]/'evidence/owl-smooth-v2'/ (sys.argv[1] if len(sys.argv)>1 else 'browser-isolated')
def sheet(images,path,columns=4):
    out=Image.new('RGB',(columns*420,((len(images)+columns-1)//columns)*280),'#e7f0f7');draw=ImageDraw.Draw(out)
    for i,(name,im) in enumerate(images):
        im=im.convert('RGB').crop((80,0,465,270));im.thumbnail((410,250))
        x,y=(i%columns)*420,(i//columns)*280;out.paste(im,(x,y+25));draw.text((x+8,y+7),name,fill='#233b51')
    out.save(path)
sheet([(p.stem,Image.open(p)) for p in sorted(ROOT.glob('hold-*.png'))],ROOT/'holds-sheet.png')
cap=cv2.VideoCapture(str(ROOT/'actual-canvas-motion.webm'));images=[]
for sec in [i*.4 for i in range(61)]:
    cap.set(cv2.CAP_PROP_POS_MSEC,sec*1000);ok,f=cap.read()
    if ok:images.append((f'{sec:.1f}s',Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB))))
cap.release()
for n in range(0,len(images),16):sheet(images[n:n+16],ROOT/f'motion-sheet-{n//16}.png')
