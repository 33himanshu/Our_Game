import base64, os, sys
V='../models/'
out='window.MODEL_B64 = window.MODEL_B64 || {}; window.MODEL_META = window.MODEL_META || {};\n'
for k in ('charan','himanshu','aman'):
    full=os.path.exists(V+k+'_full.glb')
    out+='window.MODEL_B64.'+k+' = "'+base64.b64encode(open(V+k+('_full' if full else '')+'.glb','rb').read()).decode()+'";\n'
    if full: out+='window.MODEL_META.'+k+' = '+__import__('json').dumps({'full':True, **(__import__('json').load(open(V+k+'_meta.json')) if os.path.exists(V+k+'_meta.json') else {})})+';\n'
open(V+'bodies.js','w').write(out); print('bodies.js %.1f MB'%(len(out)/1e6))
