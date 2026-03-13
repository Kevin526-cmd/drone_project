import cv2
import numpy as np
import tensorflow as tf
import tkinter as tk
from tkinter import messagebox
import os
import random
import heapq
from scipy.spatial import KDTree
from scipy.special import comb
import time 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, 'static', 'unet_model_new.h5')
image_path = os.path.join(BASE_DIR, 'static', 'map.png')

model = tf.keras.models.load_model(model_path)
original_image = cv2.imread(image_path)
if original_image is None:
    raise FileNotFoundError("錯誤：無法讀取影像，請確認路徑是否正確！")
original_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
input_size = (256, 256)
image_resized = cv2.resize(original_image, input_size) / 255.0
image_resized = np.expand_dims(image_resized, axis=0)

mask_pred = model.predict(image_resized)[0]
mask_pred = (mask_pred > 0.5).astype(np.uint8)
mask_pred = cv2.resize(mask_pred, (original_image.shape[1], original_image.shape[0]), interpolation=cv2.INTER_NEAREST)

root = tk.Tk()
root.withdraw()
# 對 mask_pred 做膨脹 (dilate) 擴大白色區域，讓道路邊緣也視為不可通行
kernel = np.ones((30, 30), np.uint8)  # 15 可調大或小
expanded_mask = cv2.dilate(mask_pred, kernel, iterations=1)

def prm_search(grid, start, goal, num_samples=10000, k=50):
    height, width = grid.shape
    free_points = [(y, x) for y in range(height) for x in range(width) if grid[y, x] == 0]
    if len(free_points) < 2:
        return None

    samples = random.sample(free_points, min(num_samples, len(free_points)))
    samples.append(start)
    samples.append(goal)

    def euclidean(p1, p2):
        return np.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def is_free_line(p1, p2):
        y_coords = np.round(np.linspace(p1[0], p2[0], 100)).astype(int)
        x_coords = np.round(np.linspace(p1[1], p2[1], 100)).astype(int)
        line = list(zip(y_coords, x_coords))
        return all(0 <= y < height and 0 <= x < width and grid[y, x] == 0 for y, x in line)

    tree = KDTree(samples)
    graph = {tuple(p): [] for p in samples}

    for p in samples:
        distances, indices = tree.query(p, k=k+1)
        for idx in indices[1:]:
            q = samples[idx]
            if is_free_line(p, q):
                graph[tuple(p)].append(tuple(q))
                graph[tuple(q)].append(tuple(p))

    def dijkstra(start, goal):
        queue = [(0, start)]
        visited = set()
        came_from = {}
        dist = {start: 0}

        while queue:
            cost, current = heapq.heappop(queue)
            if current == goal:
                path = []
                while current:
                    path.append(current)
                    current = came_from.get(current)
                return path[::-1]
            if current in visited:
                continue
            visited.add(current)
            for neighbor in graph[current]:
                new_cost = cost + euclidean(current, neighbor)
                if neighbor not in dist or new_cost < dist[neighbor]:
                    dist[neighbor] = new_cost
                    came_from[neighbor] = current
                    heapq.heappush(queue, (new_cost, neighbor))
        return None

    return dijkstra(start, goal)

def adaptive_smooth_path(path, angle_threshold=15, smooth_resolution=10, min_dist=10):
    if len(path) < 3:
        return path

    path = np.array(path)
    smoothed = [tuple(path[0])]

    def angle_between(v1, v2):
        unit_v1 = v1 / (np.linalg.norm(v1) + 1e-8)
        unit_v2 = v2 / (np.linalg.norm(v2) + 1e-8)
        dot = np.clip(np.dot(unit_v1, unit_v2), -1.0, 1.0)
        return np.arccos(dot) * 180 / np.pi

    def interpolate(p0, p1, p2, t):
        a = (1 - t) * p0 + t * p1
        b = (1 - t) * p1 + t * p2
        return ((1 - t) * a + t * b).astype(int)

    for i in range(1, len(path) - 1):
        p0, p1, p2 = path[i - 1], path[i], path[i + 1]
        if np.linalg.norm(p1 - smoothed[-1]) < min_dist:
            continue
        v1 = p1 - p0
        v2 = p2 - p1
        angle = angle_between(v1, v2)
        if angle > angle_threshold:
            for t in np.linspace(0, 1, smooth_resolution):
                pt = interpolate(p0, p1, p2, t)
                smoothed.append(tuple(pt))
        else:
            smoothed.append(tuple(p1))
    smoothed.append(tuple(path[-1]))
    return smoothed

def bezier_curve(points, n_points=200):
    points = np.array(points)
    N = len(points)
    t_values = np.linspace(0, 1, n_points)
    curve = []
    for t in t_values:
        pt = np.zeros(2)
        for i in range(N):
            b = comb(N - 1, i) * (t**(N - 1 - i)) * ((1 - t)**i)
            pt += b * np.array(points[i][::-1])  # (x, y)
        curve.append(tuple(pt.astype(int)))
    return curve

points = []
image = original_image.copy()
prev_image = image.copy()
scale_ratio = 0.5

def process_path():
    global points, image, prev_image
    start, end = points
    start_time = time.time()  # ⏱️ 開始計時
    #path = prm_search(mask_pred, start, end)
    path = prm_search(expanded_mask, start, end)


    if path:
        image = original_image.copy()
        prev_image = image.copy()
        path = adaptive_smooth_path(path)

        bezier_pts = bezier_curve(path, n_points=200)
        bezier_pts = bezier_pts[::-1]

        valid_curve = []
        for pt in bezier_pts:
            x, y = pt  # 注意 pt 是 (x, y)，mask 用 [y, x]
            if 0 <= y < expanded_mask.shape[0] and 0 <= x < expanded_mask.shape[1]:
                if expanded_mask[y, x] == 0:  # 0 = 路面
                    valid_curve.append(pt)
                else:
                    break  # 碰到草地，停止繪製

        for i in range(1, len(bezier_pts)):
            cv2.line(image, bezier_pts[i - 1], bezier_pts[i], (255, 0, 0), 5)

            temp = image.copy()
            cv2.circle(temp, (start[1], start[0]), 12, (0, 0, 255), -1)
            cv2.circle(temp, (end[1], end[0]), 12, (0, 0, 255), -1)
            display = cv2.resize(temp, (0, 0), fx=scale_ratio, fy=scale_ratio)
            cv2.imshow("Path Finder", cv2.cvtColor(display, cv2.COLOR_RGB2BGR))
            cv2.waitKey(5)

        cv2.circle(image, (start[1], start[0]), 10, (0, 0, 255), -1)
        cv2.circle(image, (end[1], end[0]), 10, (0, 0, 255), -1)

        display_image = cv2.resize(image, (0, 0), fx=scale_ratio, fy=scale_ratio)
        cv2.imshow("Path Finder", cv2.cvtColor(display_image, cv2.COLOR_RGB2BGR))
        #elapsed_time = time.time() - start_time  # ⏱️ 計算花費秒數
        #messagebox.showinfo("計算完成", f"路徑計算與顯示總花費時間：約 {elapsed_time:.3f} 秒")

        #elapsed_time = time.time() - start_time  # ⏱️ 計算花費秒數
        #print(f"🚀 路徑計算與顯示總花費時間：約 {elapsed_time:.3f} 秒")

    else:
        messagebox.showerror("路徑錯誤", "PRM 無法找到可行走路徑，請重新選擇！")

    points.clear()
    cv2.setMouseCallback("Path Finder", select_points)

def select_points(event, x, y, flags, param):
    global points, image, prev_image

    real_x = int(x / scale_ratio)
    real_y = int(y / scale_ratio)

    if event == cv2.EVENT_LBUTTONDOWN:
        if mask_pred[real_y, real_x] == 1:
            messagebox.showerror("選擇錯誤", "起點或終點在不可行走區域，請重新選擇！")
        else:
            if len(points) == 0:
                image = prev_image.copy()
            points.append((real_y, real_x))
            cv2.circle(image, (real_x, real_y), 10, (0, 0, 255), -1)
            display_image = cv2.resize(image, (0, 0), fx=scale_ratio, fy=scale_ratio)
            cv2.imshow("Path Finder", cv2.cvtColor(display_image, cv2.COLOR_RGB2BGR))
            if len(points) == 2:
                process_path()

image = original_image.copy()
display_image = cv2.resize(image, (0, 0), fx=scale_ratio, fy=scale_ratio)
cv2.imshow("Path Finder", cv2.cvtColor(display_image, cv2.COLOR_RGB2BGR))
cv2.setMouseCallback("Path Finder", select_points)



while True:
    key = cv2.waitKey(0)
    if key == 27:
        break
cv2.destroyAllWindows()
