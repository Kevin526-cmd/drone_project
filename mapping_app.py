from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
import threading
import queue
import time

app = Flask(__name__)
CORS(app)


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
            print(line) 
        process.wait()
    except Exception as e:
        queue.put(f"Error: {str(e)}")

@app.route('/')
def index():
    return send_file("ui.html")

@app.route('/mapping_status', methods=['GET'])
def get_mapping_status():
    """提供建圖狀態的端點"""
  
    current_logs = []
    while not log_queue.empty():
        current_logs.append(log_queue.get())
    
    mapping_status['logs'] = current_logs
    return jsonify(mapping_status)

@app.route('/select_folder', methods=['POST'])
def select_folder():
    global mapping_status
    try:
       
        mapping_status = {
            "status": "processing", 
            "message": "開始建圖", 
            "progress": 0,
            "logs": []
        }
        
        
        process = subprocess.Popen(
            ["python", "dronemapping.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

       
        output_thread = threading.Thread(
            target=capture_output, 
            args=(process, log_queue)
        )
        output_thread.start()

       
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