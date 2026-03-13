// const socket = new WebSocket('ws://localhost:8765'); // 替换为你的 WebSocket 地址
const socket = new WebSocket('ws://192.168.137.1:8765');
let currentCompassAngle = 0; // 當前指南針角度 (初始化為 0)

// 讓指南針平滑旋轉的函數
function smoothRotateCompass(targetAngle) {
    function updateRotation() {
        currentCompassAngle += (targetAngle - currentCompassAngle) * 0.1;

        document.getElementById('compassNeedle').style.transform = `rotate(${currentCompassAngle}deg)`;

        // 只要當前角度與目標角度的差距大於 0.1 度，就繼續動畫
        if (Math.abs(currentCompassAngle - targetAngle) > 0.1) {
            requestAnimationFrame(updateRotation);
        }
    }

    updateRotation();
}

socket.onopen = function() {
    console.log("WebSocket connected.");
    const deviceID = 1; // 示例设备ID
    socket.send(JSON.stringify({ device_id: deviceID }));
};

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log("Received data:", data);

    // 更新设备ID
    if (data.device_id) {
        document.getElementById('device_id').innerText = `Device ${data.device_id}`;
    }

    // 更新电池电量
    if (data.data && data.data.battery_capacity !== undefined) {
        const batteryLevel = document.getElementById('battery_level_drone1');
        const batteryCapacity = data.data.battery_capacity;
        batteryLevel.style.height = `${batteryCapacity}%`;

        if (batteryCapacity < 20) {
            batteryLevel.classList.add('low');
            batteryLevel.classList.remove('medium', 'high');
        } else if (batteryCapacity < 50) {
            batteryLevel.classList.add('medium');
            batteryLevel.classList.remove('low', 'high');
        } else {
            batteryLevel.classList.add('high');
            batteryLevel.classList.remove('low', 'medium');
        }

        document.getElementById('battery_capacity').innerText = `電池:${batteryCapacity}%`;
    }

    // 更新速度表
    if (data.data && data.data.drone_speed !== undefined) {
        document.getElementById('drone_speed').innerText = `速度:${data.data.drone_speed} m/s`;
        drawSpeedometer(data.data.drone_speed);
    }

    // 更新經緯度和海拔
    if (data.data && data.data.latitude !== undefined) {
        document.getElementById('latitude').innerText = `${data.data.latitude}`;
    }
    if (data.data && data.data.longitude !== undefined) {
        document.getElementById('longitude').innerText = `${data.data.longitude}`;
    }
    if (data.data && data.data.altitude !== undefined) {
        document.getElementById('altitude').innerText = `${data.data.altitude} m`;
    }

    // 更新指南針方向 (平滑轉動)
    if (data.data && data.data.compass !== undefined) {
        const compass = data.data.compass;
        document.getElementById('compass').innerText = `航向角:${compass}°`;
        smoothRotateCompass(compass);
    }
    if (data.image_data) {
        setTimeout(() => {
            const imageElement = document.getElementById("droneCamera1");
            imageElement.src = "data:image/jpeg;base64," + data.image_data;
        }, 50); // 延遲 50ms 避免 UI 閃爍
    }
};

// === 控制拍照功能 ===
function enablePhotoCapture() {
    if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            action: "set_capture_config",
            device_id: 1,
            enabled: true,
            interval: 1
        }));
        alert("✅ 已啟用拍照");
    } else {
        alert("❌ WebSocket 尚未連線");
    }
}

function disablePhotoCapture() {
    if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            action: "set_capture_config",
            device_id: 1,
            enabled: false,
            interval: 1
        }));
        alert("🛑 已關閉拍照");
    } else {
        alert("❌ WebSocket 尚未連線");
    }
}

socket.onerror = function(error) {
    console.log("WebSocket Error:", error);
};

socket.onclose = function() {
    console.log("WebSocket closed.");
};