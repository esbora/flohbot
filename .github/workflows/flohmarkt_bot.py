# -*- coding: utf-8 -*-
"""
FlohBot: Bochum (51.4818, 7.2162) merkezli 80 km yarıçapındaki trödel/bit pazarlarını
kaynak sitelerden çekip Telegram'a "Bu hafta pazarlar" özetini gönderir.
"""
import re, math, os, requests, pytz
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dateutil import parser as dparser

BOCHUM_LAT, BOCHUM_LON = 51.4818, 7.2162
RADIUS_KM = 80
TZ = pytz.timezone("Europe/Berlin")
UA = {"User-Agent": "Mozilla/5.0 (compatible; FlohScanner/1.0)"}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2-lat1); dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(a))

def geocode_city_fallback(address_or_city: str):
    mapping = {
        "Bochum": (51.4818, 7.2162),
        "Gelsenkirchen": (51.5177, 7.0857),
        "Dortmund": (51.5136, 7.4653),
        "Dorsten": (51.6617, 6.9651),
        "Essen": (51.4556, 7.0116),
        "Herne": (51.5380, 7.2257),
        "Witten": (51.4436, 7.3526),
        "Recklinghausen": (51.6140, 7.1970),
        "Bottrop": (51.5232, 6.9285),
        "Oberhausen": (51.4963, 6.8638),
        "Duisburg": (51.4344, 6.7623),
        "Hagen": (51.3671, 7.4633),
        "Wuppertal": (51.2562, 7.1508),
        "Gladbeck": (51.5708, 6.9856),
        "Mülheim": (51.4332, 6.8797),
    }
    for k, v in mapping.items():
        if k.lower() in address_or_city.lower():
            return v
    return (BOCHUM_LAT, BOCHUM_LON)

def within_radius(city_or_addr: str):
    lat, lon = geocode_city_fallback(city_or_addr)
    return haversine(BOCHUM_LAT, BOCHUM_LON, lat, lon) <= RADIUS_KM

def parse_de_datetime(date_str, time_start=None, time_end=None):
    base = dparser.parse(date_str, dayfirst=True, fuzzy=True)
    base = datetime(base.year, base.month, base.day, 0, 0, tzinfo=TZ)
    if time_start:
        t0 = dparser.parse(time_start.strip().replace("Uhr",""), fuzzy=True, dayfirst=True)
        start = datetime(base.year, base.month, base.day, t0.hour, t0.minute, tzinfo=TZ)
    else:
        start = base.replace(hour=9)
    if time_end:
        t1 = dparser.parse(time_end.strip().replace("Uhr",""), fuzzy=True, dayfirst=True)
        end = datetime(base.year, base.month, base.day, t1.hour, t1.minute, tzinfo=TZ)
    else:
        end = start + timedelta(hours=6)
    return start, end

def fetch(url):
    r = requests.get(url, headers=UA, timeout=25)
    r.raise_for_status()
    return r.text

def scrape_marktcom_ruhrpark():
    url = "https://www.marktcom.de/veranstaltung/troedelmarkt-bochum-ruhr-park-in-44791-bochum-bochum-nord"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    events = []
    table = soup.find("table")
    if table:
        for tr in table.select("tr"):
            tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(tds) >= 2 and re.search(r"\d{2}\.\d{2}\.\d{4}", tds[0]):
                date_txt = re.search(r"\d{2}\.\d{2}\.\d{4}", tds[0]).group(0)
                times = re.findall(r"\d{1,2}:\d{2}", " ".join(tds[1:]))
                t0, t1 = (times[0] if times else "11:00"), (times[1] if len(times)>1 else "17:00")
                start, end = parse_de_datetime(date_txt, t0, t1)
                events.append({
                    "title": "Trödelmarkt Ruhr Park",
                    "city": "Bochum",
                    "venue": "Westfield Ruhr Park (P1)",
                    "address": "Am Einkaufszentrum 1, 44791 Bochum",
                    "start": start, "end": end,
                    "org": "MARKTCOM / Ostwald",
                    "src": url
                })
    else:
        txt = soup.get_text(" ", strip=True)
        for m in re.finditer(r"\d{2}\.\d{2}\.\d{4}", txt):
            date_txt = m.group(0)
            start, end = parse_de_datetime(date_txt, "11:00", "17:00")
            events.append({
                "title": "Trödelmarkt Ruhr Park", "city": "Bochum",
                "venue": "Westfield Ruhr Park (P1)",
                "address": "Am Einkaufszentrum 1, 44791 Bochum",
                "start": start, "end": end, "org": "MARKTCOM / Ostwald", "src": url
            })
    return events

def scrape_kd_poco_dorsten():
    url = "https://www.kd-maerkte.de/poco-dorsten.html"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    txt = soup.get_text(" ", strip=True)
    events = []
    for m in re.finditer(r"(\d{2}\.\d{2}\.\d{4})", txt):
        date_txt = m.group(1)
        start, end = parse_de_datetime(date_txt, "11:00", "18:00")
        events.append({
            "title": "Trödelmarkt POCO Dorsten",
            "city": "Dorsten",
            "venue": "POCO Dorsten",
            "address": "Marler Str. 137, 46282 Dorsten",
            "start": start, "end": end,
            "org": "K&D Märkte",
            "src": url
        })
    return events

def scrape_dortmund_westpark():
    url = "https://www.dortmund.de/dortmund-erleben/veranstaltungskalender/termin_98666.html"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    txt = soup.get_text(" ", strip=True)
    events = []
    for m in re.finditer(r"(\d{1,2}\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s*2025)", txt, re.IGNORECASE):
        date_txt = m.group(1)
        dt = dparser.parse(date_txt, dayfirst=True, fuzzy=True)
        start = datetime(dt.year, dt.month, dt.day, 11, 0, tzinfo=TZ)
        end   = datetime(dt.year, dt.month, dt.day, 16, 0, tzinfo=TZ)
        events.append({
            "title": "Trödelmarkt im Westpark",
            "city": "Dortmund",
            "venue": "Westpark",
            "address": "Rittershausstr., 44137 Dortmund",
            "start": start, "end": end,
            "org": "Stadt Dortmund",
            "src": url
        })
    return events

SOURCES = [
    scrape_marktcom_ruhrpark,
    scrape_kd_poco_dorsten,
    scrape_dortmund_westpark,
]

def collect_events():
    evs = []
    for fn in SOURCES:
        try:
            evs += fn()
        except Exception as e:
            print("Kaynak hatası:", fn.__name__, e)
    # Sadece radius filtresi; hafta filtresi mesaj tarafında
    evs = [e for e in evs if within_radius(f"{e['city']} {e['address']}")]
    # Dedup: (tarih, şehir, venue)
    seen=set(); out=[]
    for e in sorted(evs, key=lambda x: x["start"]):
        key=(e["start"].date(), e["city"].lower(), e["venue"].lower())
        if key in seen: continue
        seen.add(key); out.append(e)
    return out

def current_week_range(now=None):
    if not now:
        now = datetime.now(tz=TZ)
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59)
    return monday, sunday

def filter_this_week(events):
    start, end = current_week_range()
    return [e for e in events if start <= e["start"] <= end]

def fmt_event(e):
    day = e["start"].strftime("%a %d.%m")
    hrs = f"{e['start'].strftime('%H:%M')}-{e['end'].strftime('%H:%M')}"
    return f"• {day} – {e['city']}: *{e['venue']}* ({hrs}) — {e['title']}"

def build_message(events):
    week_events = filter_this_week(events)
    if not week_events:
        return "🔎 Bu hafta Bochum 80 km içinde kayıtlı pazar bulunamadı. (Kaynaklar: Marktcom, K&D, Dortmund Takvimi)"
    lines = ["🧺 *Bu hafta pazarlar* (Bochum +80 km)", ""]
    by_day = {}
    for e in week_events:
        d = e["start"].strftime("%Y-%m-%d")
        by_day.setdefault(d, []).append(e)
    for d in sorted(by_day.keys()):
        # başlık için günün adını e'nin saatinden üretelim
        hdr_dt = by_day[d][0]["start"]
        hdr = hdr_dt.strftime("📅 *%A* %d.%m")
        lines.append(hdr)
        for e in by_day[d]:
            lines.append(fmt_event(e))
        lines.append("")
    lines.append("_Kaynak örnekleri: Marktcom, K&D Märkte, Stadt Dortmund_")
    return "\n".join(lines)

def tg_send_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise SystemExit("Env eksik: TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID gerekli.")
    all_events = collect_events()
    msg = build_message(all_events)
    print(msg)
    tg_send_message(token, chat_id, msg)

if __name__ == "__main__":
    main()
