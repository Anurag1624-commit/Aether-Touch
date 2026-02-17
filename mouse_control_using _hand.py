import cv2
import mediapipe
import pyautogui
import math

# Initialize mediapipe
capture_hands = mediapipe.solutions.hands.Hands()
drawing_option = mediapipe.solutions.drawing_utils

# Screen size
screen_width, screen_height = pyautogui.size()

# Camera
camera = cv2.VideoCapture(0)

# Landmark positions
x1 = y1 = x2 = y2 = x3 = y3 = 0

# Click control flags
clicking = False
right_clicking = False

# Cursor smoothing
plocX, plocY = 0, 0
clocX, clocY = 0, 0
smoothening = 6


while True:
    _, image = camera.read()
    image = cv2.flip(image, 1)

    image_height, image_width, _ = image.shape
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    output_hands = capture_hands.process(rgb_image)
    all_hands = output_hands.multi_hand_landmarks

    if all_hands:
        for hand in all_hands:

            drawing_option.draw_landmarks(image, hand)
            one_hand_landmarks = hand.landmark

            for id, lm in enumerate(one_hand_landmarks):

                x = int(lm.x * image_width)
                y = int(lm.y * image_height)

                # INDEX FINGER (Cursor Movement)
                if id == 8:
                    mouse_x = int(screen_width / image_width * x)
                    mouse_y = int(screen_height / image_height * y)

                    # Smoothing
                    clocX = plocX + (mouse_x - plocX) / smoothening
                    clocY = plocY + (mouse_y - plocY) / smoothening

                    pyautogui.moveTo(clocX, clocY)

                    plocX, plocY = clocX, clocY

                    x1, y1 = x, y
                    cv2.circle(image, (x, y), 10, (0, 255, 255), -1)

                # THUMB (Left Click)
                if id == 4:
                    x2, y2 = x, y
                    cv2.circle(image, (x, y), 10, (0, 255, 255), -1)

                # MIDDLE FINGER (Right Click)
                if id == 12:
                    x3, y3 = x, y
                    cv2.circle(image, (x,y), 10, (255, 0 , 255), -1)
                dist = math.hypot(x2 - x1, y2 - y1)

        if dist < 30:
            if not clicking:
                pyautogui.click()
                clicking = True
        else:
            clicking = False

        # Visual line for left click
        cv2.line(image, (x1, y1), (x2, y2), (0, 255, 0), 3)

        # ---------------- RIGHT CLICK ----------------
        dist2 = math.hypot(x3 - x1, y3 - y1)

        if dist2 < 30:
            if not right_clicking:
                pyautogui.rightClick()
                right_clicking = True
        else:
            right_clicking = False

    cv2.imshow("Hand movement video capture", image)

    if cv2.waitKey(1) == 27:
        break

camera.release()
cv2.destroyAllWindows()
