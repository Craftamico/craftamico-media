import sys, subprocess, numpy as np, io
from PIL import Image
from scipy import ndimage
def frame(src,t):
    out=subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',src,'-frames:v','1','-f','image2pipe','-vcodec','png','-'])
    return np.asarray(Image.open(io.BytesIO(out)).convert('RGB')).astype(int)
def pills(a):
    r,g,b=a[...,0],a[...,1],a[...,2]
    m=(r<60)&(g<65)&(b>50)&(b<105)&(b-r>18)
    m=ndimage.binary_closing(m,iterations=6)
    lab,n=ndimage.label(m); res=[]
    for i,sl in enumerate(ndimage.find_objects(lab)):
        h=sl[0].stop-sl[0].start; w=sl[1].stop-sl[1].start
        if h<60 or w<200 or h>400: continue
        fill=(lab[sl]==i+1).mean()
        if fill>0.75: res.append((sl[1].start,sl[0].start,sl[1].stop,sl[0].stop))
    return res
def union(src,start,dur,step=0.4):
    boxes=[]; t=start
    while t<start+dur: boxes+=pills(frame(src,t)); t+=step
    if not boxes: return None
    return (min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)), len(boxes)
if __name__=='__main__':
    src=sys.argv[1]; d=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',src]))
    t=0.2
    while t<d: print(round(t,1),pills(frame(src,t))); t+=1.0
