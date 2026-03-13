# Drone-based Victim Detection and Shortest Path Planning System
# 基於無人機影像之受困者偵測與最短救援路徑規劃系統

## Project Overview
This project aims to use drone aerial images for disaster scene analysis, detecting possible trapped victims under debris and computing the shortest rescue path to the target location. The system integrates image recognition, coordinate mapping, and path planning algorithms to improve the efficiency of disaster response and rescue operations.

本專案利用無人機空拍影像進行災害場域分析，偵測是否存在遭受壓埋之受困者，並結合最短路徑規劃演算法，協助救援人員快速找到目標位置。系統整合影像辨識、座標定位與路徑規劃，以提升搜救效率。

## Motivation
In disaster rescue scenarios, responders need to quickly identify victim locations and determine an efficient route to reach them. By combining drone imaging with AI-based detection and shortest path planning, this project provides a practical framework for intelligent rescue assistance.

在災害搜救場景中，救援人員需要快速確認受困者位置，並規劃有效率的移動路徑。本專案結合無人機影像、人工智慧辨識與最短路徑規劃，作為智慧搜救輔助系統的基礎。

## Features
- 可以自行規劃無人機要飛行路徑
- 飛行時自行拍攝照片並進行自動拼接
- 顯示受困者位置
- 建立地圖與顯示受災者座標
- Shortest path planning for rescue
- Visualization of detection and path results

## Technologies
- Python / html / javascript / css
- ROS
- OpenCV
- YOLO / image recognition model / Unet
- Dijkstra / PRM
- Drone integration / simulation
- Backend / Database: MySQL / Flask / FastAPI
- Visualization: map interface

## System Workflow
1. Capture aerial images using a drone
2. Analyze images with a detection model
3. Identify possible trapped victims
4. Convert target location into map coordinates
5. Compute the shortest rescue path
6. Display detection and path planning results

## My Role
- 負責無人機系統整合與模擬測試
- 協助空拍資料取得與影像處理流程串接
- 參與受困者辨識流程設計
- 設計無人機的飛行
- 協助系統測試、結果展示與功能驗證

## Project Structure
```text
project/
│── data/
│── models/
│── drone_module/
│── path_planning/
│── results/
│── README.md