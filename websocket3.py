import asyncio
import websockets
import json
import cv2
import numpy as np
import os
import math
import rospy
import time
import threading
from sensor_msgs.msg import NavSatFix, BatteryState
from std_msgs.msg import Float64
from nav_msgs.msg import Odometry

capture_enabled = False
capture_interval = 1  # 每幾秒拍一張
last_capture_time = 0
latest_frame = None

device_id = "1"

# 攝影機初始化
cap = cv2.VideoCapture(0)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = 30

# 錄影設定
recording_enabled = True
video_writer = None
video_output_path = f"video_{time.strftime('%Y%m%d_%H%M%S')}.mp4"

# ROS 數據變數
latitude_deg = 0.0
longitude_deg = 0.0
altitude = 0.0
compass = 0
battery_capacity = 100
drone_speed = 0.0

def global_pos_callback(data):
    global latitude_deg, longitude_deg, altitude
    latitude_deg = round(data.latitude, 6)
    longitude_deg = round(data.longitude, 6)
    altitude = round(data.altitude, 2)

def compass_callback(data):
    global compass
    compass = int(data.data)

def battery_status_callback(data):
    global battery_capacity
    battery_capacity = int(data.percentage * 100)

def local_velocity_callback(data):
    global drone_speed
    vx = data.twist.twist.linear.x
    vy = data.twist.twist.linear.y
    vz = data.twist.twist.linear.z
    drone_speed = round(math.sqrt(vx**2 + vy**2 + vz**2), 2)

def initialize_ros_subscribers():
    rospy.init_node('vehicle_listener', anonymous=True)
    rospy.Subscriber('/mavros/global_position/global', NavSatFix, global_pos_callback)
    rospy.Subscriber('/mavros/global_position/compass_hdg', Float64, compass_callback)
    rospy.Subscriber('/mavros/global_position/local', Odometry, local_velocity_callback)
    rospy.Subscriber('/mavros/battery', BatteryState, battery_status_callback)

initialize_ros_subscribers()

# 攝影機讀取主循環

def camera_reader_loop():
    global latest_frame
    while True:
        ret, frame = cap.read()
        if ret:
            latest_frame = frame
        time.sleep(1 / fps)

# 拍照循環

def photo_capture_loop():
    global last_capture_time
    while True:
        if capture_enabled and latest_frame is not None:
            current_time = time.time()
            if current_time - last_capture_time >= capture_interval:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                save_dir = "photos"
                os.makedirs(save_dir, exist_ok=True)
                cv2.imwrite(os.path.join(save_dir, f"photo_{timestamp}.jpg"), latest_frame)
                last_capture_time = current_time
        time.sleep(0.1)

# 擷取 JPEG bytes

async def capture_camera_frame_bytes():
    if latest_frame is not None:
        resized_frame = cv2.resize(latest_frame, (320, 240))
        _, buffer = cv2.imencode('.jpg', resized_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 30])
        return latest_frame, buffer.tobytes()
    return None, None

async def send_data():
    uri = "ws://192.168.31.145:8765"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"device_id": device_id}))
        print(f"✅ 設備 {device_id} 已連線到伺服器")

        async def receive_pings():
            while True:
                try:
                    await websocket.ping()
                    await asyncio.sleep(10)
                except websockets.exceptions.ConnectionClosed:
                    print("❌ 連線已斷開！")
                    break

        async def handle_incoming():
            global capture_enabled, capture_interval
            while True:
                message = await websocket.recv()
                try:
                    data = json.loads(message)
                    if data.get("type") == "waypoints":
                        waypoints = data["waypoints"]
                        print("📍 收到飛控點位:", waypoints)
                        with open("waypoints.txt", "w", encoding="utf-8") as f:
                            for wp in waypoints:
                                f.write(f"{wp['latitude']}, {wp['longitude']}\n")
                        print("✅ 成功寫入 waypoints.txt")

                    elif data.get("type") == "capture_config":
                        capture_enabled = data.get("enabled", False)
                        capture_interval = data.get("interval", 1)
                        print(f"⚙️ 設定更新: 拍照功能 = {capture_enabled}, 間隔 = {capture_interval} 秒")
                except json.JSONDecodeError:
                    pass

        asyncio.create_task(receive_pings())
        asyncio.create_task(handle_incoming())

        global video_writer
        while True:
            frame, frame_bytes = await capture_camera_frame_bytes()

            if frame is not None and recording_enabled:
                try:
                    if video_writer is None:
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        video_writer = cv2.VideoWriter(video_output_path, fourcc, fps, (frame_width, frame_height))
                    video_writer.write(frame)
                except Exception as e:
                    print(f"⚠️ 錄影失敗: {e}")

            sensor_data = {
                "longitude": longitude_deg,
                "latitude": latitude_deg,
                "altitude": altitude,
                "battery_capacity": battery_capacity,
                "compass": compass,
                "drone_speed": drone_speed
            }

            try:
                await websocket.send(json.dumps(sensor_data))
                await asyncio.sleep(0.01)
                if frame_bytes:
                    await websocket.send(frame_bytes)
            except websockets.exceptions.ConnectionClosed:
                print("❌ 連線已斷開，嘗試重新連線...")
                break

if __name__ == "__main__":
    try:
        threading.Thread(target=camera_reader_loop, daemon=True).start()
        threading.Thread(target=photo_capture_loop, daemon=True).start()
        asyncio.run(send_data())
    finally:
        cap.release()
        if video_writer:
            video_writer.release()
            print(f"📽️ 錄影已完成，儲存為 {video_output_path}")