from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
from copy import deepcopy
import hashlib, re, json

root=Path(__file__).resolve().parents[1]
ref=Path(r'C:/Users/harsh/.codex/plugins/cache/openai-curated-remote/openai-templates/0.1.1/skills/artifact-template-system-design/assets/reference.docx')
md=root/'outputs/AI Learning Harness Specification.md'
out=md.with_suffix('.docx')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W='{'+ns['w']+'}'
with ZipFile(ref) as z: parts={n:z.read(n) for n in z.namelist()}
tree=E.fromstring(parts['word/document.xml']); body=tree.find('w:body',ns)
sect=deepcopy(body.find('w:sectPr',ns))
patterns={}
for p in body.findall('w:p',ns):
    st=p.find('w:pPr/w:pStyle',ns)
    key=st.get(W+'val') if st is not None else 'Normal'
    txt=''.join(p.itertext())
    if key not in patterns and p.findall('w:r',ns): patterns[key]=deepcopy(p)
for c in list(body): body.remove(c)
def paragraph(text,style='Normal',bookmark=None):
    p=E.Element(W+'p'); pp=E.SubElement(p,W+'pPr'); E.SubElement(pp,W+'pStyle').set(W+'val',style)
    if style in ('Heading1','Heading3','Title'): E.SubElement(pp,W+'keepNext')
    if bookmark:
        b=E.SubElement(p,W+'bookmarkStart'); b.set(W+'id',str(bookmark)); b.set(W+'name','section_'+str(bookmark))
    r=E.SubElement(p,W+'r'); t=E.SubElement(r,W+'t'); t.text=text
    if bookmark:
        b=E.SubElement(p,W+'bookmarkEnd'); b.set(W+'id',str(bookmark))
    body.append(p)
    return p
lines=md.read_text(encoding='utf-8').splitlines()
counter=0
for line in lines:
    if not line.strip(): continue
    if line.startswith('# '): paragraph(line[2:],'Title')
    elif line=='## Product and Technical Specification': paragraph(line[3:],'Subtitle')
    elif line.startswith('## '):
        counter+=1; paragraph(line[3:],'Heading1',counter)
    elif line.startswith('### '): paragraph(line[4:],'Heading3')
    else: paragraph(line)
body.append(sect)
parts['word/document.xml']=E.tostring(tree,xml_declaration=True,encoding='UTF-8',standalone=True)
# Preserve template package and recurring furniture, replacing its organization placeholder.
for name,data in list(parts.items()):
    if re.match(r'word/(header|footer)\d+\.xml',name):
        parts[name]=data.replace(b'[Organization Name]',b'AI Learning Harness').replace(b'System Design RFC',b'Product and Technical Specification')
with ZipFile(out,'w',ZIP_DEFLATED) as z:
    for name,data in parts.items(): z.writestr(name,data)
with ZipFile(out) as z:
    assert z.testzip() is None
    extracted=[''.join(p.itertext()) for p in E.fromstring(z.read('word/document.xml')).findall('w:body/w:p',ns)]
    assert len(extracted)==len([l for l in lines if l.strip()])
    assert all(not x.startswith('[Summarize') for x in extracted)
    for n in parts:
        if n!='word/document.xml' and not re.match(r'word/(header|footer)\d+\.xml',n):
            with ZipFile(ref) as rz: assert z.read(n)==rz.read(n)
contract={'reference':str(ref),'sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'sections':1,'page_twips':[12240,15840],'margins_twips':{'top':1008,'bottom':893,'left':1008,'right':1008},'styles':'Preserve source Title, Subtitle, Heading1, Heading3 and Normal definitions','slots':'Replace body placeholders with specification paragraphs; extend heading and body patterns; replace footer organization and document label','preserve':'All package parts except document body and footer text unchanged','render_status':'Unavailable: no bundled Windows LibreOffice executable; no page-layout verification claimed','paragraphs':len(extracted),'words':len(md.read_text(encoding='utf-8').split())}
(root/'work/artifact.md').write_text(json.dumps(contract,indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'paragraphs':len(extracted),'words':contract['words'],'sections':counter}))

