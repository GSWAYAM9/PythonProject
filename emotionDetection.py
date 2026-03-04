import cv2
from fer import FER

# Initialize the emotion detector (using MTCNN for better face accuracy)
detector = FER(mtcnn=True)

# Start video capture from the webcam (0 = default camera)
cap = cv2.VideoCapture(0)

# Optional: Set higher resolution (for better detection)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("🎥 Starting Facial Emotion Detection... (Press 'q' to quit)")

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Camera not detected. Exiting...")
        break

    # Flip frame horizontally for a natural webcam feel
    frame = cv2.flip(frame, 1)

    # Detect emotions
    emotions = detector.detect_emotions(frame)

    # Draw results on frame
    for emotion in emotions:
        (x, y, w, h) = emotion["box"]
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Get the dominant emotion and its score
        emotion_scores = emotion["emotions"]
        dominant_emotion = max(emotion_scores, key=emotion_scores.get)
        confidence = emotion_scores[dominant_emotion]

        # Display emotion and confidence
        label = f"{dominant_emotion} ({confidence*100:.1f}%)"
        cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (0, 255, 0), 2, cv2.LINE_AA)

    # Show the resulting frame
    cv2.imshow('😊 Facial Emotion Detection', frame)

    # Break the loop when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("🛑 Exiting...")
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
print("✅ Facial Emotion Detection Ended Successfully.")
