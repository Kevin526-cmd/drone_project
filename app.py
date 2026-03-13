from flask import Flask, render_template, request, jsonify
import subprocess
import json
import os
import sys

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def ui():
    return render_template('ui.html')

@app.route('/run_shortest_path')
def run_shortest_path():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(BASE_DIR, 'shortest_path2.py')

    process = subprocess.Popen([sys.executable, script_path])
    return jsonify({"message": "最短路徑計算已啟動！"})


@app.route('/run_astar', methods=['POST'])
def run_astar():
    data = request.json
    points = data['points']

    start = points[0]
    end = points[1]

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    result = subprocess.run(
        [sys.executable, 'test.py', json.dumps(start), json.dumps(end)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        return jsonify({"message": "路徑計算成功！"})
    else:
        stderr_msg = result.stderr.strip()
        if "不可行走區域" in stderr_msg:
            return jsonify({"message": "此路無法行走！"})
        else:
            return jsonify({"message": f"路徑計算失敗: {stderr_msg or result.stdout.strip()}"})

if __name__ == '__main__':
    app.run(debug=True, port = 5000)
