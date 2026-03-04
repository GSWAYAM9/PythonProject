import cv2
import numpy as np
import time

# Open camera
cap = cv2.VideoCapture(0)
time.sleep(2)  # allow camera to warm up

# Capture the background for 60 frames
background = 0
for i in range(60):
    ret, background = cap.read()
    if not ret:
        continue
    background = cv2.flip(background, 1)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.flip(frame, 1)

    # Convert frame to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Define HSV range for yellow cloak
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([35, 255, 255])

    # Create mask for yellow color
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # Clean the mask
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)

    # Invert mask
    mask_inv = cv2.bitwise_not(mask)

    # Segment cloak part from background
    res1 = cv2.bitwise_and(background, background, mask=mask)
    # Segment non-cloak part from current frame
    res2 = cv2.bitwise_and(frame, frame, mask=mask_inv)

    # Combine both
    final_output = cv2.addWeighted(res1, 1, res2, 1, 0)

    # Display result
    cv2.imshow("Invisibility Cloak - Yellow", final_output)

    # Exit on ESC key
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
