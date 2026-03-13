# test_client.py

import asyncio
import websockets
import json
import random

# 連線參數
WS_URI      = "ws://localhost:8765"
DEVICE_ID   = 1      
SEND_COUNT  = 0      
INTERVAL_S  = 1.0    

async def send_sensor_data(ws):
    
    i = 0
    while SEND_COUNT == 0 or i < SEND_COUNT:
        sensor_msg = {
            "latitude":         round(random.uniform(24.0, 26.0), 10),
            "longitude":        round(random.uniform(120.0, 122.0), 10),
            "altitude":         random.randint(0, 500),
            "battery_capacity": random.randint(0, 100),
            "compass":          random.randint(0, 359),
            "drone_speed":      round(random.uniform(0, 20), 2)
        }
        await ws.send(json.dumps(sensor_msg))
        print(f"[SEND#{i+1}] {sensor_msg}")
        i += 1
        await asyncio.sleep(INTERVAL_S)

async def recv_loop(ws):
    
    async for msg in ws:
        try:
            data = json.loads(msg)
            print("← RECV:", data)
        except json.JSONDecodeError:
            print(f"← RECV (非 JSON，長度 {len(msg)} bytes)")

async def main():
    async with websockets.connect(WS_URI) as ws:
        
        init = {"device_id": DEVICE_ID}
        await ws.send(json.dumps(init))
        print("→ 已送出初始化註冊：", init)

        
        await asyncio.gather(
            send_sensor_data(ws),
            recv_loop(ws),
        )

if __name__ == "__main__":
    asyncio.run(main())
