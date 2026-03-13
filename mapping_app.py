# app.py
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
import threading
import queue
import time

app = Flask(__name__)
CORS(app)

# 創建一個線程安全的佇列來存儲日誌
log_queue = queue.Queue()
mapping_status = {
    "status": "idle", 
    "message": "", 
    "progress": 0,
    "logs": []
}

def capture_output(process, queue):
    """捕獲進程的輸出"""
    try:
        for line in process.stdout:
            line = line.strip()
            queue.put(line)
            print(line)  # 同時在控制台打印
        process.wait()
    except Exception as e:
        queue.put(f"Error: {str(e)}")

@app.route('/')
def index():
    return send_file("ui.html")

@app.route('/mapping_status', methods=['GET'])
def get_mapping_status():
    """提供建圖狀態的端點"""
    # 收集佇列中的最新日誌
    current_logs = []
    while not log_queue.empty():
        current_logs.append(log_queue.get())
    
    mapping_status['logs'] = current_logs
    return jsonify(mapping_status)

@app.route('/select_folder', methods=['POST'])
def select_folder():
    global mapping_status
    try:
        # 重置狀態
        mapping_status = {
            "status": "processing", 
            "message": "開始建圖", 
            "progress": 0,
            "logs": []
        }
        
        # 使用子進程執行建圖腳本
        process = subprocess.Popen(
            ["python", "dronemapping.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # 啟動線程來捕獲輸出
        output_thread = threading.Thread(
            target=capture_output, 
            args=(process, log_queue)
        )
        output_thread.start()

        # 如果成功，返回初始響應
        return jsonify({
            "message": "建圖進行中",
            "status": "processing"
        }), 200

    except Exception as e:
        mapping_status['status'] = 'error'
        mapping_status['message'] = f"執行錯誤: {str(e)}"
        return jsonify(mapping_status), 500

if __name__ == '__main__':
    app.run(debug=True, port=8800)