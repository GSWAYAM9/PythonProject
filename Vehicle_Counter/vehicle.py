import cv2
import numpy as np
from collections import OrderedDict
import time

# ----------------------------
# Simple CentroidTracker class
# ----------------------------
class CentroidTracker:
    def __init__(self, max_disappeared=50, max_distance=50):
        # next object ID to assign
        self.next_object_id = 0
        # object_id -> centroid (x, y)
        self.objects = OrderedDict()
        # object_id -> number of consecutive frames it has disappeared
        self.disappeared = OrderedDict()
        # optional store of last centroid to detect direction
        self.previous_centroids = OrderedDict()
        # parameters
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def register(self, centroid):
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.previous_centroids[self.next_object_id] = centroid
        self.next_object_id += 1

    def deregister(self, object_id):
        del self.objects[object_id]
        del self.disappeared[object_id]
        del self.previous_centroids[object_id]

    def update(self, rects):
        """
        rects: list of bounding boxes [x, y, w, h]
        returns: OrderedDict of object_id -> centroid
        """
        # if no detections, mark disappeared
        if len(rects) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects

        # compute centroids for input rects
        input_centroids = np.zeros((len(rects), 2), dtype="int")
        for (i, (x, y, w, h)) in enumerate(rects):
            cX = int(x + w / 2.0)
            cY = int(y + h / 2.0)
            input_centroids[i] = (cX, cY)

        # if no existing objects, register all input centroids
        if len(self.objects) == 0:
            for i in range(0, len(input_centroids)):
                self.register(tuple(input_centroids[i]))
        else:
            # build arrays of current object IDs and centroids
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            # compute distance matrix between object_centroids and input_centroids
            D = np.linalg.norm(np.array(object_centroids)[:, np.newaxis] - input_centroids[np.newaxis, :], axis=2)

            # for each existing object, find closest input centroid (and vice versa)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows = set()
            used_cols = set()

            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                if D[row, col] > self.max_distance:
                    continue

                object_id = object_ids[row]
                self.objects[object_id] = tuple(input_centroids[col])
                self.previous_centroids[object_id] = tuple(object_centroids[row])  # store previous
                self.disappeared[object_id] = 0

                used_rows.add(row)
                used_cols.add(col)

            # compute unused rows and cols
            unused_rows = set(range(0, D.shape[0])).difference(used_rows)
            unused_cols = set(range(0, D.shape[1])).difference(used_cols)

            # objects with no matched centroid => disappeared
            for row in unused_rows:
                object_id = object_ids[row]
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)

            # new input centroids => register
            for col in unused_cols:
                self.register(tuple(input_centroids[col]))

        return self.objects

# ----------------------------
# Main detection & counting
# ----------------------------

def main():
    # -------------------
    # Configuration
    # -------------------
    WEIGHTS = "yolov3.weights"
    CFG = "yolov3.cfg"
    NAMES = "coco.names"
    VIDEO_PATH = "video.mp4"
    OUTPUT_PATH = "output.avi"  # set to None to disable saving
    CONF_THRESH = 0.5
    NMS_THRESH = 0.4
    SKIP_FRAMES = 1  # run detection every SKIP_FRAMES frames (1 = every frame)
    VEHICLE_CLASSES = {"car", "bus", "truck", "motorbike"}
    COUNT_LINE_Y = 350  # set based on your video
    DIRECTION = "down"  # count vehicles moving 'down' (increasing y); can also adapt to 'up'

    # -------------------
    # Load YOLO
    # -------------------
    net = cv2.dnn.readNet(WEIGHTS, CFG)
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers().flatten()]
    with open(NAMES, "r") as f:
        classes = [c.strip() for c in f.readlines()]

    # -------------------
    # Initialize
    # -------------------
    cap = cv2.VideoCapture(VIDEO_PATH)
    writer = None
    fps = cap.get(cv2.CAP_PROP_FPS) if cap.get(cv2.CAP_PROP_FPS) > 0 else 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if OUTPUT_PATH is not None:
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))

    tracker = CentroidTracker(max_disappeared=40, max_distance=80)
    counted_ids = set()
    total_count = 0
    frame_count = 0

    start = time.time()
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        rgb = frame  # we use BGR frames directly for dnn

        rects = []  # bounding boxes for this frame

        # Run detection every SKIP_FRAMES frames
        if frame_count % SKIP_FRAMES == 0:
            blob = cv2.dnn.blobFromImage(rgb, 1/255.0, (416, 416), swapRB=True, crop=False)
            net.setInput(blob)
            outs = net.forward(output_layers)

            boxes = []
            confidences = []
            class_ids = []

            for out in outs:
                for detection in out:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    if confidence > CONF_THRESH and classes[class_id] in VEHICLE_CLASSES:
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)
                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)
                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)

            # NMS
            idxs = cv2.dnn.NMSBoxes(boxes, confidences, CONF_THRESH, NMS_THRESH)
            if len(idxs) > 0:
                for i in idxs.flatten():
                    rects.append(boxes[i])

        # Update tracker with bounding boxes (if empty, will update disappearance)
        objects = tracker.update(rects)

        # Draw counting line
        cv2.line(frame, (0, COUNT_LINE_Y), (width, COUNT_LINE_Y), (255, 0, 0), 2)

        # Loop over tracked objects
        for (object_id, centroid) in objects.items():
            cX, cY = centroid
            prev = tracker.previous_centroids.get(object_id, None)

            # Draw ID and centroid
            text = f"ID {object_id}"
            cv2.putText(frame, text, (cX - 10, cY - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.circle(frame, (cX, cY), 4, (0, 255, 0), -1)

            # If we have a previous centroid, check crossing
            if prev is not None and object_id not in counted_ids:
                prev_y = prev[1]
                cur_y = cY

                # crossing downward
                if DIRECTION == "down" and prev_y < COUNT_LINE_Y <= cur_y:
                    total_count += 1
                    counted_ids.add(object_id)
                # crossing upward (if you want)
                elif DIRECTION == "up" and prev_y > COUNT_LINE_Y >= cur_y:
                    total_count += 1
                    counted_ids.add(object_id)

        # Display count
        cv2.putText(frame, f"Count: {total_count}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

        # Write output frame
        if writer is not None:
            writer.write(frame)

        cv2.imshow("Vehicle Counter", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break

    elapsed = time.time() - start
    print(f"[INFO] Elapsed: {elapsed:.2f}s, Frames: {frame_count}, FPS: {frame_count/elapsed:.2f}")
    cap.release()
    if writer is not None:
        writer.release()
        print(f"[INFO] Output saved to {OUTPUT_PATH}")
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
