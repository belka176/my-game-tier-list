import argparse, json, os, time, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'steam-imported-games.js'; STATE=ROOT/'.steam-import-state.json'; COVERS=ROOT/'covers'/'steam'
LIST_URL='https://api.steampowered.com/IStoreService/GetAppList/v1/'
DETAILS_URL='https://store.steampowered.com/api/appdetails'
HEADERS={'User-Agent':'GameTierSteamImporter/1.0 (local catalog importer)'}
GENRES={'Action':'Экшен','Adventure':'Приключения','Indie':'Инди','RPG':'RPG','Strategy':'Стратегии','Simulation':'Симуляторы','Racing':'Гонки','Sports':'Спорт','Casual':'Казуальные','Massively Multiplayer':'Онлайн','Free To Play':'Онлайн'}

def load_env():
    path=ROOT/'.env'
    if not path.exists():return
    for raw in path.read_text(encoding='utf-8').splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line:continue
        name,value=line.split('=',1)
        os.environ.setdefault(name.strip(),value.strip().strip('"').strip("'"))

def request_json(url,params):
    req=urllib.request.Request(url+'?'+urllib.parse.urlencode(params),headers=HEADERS)
    with urllib.request.urlopen(req,timeout=60) as response:return json.load(response)

def app_list(key,limit,cursor):
    data=request_json(LIST_URL,{'key':key,'include_games':1,'include_dlc':0,'include_software':0,'include_videos':0,'include_hardware':0,'max_results':limit,'last_appid':cursor}).get('response',{})
    return data.get('apps',[]),bool(data.get('have_more_results')),int(data.get('last_appid',cursor))

def details(appid):
    for country in ('ru','us'):
        item=request_json(DETAILS_URL,{'appids':appid,'l':'russian','cc':country}).get(str(appid),{})
        if item.get('success') and isinstance(item.get('data'),dict):return item['data']

def download(url,target):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=60) as response:data=response.read()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);return True
    except Exception:return False

def cover(appid,data):
    target=COVERS/f'{appid}.jpg'
    portrait=f'https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900.jpg'
    if download(portrait,target) or (data.get('header_image') and download(data['header_image'],target)):
        return target.relative_to(ROOT).as_posix()
    return ''

def load_games():
    if not OUTPUT.exists():return []
    text=OUTPUT.read_text(encoding='utf-8').strip();prefix='const steamImportedGames='
    try:return json.loads(text[len(prefix):].rstrip(';')) if text.startswith(prefix) else []
    except json.JSONDecodeError:return []

def load_state():
    try:return json.loads(STATE.read_text(encoding='utf-8'))
    except (FileNotFoundError,json.JSONDecodeError):return {'lastAppId':0,'failed':[]}

def save(games,state):
    payload=json.dumps(games,ensure_ascii=False,separators=(',',':'))
    OUTPUT.write_text('const steamImportedGames='+payload+';\n',encoding='utf-8')
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def year(data):
    parts=str(data.get('release_date',{}).get('date','')).replace(',',' ').split()
    years=[part for part in parts if len(part)==4 and part.isdigit()]
    return int(years[-1]) if years else 0

def convert(app,data,minimum):
    if data.get('type')!='game':return None,'not a game'
    popularity=int(data.get('recommendations',{}).get('total',0))
    if popularity<minimum:return None,f'only {popularity} recommendations'
    appid=int(app['appid']);source_genres=[x.get('description','') for x in data.get('genres',[])]
    genre=next((GENRES[x] for x in source_genres if x in GENRES),'Другое')
    score=data.get('metacritic',{}).get('score')
    return {'id':appid,'name':data.get('name') or app.get('name') or f'Game {appid}','genre':genre,'year':year(data),'studio':', '.join(data.get('developers') or []) or 'Неизвестная студия','rating':round(float(score)/10,1) if score else 0,'popularity':popularity,'cover':cover(appid,data),'source':'steam-import','catalogSource':'steam-import','steamAppId':appid},'added'

def main():
    load_env()
    parser=argparse.ArgumentParser(description='Batch-import popular Steam games into GameTier')
    parser.add_argument('--limit',type=int,default=20);parser.add_argument('--delay-ms',type=int,default=1500)
    parser.add_argument('--last-appid',type=int);parser.add_argument('--min-recommendations',type=int,default=0)
    parser.add_argument('--retry-failed',action='store_true');args=parser.parse_args()
    key=os.environ.get('STEAM_API_KEY','').strip()
    if not key:raise SystemExit('STEAM_API_KEY is missing. Get one at https://steamcommunity.com/dev/apikey')
    state=load_state();stored=load_games();by_id={int(x['steamAppId']):x for x in stored if x.get('steamAppId')}
    if args.retry_failed and state.get('failed'):
        apps=[{'appid':x,'name':''} for x in state['failed']];more=bool(state.get('hasMore',True));cursor=int(state.get('lastAppId',0))
    else:
        start=args.last_appid if args.last_appid is not None else int(state.get('lastAppId',0))
        apps,more,cursor=app_list(key,args.limit,start)
    failed=[]
    for index,app in enumerate(apps):
        appid=int(app['appid'])
        try:
            data=details(appid)
            if not data:raise RuntimeError('appdetails unavailable')
            game,result=convert(app,data,args.min_recommendations)
            if game:by_id[appid]=game
            print(f'{appid}: {data.get("name") or app.get("name")} - {result}')
        except Exception as error:failed.append(appid);print(f'{appid}: error - {error}')
        if index+1<len(apps):time.sleep(max(0,args.delay_ms)/1000)
    games=sorted(by_id.values(),key=lambda x:(-int(x.get('popularity',0)),x['name'].casefold()))
    save(games,{'lastAppId':cursor,'failed':failed,'hasMore':more,'updatedAt':time.strftime('%Y-%m-%dT%H:%M:%S')})
    print(f'Done: {len(games)} local Steam games; {len(failed)} errors; cursor {cursor}.')

if __name__=='__main__':main()
