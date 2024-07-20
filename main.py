from flask import Flask, render_template, request, send_file
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from collections import defaultdict
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from flask_cors import CORS
import psutil

app = Flask(__name__)
CORS(app)

# 접속자 수를 저장할 딕셔너리
visitor_count = defaultdict(int)
total_visitors = 0

def fetch_menu(url, day_offset):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        menu_data = soup.select('tbody > tr > td')

        index = day_offset * 4
        breakfast = menu_data[index].text
        lunch = menu_data[index + 1].text
        dinner = menu_data[index + 2].text
        snack = menu_data[index + 3].text
        return breakfast, lunch, dinner, snack
    except requests.RequestException as e:
        return "데이터를 불러오는 데 실패했습니다.", "", "", ""
    except IndexError:
        return "데이터가 없습니다.", "", "", ""

def save_daily_visitors():
    global total_visitors
    todayDate = datetime.today().strftime('%Y-%m-%d')
    today_visitors = visitor_count[todayDate]
    with open('daily_visitors.txt', 'a') as f:
        f.write(f"{todayDate}: {today_visitors}\n")
    total_visitors += today_visitors
    visitor_count.clear()

scheduler = BackgroundScheduler()
scheduler.add_job(func=save_daily_visitors, trigger="cron", hour=0, minute=0)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())

def get_system_info():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    disk_info = psutil.disk_usage('/')

    system_info = {
        'cpu_percent': cpu_percent,
        'memory_total': memory_info.total,
        'memory_used': memory_info.used,
        'memory_percent': memory_info.percent,
        'disk_total': disk_info.total,
        'disk_used': disk_info.used,
        'disk_percent': disk_info.percent,
    }
    return system_info

@app.route('/manifest.json')
def serve_manifest():
    return send_file('manifest.json', mimetype='application/manifest+json')

@app.route('/static/sw.js')
def serve_sw():
    return send_file('static/sw.js', mimetype='application/javascript')

@app.route('/')
def index():
    days = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일']
    day_offset = request.args.get('day', default=(int(datetime.today().weekday())+1) % 7, type=int)
    url = "http://www.ggdorm.or.kr/home/main_kr/main.php?ctt=../contents_kr/m_5_5&mc=1|5|1"
    breakfast, lunch, dinner, snack = fetch_menu(url, day_offset)
    todayDate = datetime.today().strftime('%Y-%m-%d')
    defaultdays = days[(int(datetime.today().weekday())+1) % 7]

    # 오늘 날짜의 접속자 수 증가
    visitor_count[todayDate] += 1
    today_visitors = visitor_count[todayDate]

    return render_template('index.html', days=days, day=day_offset, todayDate=todayDate, defaultdays=defaultdays, todayBreakfast=breakfast, todayLunch=lunch, todayDinner=dinner, todaySnack=snack, todayVisitors=today_visitors, totalVisitors=total_visitors)


@app.route('/manage')
def manage():
    system_info = get_system_info()
    return render_template('manage.html', system_info=system_info)
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)