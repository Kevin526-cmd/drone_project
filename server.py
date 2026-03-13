import asyncio
import websockets
import json
import mysql.connector
from mysql.connector import Error, pooling
import base64
import subprocess
import numpy as np
import cv2

# === 設置 MySQL 連線池 ===
db_pool = None
map_db_pool = None

def init_db_pool():
    global db_pool
    if db_pool is None:
        try:
            db_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="mypool",
                pool_size=5,
                host="localhost",
                user="root",
                password="Kevin05298766",
                database="device_data"
            )
            print("Device Database connection pool initialized.")
        except Error as e:
            print(f"Error initializing device database pool: {e}")
            db_pool = None

def init_map_db_pool():
    global map_db_pool
    if map_db_pool is None:
        try:
            map_db_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="map_pool",
                pool_size=5,
                host="localhost",
                user="root",
                password="Kevin05298766",
                database="map_data"
            )
            print("Map Database connection pool initialized.")
        except Error as e:
            print(f"Error initializing map database pool: {e}")
            map_db_pool = None

def get_db_connection():
    if db_pool:
        return db_pool.get_connection()
    return None

def get_map_db_connection():
    if map_db_pool:
        return map_db_pool.get_connection()
    return None

def save_waypoints_to_map_db(waypoints):
    conn = get_map_db_connection()
    if not conn:
        print("錯誤: 無法獲取 map_data 資料庫連線")
        return {"status": "error", "message": "無法連接 map_data 資料庫"}

    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO waypoints (point_index, latitude, longitude)
            VALUES (%s, %s, %s)
        """
        for wp in waypoints:
            cursor.execute(query, (wp["point_index"], wp["latitude"], wp["longitude"]))
        
        conn.commit()  # 確保資料提交
        print("標記點成功儲存到 map_data")

        return {"status": "success", "message": "標記點已成功儲存到 map_data"}
    
    except Error as e:
        print(f"資料庫錯誤: {e}")
        return {"status": "error", "message": str(e)}
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_device_data_from_db(device_id):
    db_conn = get_db_connection()
    if db_conn:
        try:
            cursor = db_conn.cursor(dictionary=True)
            query = """
                SELECT * FROM drone WHERE device_id = %s ORDER BY id DESC LIMIT 1
            """
            cursor.execute(query, (device_id,))
            result = cursor.fetchone()
            return result
        except Error as e:
            return None
        finally:
            cursor.close()
            db_conn.close()

async def handle_camera_data(device_id, data):
    encoded_image = base64.b64encode(data).decode('utf-8')
    response = {"device_id": device_id, "image_data": encoded_image}
    await asyncio.gather(*[client.send(json.dumps(response)) for client in connected_clients])

stored_waypoints = []

connected_clients = {}

async def handler(websocket, path):
    global stored_waypoints  # 確保 stored_waypoints 可以被修改
    try:
        init_message = await websocket.recv()
        init_data = json.loads(init_message)
        device_id = int(init_data.get("device_id", -1))
        connected_clients[websocket] = device_id
        print(f"設備 {device_id} 連線成功")

        # 發送已存儲的 waypoints
        if stored_waypoints:
            await websocket.send(json.dumps({"type": "waypoints", "waypoints": stored_waypoints}))

        # 發送該設備的最新數據
        device_data = get_device_data_from_db(device_id)
        if device_data:
            await websocket.send(json.dumps({"device_id": device_id, "data": device_data}))

        while True:
            message = await websocket.recv()

            if isinstance(message, bytes):  # 判斷是否為影像數據
                print(f"設備 {device_id} 傳來影像數據 ({len(message)} bytes)")
                await handle_camera_data(device_id, message)

            else:  # 處理 JSON 文字數據
                data = json.loads(message)
                
                # 印出接收到的感測數據
                print(f"來自 {device_id} 的感測數據: {data}")

                if data.get("type") == "save_waypoints":
                    response = save_waypoints_to_map_db(data["waypoints"])
                    await websocket.send(json.dumps(response))
                    stored_waypoints = data["waypoints"]
                    
                    broadcast_data = {"type": "waypoints", "waypoints": stored_waypoints}
                    await asyncio.gather(*[client.send(json.dumps(broadcast_data)) for client in connected_clients])

                elif "latitude" in data:
                    db_conn = get_db_connection()
                    if db_conn:
                        try:
                            cursor = db_conn.cursor()
                            insert_query = """
                            INSERT INTO drone (device_id, latitude, longitude, altitude, battery_capacity, compass, drone_speed)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(insert_query, (
                                device_id, data.get("latitude", 0.0), 
                                data.get("longitude", 0.0),
                                data.get("altitude", 0), 
                                data.get("battery_capacity", 0),
                                data.get("compass", 0), 
                                data.get("drone_speed", 0)
                            ))
                            db_conn.commit()
                        except Error as e:
                            print(f"資料庫錯誤: {e}")
                        finally:
                            cursor.close()
                            db_conn.close()

                elif data.get("action") == "set_capture_config":
                    config = {
                        "type": "capture_config",
                        "enabled": data["enabled"],      # bool
                        "interval": data["interval"]     # int 秒數
                    }
                    # 傳送給指定 device_id 的 client
                    for client, did in connected_clients.items():
                        if did == device_id:
                            await client.send(json.dumps(config))
                            print(f"📤 已轉發拍照設定給設備 {device_id}: {config}")
    

    except websockets.exceptions.ConnectionClosed:
        print(f"裝置 {connected_clients.get(websocket, '未知')} 斷開連線")
    finally:
        connected_clients.pop(websocket, None)

async def send_periodic_data():
    while True:
        await asyncio.sleep(0.1)
        for websocket in connected_clients:
            device_id = connected_clients[websocket]
            device_data = get_device_data_from_db(device_id)
            if device_data:
                await websocket.send(json.dumps({"device_id": device_id, "data": device_data}))

async def start_websocket_server():
    init_db_pool()
    init_map_db_pool()
    # server = await websockets.serve(handler, "localhost", 8765)
    server = await websockets.serve(handler, "192.168.137.1", 8765)
    print("WebSocket 伺服器已啟動")
    asyncio.create_task(send_periodic_data())
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(start_websocket_server()) 


