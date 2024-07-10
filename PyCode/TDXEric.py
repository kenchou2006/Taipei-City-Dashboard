import requests
import time
from datetime import datetime, timedelta
import sched
import sqlite3
import os

# 全域變數，用來計算誤點的次數和沒有誤點的次數
delayed_count = 0
on_time_count = 0  

# TDX API 憑證
client_id = "jack306-946ef12f-2953-48a8"
client_secret = "ebbecc91-624c-416b-8d75-8b8b99630422"

# 連接 SQLite 資料庫
conn = sqlite3.connect(os.path.join('bus_delay.db'))
cursor = conn.cursor()

# TDX 類別
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
            raise Exception(f"Failed to retrieve access token: {response.status_code} - {response.text}")

    def get_response(self, url):
        headers = {'authorization': f'Bearer {self.get_token()}'}
        response = requests.get(url, headers=headers)
        return response.json()

# API URL
url = "https://tdx.transportdata.tw/api/basic/v2/Bus/EstimatedTimeOfArrival/City/Taipei?&%24format=JSON"

# 儲存每條路線的預估到站時間
estimated_arrival_times = {}
# 儲存誤點記錄
delayed_routes = {}
# 每分鐘檢查一次
check_interval = 60

def check_delays():
    global delayed_count, on_time_count  # 聲明全域變數

    tdx = TDX(client_id, client_secret)
	
    # 獲取當前資料
    current_data = tdx.get_response(url)

    # 記錄當前時間
    current_time = datetime.now()

    # 更新預估到站時間
    for item in current_data:
        route_name = item['RouteName']['Zh_tw']
        stop_name = item['StopName']['Zh_tw']
        estimate_time = item.get('EstimateTime')
        stop_status = item.get('StopStatus')

        if route_name not in estimated_arrival_times:
            estimated_arrival_times[route_name] = {}

        if estimate_time is not None and stop_status == 0:
            arrival_time = current_time + timedelta(seconds=estimate_time)
            estimated_arrival_times[route_name][stop_name] = arrival_time

    # 檢查是否誤點
    for route_name, stops in estimated_arrival_times.items():
        for stop_name, arrival_time in list(stops.items()):
            if current_time > arrival_time + timedelta(minutes=1):  # 超過預估到站時間1分鐘算誤點
                delayed_count += 1
                if route_name not in delayed_routes:
                    delayed_routes[route_name] = []
                delayed_routes[route_name].append({
                    'stop': stop_name,
                    'expected_arrival': arrival_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'actual_time': current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'delay_time': (current_time - arrival_time).seconds
                })
                del estimated_arrival_times[route_name][stop_name]  # 誤點記錄後從預估時間表中刪除
            else:
                on_time_count += 1

    # 只打印誤點和準時的公車數量
    if delayed_count > 0 or on_time_count > 0:
        print(f"總共有 {delayed_count} 班公車誤點，總共有 {on_time_count} 班公車準時，總共有{delayed_count+on_time_count}班公車")
        delayed_count = 0  # 重置誤點計數
        on_time_count = 0  # 重置準時計數

    scheduler.enter(check_interval, 1, check_delays)  # 再次安排下一次檢查

if __name__ == '__main__':
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(0, 1, check_delays)
    scheduler.run()
