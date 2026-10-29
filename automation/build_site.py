import json,pathlib,shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'_site';OUT.mkdir(exist_ok=True)
names=['index.html','library.css','library.js','resources.js','auto-ui.js','auto-ui.css','README.md','.nojekyll']
names += [stem+suffix for stem in ['data','extra-data','benif-data','auto-data','discovery-data','sync-status'] for suffix in ['.js','.json']]
for name in names:shutil.copy2(ROOT/name,OUT/name)
assets=set()
for file in ['data.json','extra-data.json','benif-data.json','auto-data.json']:
    for it in json.loads((ROOT/file).read_text(encoding='utf-8-sig'))['items']:
        for key in ['image','thumb']:
            value=it[key];path=(ROOT/value).resolve();assert path.is_relative_to(ROOT) and path.is_file(),value;assets.add(value)
for value in assets:
    target=OUT/value;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/value,target)
size=sum(x.stat().st_size for x in OUT.rglob('*') if x.is_file());assert size<950*1024*1024,'Published website exceeds safe Pages size'
print('Website assets:',len(assets),'size MB:',round(size/1024**2,1))
