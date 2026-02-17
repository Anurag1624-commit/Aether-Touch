# Aether-Touch 🖐️🔊
Real-Time Gesture-Controlled Interface

Aether-Touch is a computer vision-based application that allows users to control their system volume using hand gestures. By leveraging MediaPipe's neural networks for hand landmark detection and OpenCV for real-time video processing, it transforms "thin air" into a functional, touchless controller.

# Features
1. Precision Tracking: Utilizes 21 3D hand landmarks for high-accuracy gesture recognition.
2. Dynamic Volume Scaling: Maps the Euclidean distance between the thumb and index finger to the system's volume range.
3. Visual Feedback: Real-time HUD (Heads-Up Display) showing a volume bar and landmark overlays on the camera feed.
4. Zero-Touch Interaction: Designed for hygiene and convenience in "lean-back" computing environments.

 # Tech Stack
Language: Python 3.x
Computer Vision: OpenCV
Inference Engine: MediaPipe (Hand Landmarker API)
Math: NumPy (for linear interpolation and distance calculations)

# How It Works

The system follows a three-step pipeline to translate physical movement into digital commands:
1. Capture: OpenCV grabs frames from the webcam.
2. Detection: MediaPipe identifies the coordinates of the Thumb Tip (ID 4) and Index Tip (ID 8).
3. Mapping: The distance between these two points is calculated. If the distance is small (pinch), the volume decreases; if large, it increases.

# Installation & Usage: 
Follow the below steps.

# Clone the repository:
git clone https://github.com/Anurag1624/Aether-Touch.git
cd Aether-Touch

# Install dependencies:
pip install opencv-python mediapipe numpy pycaw

# Run the application:
python main.py
# File: 
[mouse_control_using _hand.py](https://github.com/user-attachments/files/25368203/mouse_control_using._hand.py)

