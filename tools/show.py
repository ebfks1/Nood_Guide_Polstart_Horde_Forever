import re,sys
s=open('/home/claude/out/PolestarPack_BalCon/Guides.lua',encoding='utf-8').read()
src,needle,before,after=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
a=s.index('-- Source: '+src); b=s.find('-- Source: ',a+10); g=s[a:b if b>0 else None]
def ko(l): return re.sub(r'T\("(?:[^"\\]|\\.)*", ("(?:[^"\\]|\\.)*")\)',r'\1',l)
out=[ko(l) for l in g.split('\n')]
i=[k for k,l in enumerate(out) if needle in l][0]
for l in out[max(0,i-before):i+after]: print(l[:int(sys.argv[5]) if len(sys.argv)>5 else 260])
