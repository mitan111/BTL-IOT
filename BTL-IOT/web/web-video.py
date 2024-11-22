from flask import Flask, Response, render_template, jsonify, request, redirect, url_for, session
import cv2
import time
from ultralytics import YOLO
import serial
import threading
import os
import mysql.connector

os.urandom(12)

app = Flask(__name__)
app.secret_key = os.urandom(12).hex()

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="iot"
)

model = YOLO('vehicle-detection.pt')
class_names = ['bus', 'car', 'motorbike','truck']

video_1 = "video-1.mp4"
video_2 = "video-2.mp4"

arduino = serial.Serial('COM3', 9600)
time.sleep(2)  # Đợi kết nối được thiết lập

# Biến toàn cục cho mọi thứ
car_count_vid_1 = 0
motobike_count_vid_1 = 0
car_count_vid_2 = 0
motobike_count_vid_2 = 0

green_time = 20
red_time = 20

manual_green_time = 20
manual_red_time = 20

is_green = True
is_automatic_mode = True
state = 0

# Hàm để đếm số lượng phương tiện trong khung hình
def get_traffic_density(frame):
    results = model(frame)
    car_count = 0
    motobike_count = 0
    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])
            currentClass = class_names[cls]
            if currentClass == "car" or currentClass == "bus" or currentClass == "truck":
                car_count += 1
            else:
                motobike_count += 1
    return car_count, motobike_count

# Hàm để tính toán thời gian đèn giao thông (mỗi xe otô sẽ cộng thêm 1.5 giây, mỗi xe máy sẽ cộng 0.5 giây)
def calculate_traffic_light_times():
    global green_time, red_time, car_count_vid_1, motobike_count_vid_1, car_count_vid_2, motobike_count_vid_2
    car_diff = car_count_vid_1 - car_count_vid_2
    motobike_diff = motobike_count_vid_1 - motobike_count_vid_2
    green_time = min(max(45 + int(car_diff * 1.5 + motobike_diff * 0.5), 20), 90)
    red_time = min(max(45 - int(car_diff * 1.5 + motobike_diff * 0.5), 20), 90)

# Hàm để đếm ngược thời gian đèn giao thông
def traffic_light_countdown():
    global green_time, red_time, is_green, state
    while True:
        if is_green:
            if green_time > 4: # Đèn xanh ở video 1
                if state != 1:
                    state = 1
                    arduino.write(b'G')
                    arduino.write(b'C')
                green_time -= 1
            elif green_time > 0: # Đèn vàng ở video 1
                if state != 2:
                    state = 2
                    arduino.write(b'Y')
                green_time -= 1
            else: # Hết thời gian đèn xanh ở video 1
                is_green = False
                if is_automatic_mode: # Chế độ đèn tự động
                    calculate_traffic_light_times()
                else: # Chế độ đèn mặc định
                    green_time = manual_green_time
                    red_time = manual_red_time
        else:
            if red_time > 4: # Đèn đỏ ở video 1, đèn xanh ở video 2
                if state != 3:
                    state = 3
                    arduino.write(b'R')
                    arduino.write(b'A')
                red_time -= 1
            elif red_time > 0: # Đèn đỏ ở video 1, đèn vàng ở video 2
                if state != 4:
                    state = 4
                    arduino.write(b'B')
                red_time -= 1
            else: # Hết thời gian đèn đỏ ở video 1
                is_green = True
                if is_automatic_mode: # Chế độ đèn tự động
                    calculate_traffic_light_times()
                else: # Chế độ đèn mặc định
                    green_time = manual_green_time
                    red_time = manual_red_time
        time.sleep(1)

def generate_frames():
    cap = cv2.VideoCapture(video_1)

    while True:
        # Đọc từng khung hình từ luồng video
        success, frame = cap.read()

        global car_count_vid_1, motobike_count_vid_1
        car_count_vid_1, motobike_count_vid_1 = get_traffic_density(frame)
        
        cv2.putText(frame, f"car: {car_count_vid_1}, motobike: {motobike_count_vid_1}", (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        
        # Mã hóa khung hình thành JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        # Trả về khung hình dưới dạng luồng MJPEG
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
def generate_frames_2():
    cap = cv2.VideoCapture(video_2)

    while True:
        # Đọc từng khung hình từ luồng video
        success, frame = cap.read()

        global car_count_vid_2, motobike_count_vid_2
        car_count_vid_2, motobike_count_vid_2 = get_traffic_density(frame)

        cv2.putText(frame, f"car: {car_count_vid_2}, motobike: {motobike_count_vid_2}", (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        
        # Mã hóa khung hình thành JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        # Trả về khung hình dưới dạng luồng MJPEG
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    # Trang HTML để hiển thị luồng video
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if user and user['password'] == password:
            session['user_id'] = user['username']
            return redirect(url_for('index2'))
        else:
            return "Invalid credentials", 401
    
    return render_template('login.html')


@app.route('/index2')
def index2():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('index2.html')

@app.route('/video_feed_1')
def video_feed_1():
    # Endpoint cho luồng video 1
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed_2')
def video_feed_2():
    # Endpoint cho luồng video 2
    return Response(generate_frames_2(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/traffic_times')
def traffic_times():
    # Trả về thời gian đèn giao thông hiện tại
    return jsonify({'green_time': green_time, 'red_time': red_time, 'is_green': is_green})

@app.route('/change_mode')
def change_mode():
    # Endpoint cho chuyển đổi chế độ đèn tự động/mặc định
    global is_automatic_mode
    mode = request.args.get('mode')
    if mode == 'manual':
        is_automatic_mode = False
    elif mode == 'automatic':
        is_automatic_mode = True
    return jsonify({'is_automatic_mode': is_automatic_mode})

@app.route('/set_manual_times')
def set_manual_times():
    global manual_green_time, manual_red_time
    manual_green_time = int(request.args.get('green_time', 45))
    manual_red_time = int(request.args.get('red_time', 45))
    return jsonify({'manual_green_time': manual_green_time, 'manual_red_time': manual_red_time})

if __name__ == '__main__':
    # Khởi động luồng đếm ngược đèn giao thông
    threading.Thread(target=traffic_light_countdown, daemon=True).start()
    app.run(threaded=True)