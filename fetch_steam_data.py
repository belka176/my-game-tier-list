import html, json, re, urllib.parse, urllib.request

NAMES=['PRAGMATA','Resident Evil 5','Resident Evil Revelations 2','Counter-Strike 2','House Flipper 2','Tiny Bunny','Dispatch','Heavy Rain','Far Cry New Dawn','Deadlock','YAPYAP','RV There Yet?','In Silence','Fast Food Simulator','Ghost Watchers',"Liar's Bar",'Hand Simulator']
HEADERS={'User-Agent':'Mozilla/5.0 GameTier local catalog'}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=60) as response:
        return response.read().decode('utf-8','replace')

matches={}
for name in NAMES:
    url='https://store.steampowered.com/search/suggest?'+urllib.parse.urlencode({'term':name,'f':'games','cc':'US','l':'english'})
    page=get(url)
    found=re.search(r'data-ds-appid="(\d+)"[\s\S]*?<div class="match_name">([^<]+)',page)
    if found:matches[name]={'appId':int(found.group(1)),'matchedName':html.unescape(found.group(2)).strip()}

chart=get('https://store.steampowered.com/charts/mostplayed')
app_ids=[]
for app_id in re.findall(r'/app/(\d+)',chart):
    app_id=int(app_id)
    if app_id not in app_ids:app_ids.append(app_id)

print(json.dumps({'matches':matches,'mostPlayed':app_ids[:100]},ensure_ascii=False,indent=2))
