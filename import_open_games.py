import csv, io, json, urllib.request
from pathlib import Path

BASE='https://raw.githubusercontent.com/karlforshaw/opengamedb/master/'
FILES={
 'super_nintendo_entertainment_system.csv':'Super Nintendo',
 'game_boy_advance.csv':'Game Boy Advance',
 'wii.csv':'Nintendo Wii',
 'wii_u.csv':'Nintendo Wii U',
 'dreamcast.csv':'Sega Dreamcast',
 'xbox.csv':'Xbox',
}
GENRES={'role-playing':'RPG','action adventure':'Приключения','action':'Экшен','adventure':'Приключения','strategy':'Стратегии','simulation':'Симуляторы','sports':'Спорт','racing':'Гонки','puzzle':'Головоломки','fighting':'Файтинги','platform':'Платформеры','shooter':'Шутеры','horror':'Хоррор'}

def translated(value):
 value=value.strip().lower()
 return next((result for marker,result in GENRES.items() if marker in value),'Другое')

existing=Path('games-data.js').read_text(encoding='utf-8').casefold()
items=[];seen=set()
for filename,platform in FILES.items():
 request=urllib.request.Request(BASE+filename,headers={'User-Agent':'GameTierCatalog/1.0'})
 with urllib.request.urlopen(request,timeout=90) as response:
  text=response.read().decode('utf-8-sig','replace')
 for row in csv.DictReader(io.StringIO(text)):
  name=(row.get('title') or '').strip()
  if not name or name.casefold() in seen or json.dumps(name,ensure_ascii=False)[1:-1].casefold() in existing:continue
  seen.add(name.casefold());released=(row.get('released') or '')
  raw_score=row.get('gf_score') or '';score=round(float(raw_score)*2,1) if raw_score.replace('.','',1).isdigit() else 0
  items.append({'id':f'og-{len(items)+1}','name':name,'genre':translated(row.get('genre') or ''),'year':int(released[:4]) if released[:4].isdigit() else 0,'studio':platform,'rating':score,'cover':(row.get('cover_art_url') or '').strip(),'source':'opengamedb'})
  if len(items)==600:break
 if len(items)==600:break
if len(items)<600:raise RuntimeError(f'Open Game DB returned only {len(items)} unique new games')
Path('wikidata-games.js').write_text('const openCatalogGames='+json.dumps(items,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
print(f'Wrote {len(items)} unique non-Steam games; {sum(bool(x["cover"]) for x in items)} have cover links')
