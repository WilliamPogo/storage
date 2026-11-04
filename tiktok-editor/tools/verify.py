import json,sys,cv2,numpy as np
P=sys.argv[1]; t0,t1,step=map(float,sys.argv[2:5]); out=sys.argv[5]
d=json.load(open(P+'/blur_boxes.json')); fps=d['fps']
cap=cv2.VideoCapture(P+'/src/input.mov')
want={int(round(t*fps)):t for t in np.arange(t0,t1+1e-6,step)}
tiles=[];i=0
while True:
    ok,img=cap.read()
    if not ok: break
    if i in want:
        for b in d['frames'][i]: cv2.rectangle(img,(int(b[0]),int(b[1])),(int(b[2]),int(b[3])),(255,0,255),10)
        s=cv2.resize(img,(270,480)); cv2.putText(s,f'{want[i]:.2f}',(5,25),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,255,255),2); tiles.append(s)
    i+=1
while len(tiles)%8: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(out,np.vstack([np.hstack(tiles[k:k+8]) for k in range(0,len(tiles),8)]))
