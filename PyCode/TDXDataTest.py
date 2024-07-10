import requests
import time
from datetime import datetime, timedelta
import sched
import sqlite3

conn = sqlite3.connect(r'docker\bus_delay.db')
cursor = conn.cursor()

# 創建新的表格來存儲每日統計數據
cursor.execute("""
CREATE TABLE IF NOT EXISTS daily_stats (
    date TEXT,
    route_name TEXT,
    delayed_count INTEGER,
    on_time_count INTEGER,
    PRIMARY KEY (date, route_name)
)
""")
conn.commit()

client_id = "jack306-946ef12f-2953-48a8"
client_secret = "ebbecc91-624c-416b-8d75-8b8b99630422"

class TDX:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires_at = None

    def get_token(self):
        if self.access_token and datetime.now() < self.token_expires_at:
            return self.access_token

        token_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            self.token_expires_at = datetime.now() + timedelta(seconds=response.json()['expires_in'])
            return self.access_token
        else:
            raise Exception(f"無法獲取存取權杖：{response.status_code} - {response.text}")

    def get_response(self, url):
        headers = {'authorization': f'Bearer {self.get_token()}'}
        response = requests.get(url, headers=headers)
        return response.json()

url = "https://tdx.transportdata.tw/api/basic/v2/Bus/EstimatedTimeOfArrival/City/Taipei?&%24format=JSON"

bus_stops = {}  # 儲存每個公車站的資訊
check_interval = 60  # 每分鐘檢查一次
tolerance = 120  # 容許誤差（秒）

def calculate_delay(expected_time, actual_time):
    delay = max(0, int((actual_time - expected_time).total_seconds()))
    return delay

def format_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def update_daily_stats(route_name, is_delayed):
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        INSERT INTO daily_stats (date, route_name, delayed_count, on_time_count)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(date, route_name) DO UPDATE SET
        delayed_count = delayed_count + ?,
        on_time_count = on_time_count + ?
    """, (today, route_name, 1 if is_delayed else 0, 0 if is_delayed else 1,
          1 if is_delayed else 0, 0 if is_delayed else 1))
    conn.commit()

    # 打印更新的數據
    cursor.execute("""
        SELECT * FROM daily_stats
        WHERE date = ? AND route_name = ?
    """, (today, route_name))
    result = cursor.fetchone()
    print(f"已更新數據庫: 日期={result[0]}, 路線={result[1]}, 誤點次數={result[2]}, 準時次數={result[3]}")

def check_delays():
    tdx = TDX(client_id, client_secret)
    current_data = tdx.get_response(url)
    current_time = datetime.now().replace(microsecond=0)

    for item in current_data:
        route_name = item['RouteName']['Zh_tw']
        stop_name = item['StopName']['Zh_tw']
        estimate_time = item.get('EstimateTime')
        stop_status = item.get('StopStatus')

        key = (route_name, stop_name)

        if key not in bus_stops:
            bus_stops[key] = {
                'estimate_time': estimate_time,
                'expected_arrival': (current_time + timedelta(seconds=estimate_time)).replace(microsecond=0) if estimate_time else None,
                'status': stop_status,
                'last_update': current_time
            }
        else:
            if stop_status == 1 and bus_stops[key]['status'] == 0:
                # 公車已到站
                actual_arrival = current_time
                expected_arrival = bus_stops[key]['expected_arrival']
                
                if expected_arrival:
                    delay = calculate_delay(expected_arrival, actual_arrival)
                    is_delayed = delay > tolerance
                    update_daily_stats(route_name, is_delayed)
                    print(f"路線 {route_name} 在站點 {stop_name} {'誤點' if is_delayed else '準時'}到達")

                # 重置站點資訊
                bus_stops[key] = {
                    'estimate_time': estimate_time,
                    'expected_arrival': (current_time + timedelta(seconds=estimate_time)).replace(microsecond=0) if estimate_time else None,
                    'status': stop_status,
                    'last_update': current_time
                }
            elif stop_status == 0:
                # 如果公車還沒到站，更新預估時間
                bus_stops[key]['estimate_time'] = estimate_time
                bus_stops[key]['expected_arrival'] = (current_time + timedelta(seconds=estimate_time)).replace(microsecond=0) if estimate_time else None
                bus_stops[key]['last_update'] = current_time
            
            bus_stops[key]['status'] = stop_status

    # 檢查應該已經到達但尚未到達的公車
    for key, stop_info in list(bus_stops.items()):
        if stop_info['expected_arrival'] and current_time > stop_info['expected_arrival'] + timedelta(seconds=tolerance):
            route_name, stop_name = key
            update_daily_stats(route_name, True)
            print(f"路線 {route_name} 在站點 {stop_name} 誤點（未到站）")
            
            # 從追蹤列表中移除此站點
            del bus_stops[key]

    # 安排下一次檢查
    scheduler.enter(check_interval, 1, check_delays)

if __name__ == '__main__':
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(0, 1, check_delays)
    scheduler.run()