"""Bounded daily acquisition and public-source index. No accounts or paywall bypass."""
import argparse,colorsys,concurrent.futures,datetime,hashlib,html,io,json,pathlib,re,time,urllib.parse,urllib.request,urllib.robotparser,zipfile
from html.parser import HTMLParser
from PIL import Image

ROOT=pathlib.Path(__file__).resolve().parents[1]
USER_AGENT='KongjianShejiLibrary/1.0 (+https://kongjiansheji-library.github.io/)'
MAX_RESPONSE=30*1024*1024
ASSET_BUDGET=850*1024*1024
RULES=[('木纹',r'wood|parquet|plank|timber|oak|walnut|bark|木纹|木地板|木饰面'),('大理石',r'marble|大理石'),('瓷砖',r'tile|ceramic|porcelain|瓷砖|地砖|墙砖|马赛克'),('水磨石',r'terrazzo|水磨石'),('砖墙',r'brick|砖墙'),('混凝土',r'concrete|cement|mortar|水泥|混凝土|砂浆'),('皮革',r'leather|皮革'),('地毯',r'carpet|地毯'),('布艺',r'fabric|textile|cloth|denim|布艺|布料|织物|丝绒|绒面|绢面'),('金属',r'metal|steel|iron|aluminium|aluminum|copper|rust|金属|钢|铝|铜'),('石材',r'stone|rock|granite|石材|岩石|花岗岩'),('涂料',r'plaster|stucco|paint|涂料|灰泥|乳胶漆|涂层'),('玻璃',r'glass|玻璃'),('墙纸',r'wallpaper|墙纸|壁纸'),('自然地面',r'ground|sand|soil|mud|grass|沙地|泥土|草地')]
def classify(text):
    text=text.lower()
    for name,pattern in RULES:
        if re.search(pattern,text):return name
    return '待分类'
def fetch(url,limit=MAX_RESPONSE):
    error=None
    for attempt in range(2):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Referer':'https://kongjiansheji-library.github.io/'})
            with urllib.request.urlopen(req,timeout=18) as response:
                if int(response.headers.get('Content-Length','0'))>limit:raise ValueError('response exceeds limit')
                raw=response.read(limit+1)
                if len(raw)>limit:raise ValueError('response exceeds limit')
                return raw,response.headers.get_content_charset(),response.geturl()
        except Exception as exc:error=exc;time.sleep(.5)
    raise error
def getjson(url):return json.loads(fetch(url)[0])
def load(name,default):
    p=ROOT/name
    return json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else default
def save(name,data,global_name=None):
    raw=json.dumps(data,ensure_ascii=False,indent=2)
    tmp=ROOT/(name+'.tmp');tmp.write_text(raw,encoding='utf-8');tmp.replace(ROOT/name)
    if global_name:
        p=ROOT/pathlib.Path(name).with_suffix('.js');tmp=p.with_suffix('.js.tmp');tmp.write_text('window.'+global_name+' = '+raw+';',encoding='utf-8');tmp.replace(p)
def color(im):
    rgb=im.convert('RGB').resize((1,1)).getpixel((0,0));h,s,v=colorsys.rgb_to_hsv(*(x/255 for x in rgb))
    if v<.19:return ['黑色']
    if s<.14:return ['白色' if v>.82 else '灰色']
    if h<.11 or h>.95:return ['棕色' if v<.65 else '红色']
    if h<.19:return ['米色' if s<.4 else '黄色']
    if h<.46:return ['绿色']
    if h<.72:return ['蓝色']
    return ['紫色']
def store_image(raw,ident,current_bytes):
    Image.MAX_IMAGE_PIXELS=20_000_000
    with Image.open(io.BytesIO(raw)) as im:
        im.load();im=im.convert('RGB');im.thumbnail((1024,1024));size=list(im.size);colors=color(im)
        out=io.BytesIO();im.save(out,'JPEG',quality=88);imgbytes=out.getvalue();im.thumbnail((320,320));out=io.BytesIO();im.save(out,'JPEG',quality=82);thumbbytes=out.getvalue()
    if current_bytes+len(imgbytes)+len(thumbbytes)>ASSET_BUDGET:raise ValueError('storage_budget_reached')
    image='images/auto/'+ident+'.jpg';thumb='thumbs/auto/'+ident+'.jpg'
    for rel,content in [(image,imgbytes),(thumb,thumbbytes)]:
        target=ROOT/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
    return dict(image=image,thumb=thumb,size=size,colors=colors,sha256=hashlib.sha256(raw).hexdigest()),len(imgbytes)+len(thumbbytes)
def existing_ids(items):
    ids=set()
    for it in items:
        ident=it['id'];ids.add(ident)
        if ident.startswith('ph_'):ids.add('polyhaven:'+ident[3:])
        if 'ambientcg.com' in it.get('source',''):ids.add('ambientcg:'+ident)
        if it.get('provider_asset_id'):ids.add(it.get('provider_key','')+':'+it['provider_asset_id'])
    return ids
def acquire(source,existing,quota,size):
    added=[];failures=[];name=source['name'];key=source['id'];checked=0
    if key=='polyhaven':
        catalog=getjson('https://api.polyhaven.com/assets?t=textures');candidates=sorted(catalog.items(),key=lambda x:x[1].get('date_published',0),reverse=True)
    else:
        catalog=getjson('https://ambientcg.com/api/v2/full_json?type=Material&limit=250&sort=Latest&include=downloadData,imageData')
        candidates=[(a['assetId'],a) for a in catalog['foundAssets']]
    for asset_id,a in candidates:
        if len(added)>=quota or checked>=quota*4:break
        if key+':'+asset_id in existing:continue
        checked+=1;ident=('ph_' if key=='polyhaven' else 'acg_')+asset_id
        try:
            if key=='polyhaven':
                files=getjson('https://api.polyhaven.com/files/'+asset_id);variant=(files.get('Diffuse') or files.get('diff') or {}).get('1k',{}).get('jpg')
                if not variant:continue
                url=variant['url'];raw=fetch(url)[0]
                if variant.get('md5') and hashlib.md5(raw).hexdigest()!=variant['md5']:raise ValueError('checksum mismatch')
                title=a['name'];tags=a.get('tags',[])+a.get('categories',[]);original='https://polyhaven.com/a/'+asset_id;author=', '.join(a.get('authors',{}))
            else:
                downloads=a['downloadFolders']['default']['downloadFiletypeCategories']['zip']['downloads'];variant=next(x for x in downloads if x.get('attribute')=='1K-JPG')
                if variant.get('size',0)>MAX_RESPONSE:continue
                url=variant.get('downloadLink') or variant['fullDownloadPath'];packed=fetch(url)[0]
                with zipfile.ZipFile(io.BytesIO(packed)) as z:
                    match=next(x for x in z.infolist() if re.search(r'_Color\.jpg$',x.filename,re.I));assert match.file_size<MAX_RESPONSE;raw=z.read(match)
                title=a.get('displayName',asset_id);tags=a.get('tags',[])+[a.get('displayCategory','')];original=a.get('shortLink') or 'https://ambientcg.com/a/'+asset_id;author='ambientCG'
            digest=hashlib.sha256(raw).hexdigest()
            if digest in existing:continue
            data,delta=store_image(raw,ident,size);size+=delta
            material=classify(' '.join([asset_id,title]+tags))
            added.append(dict(id=ident,name=title,label=material+' · '+title,material=material,styles=[],rooms=[],tags=tags,provider=name,provider_key=key,provider_asset_id=asset_id,source=original,original_url=url,license='CC0 公共领域',author=author,added=datetime.datetime.now(datetime.timezone.utc).isoformat(),**data));existing.add(key+':'+asset_id);existing.add(digest)
        except Exception as exc:
            failures.append({'asset':asset_id,'error':str(exc)[:160]})
            if 'storage_budget_reached' in str(exc):break
    return added,{'id':key,'name':name,'region':source['region'],'url':source['url'],'mode':'自动入库','state':'ok' if not failures else 'partial','added':len(added),'detail':'已检查公开API，新图自动分类；颜色标签为图像估计','errors':failures},size

class Anchors(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.href=None;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.href=dict(attrs).get('href');self.parts=[]
    def handle_data(self,data):
        if self.href is not None:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.href is not None:self.links.append((self.href,' '.join(self.parts).strip()));self.href=None
def valid_detail(url,title):
    p=urllib.parse.urlsplit(url)
    if re.search(r'/(categories|category|topic|topics|app|learn|blog|search|tag|tags|user|about|top|help|faq)([-/]|$)',p.path):return False
    if re.search('模型|CAD|效果图|带贴图|教程|下载方法|专题|排行榜|如何|怎么|能否|求助|[?？]',title):return False
    return len(title)>=4 and bool(re.search(r'/textures/[\w-]+/?$',p.path) or (re.search(r'\d{3,}',p.path) and re.search('贴图|材质',title)))

def discover(source):
    result={'id':source['id'],'name':source['name'],'region':source['region'],'url':source['url'],'mode':'公开线索','added':0,'state':'restricted','detail':source['note']}
    try:
        parts=urllib.parse.urlsplit(source['url']);robots=parts.scheme+'://'+parts.netloc+'/robots.txt'
        try:
            raw,_,_=fetch(robots,512000);rp=urllib.robotparser.RobotFileParser();rp.parse(raw.decode('utf-8','replace').splitlines())
            if not rp.can_fetch(USER_AGENT,source['url']):result['detail']='原站robots规则不允许访问此栏目，已跳过';return [],result
        except Exception as exc:
            # 404 robots means no published rules. Other failures are not consent.
            if getattr(exc,'code',None)!=404:result['detail']='无法核实原站robots规则，暂不采集页面';return [],result
        raw,charset,final=fetch(source['url'],4*1024*1024);s=raw.decode(charset or 'utf-8','replace');parser=Anchors();parser.feed(s);found=[];seen=set()
        for href,title in parser.links:
            title=html.unescape(re.sub(r'\s+',' ',title))[:160];url=urllib.parse.urljoin(final,href);p=urllib.parse.urlsplit(url)
            if p.scheme not in ['https','http'] or p.netloc.split(':')[0].split('.')[-2:]!=parts.netloc.split('.')[-2:]:continue
            # Only actual detail paths, not category/topic/navigation links.
            if not valid_detail(url,title):continue
            if re.search('模型|CAD|效果图|带贴图|教程|合集|下载方法|专题|排行榜',title) or len(title)<4:continue
            if url in seen:continue
            seen.add(url);found.append({'id':'ref_'+hashlib.sha256(url.encode()).hexdigest()[:16],'name':title,'url':url,'provider':source['name'],'region':source['region'],'material':classify(title+' '+p.path),'kind':'原站素材线索','license':'未转存图片；下载条件与授权以原站为准'})
            if len(found)>=15:break
        result.update(state='ok' if found else 'no_entries',detail='已读取公开详情链接，未下载或转存原图' if found else '公开页面可访问，但未提取到符合条件的贴图详情；不计作新增素材')
        return found,result
    except Exception as exc:result.update(state='unavailable',detail='公开页面暂不可获取：'+str(exc)[:150]);return [],result

def run(max_new=20):
    sources=load('automation/sources.json',[]);old=load('auto-data.json',{'meta':{},'items':[]});items=list(old['items']);allitems=items[:]
    for file in ['data.json','extra-data.json','benif-data.json']:allitems+=load(file,{'items':[]})['items']
    ids=existing_ids(allitems);ids.update(x['sha256'] for x in allitems if x.get('sha256'))
    size=sum(p.stat().st_size for folder in ['images','thumbs'] for p in (ROOT/folder).rglob('*') if p.is_file());reports=[];new=0
    for source in [x for x in sources if x['mode'].endswith('_api')]:
        try:
            quota=min(10,max_new-new);added,report,size=acquire(source,ids,quota,size);items+=added;new+=len(added);reports.append(report)
        except Exception as exc:reports.append({'id':source['id'],'name':source['name'],'region':source['region'],'url':source['url'],'mode':'自动入库','state':'error','added':0,'detail':str(exc)[:160]})
    references=[x for x in load('discovery-data.json',{'items':[]})['items'] if valid_detail(x['url'],x['name'])];known={x['id'] for x in references};added_refs=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for found,report in pool.map(discover,[x for x in sources if x['mode']=='catalog']):
            for it in found:
                if it['id'] not in known:it['discovered']=datetime.datetime.now(datetime.timezone.utc).isoformat();references.append(it);known.add(it['id']);added_refs+=1;report['added']+=1
            reports.append(report)
    stamp=datetime.datetime.now(datetime.timezone.utc).isoformat();status='ok' if any(x.get('state') in ['ok','partial'] and x['mode']=='自动入库' for x in reports) else 'failed'
    save('auto-data.json',{'meta':{'updated':stamp,'total':len(items)},'items':items},'AUTO_DATA')
    save('discovery-data.json',{'meta':{'updated':stamp,'total':len(references)},'items':references[-2000:]},'DISCOVERY_DATA')
    report={'updated':stamp,'status':status,'schedule':'每天北京时间 03:23 左右；GitHub排队可能延迟','added':new,'added_references':added_refs,'auto_total':len(items),'asset_mb':round(size/1024**2,1),'budget_mb':850,'sources':reports}
    save('sync-status.json',report,'SYNC_STATUS')
    print(json.dumps(report,ensure_ascii=True),flush=True)
    if status=='failed':raise SystemExit('All automatic image providers failed; see sync-status.json')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--max-new',type=int,default=20);args=parser.parse_args();assert 0<=args.max_new<=40;run(args.max_new)
