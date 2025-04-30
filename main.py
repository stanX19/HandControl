import math
import cv2
from cvzone.HandTrackingModule import HandDetector
import pyautogui
import time


class HandGestureTracker:
    def __init__(self):
        # Initialize HandDetector from cvzone
        self.detector = HandDetector(staticMode=False, maxHands=2, minTrackCon=0.5)

        # Parameters for gesture detection
        self.swipe_speed_threshold = 400  # swipe speed
        self.swipe_time_window = 0.5  # Time window in seconds for swipe detection
        self.cooldown_time = 1.5  # Time in seconds before another gesture

        # State tracking variables
        self.last_gesture_time = 0

        # Hand position history
        self.hand_history = []  # List of (timestamp, position, is_active) tuples

        # Screen dimensions
        screen = pyautogui.size()
        self.screen_width = screen[0]
        self.screen_height = screen[1]

        # Prevent pyautogui from raising exceptions
        pyautogui.FAILSAFE = False

        # Debug visualization
        self.debug_mode = True

    @staticmethod
    def is_hand_active(fingers):
        """Check if the hand is generally active (at least 2 fingers up)."""
        return 1 <= sum(fingers) <= 5
        # return (fingers == [0, 1, 1, 0, 0]
        #     or fingers == [1, 0, 0, 1, 1]
        #     or fingers == [1, 0, 0, 0, 0])

    def process_frame(self, frame):
        current_time = time.time()
        frame_height, frame_width = frame.shape[:2]

        # Find hands in frame
        hands, frame = self.detector.findHands(frame)

        # Debug info
        detected_swipe = None
        hand_status = "No Hand"

        # Process hand if detected
        for hand in hands:
            if hand["type"] == "Right":  # its actually left
                continue
            fingers = self.detector.fingersUp(hand)
            index_tip = hand["lmList"][8]
            center = hand["center"]
            is_active = self.is_hand_active(fingers)

            hand_status = "active" if is_active else "Closed"

            # Add to hand history
            self.hand_history.append((current_time, index_tip, is_active))

            # Clean up old history entries
            self.clean_history(current_time)

            # Detect swipe based on hand history
            detected_swipe = self.detect_swipe(current_time)
            break
        else:
            # No hand present, still clean history
            self.clean_history(current_time)

        # Add status text to frame
        cv2.putText(frame, f"Hand: {hand_status}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        if detected_swipe:
            cv2.putText(frame, f"{detected_swipe.upper()} SWIPE", (50, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Draw hand history visualization
        if self.debug_mode:
            self.visualize_hand_history(frame)

        return frame, detected_swipe

    def clean_history(self, current_time):
        """Remove hand history entries older than the time window."""
        cutoff_time = current_time - self.swipe_time_window
        self.hand_history = [entry for entry in self.hand_history if entry[0] >= cutoff_time]

    def detect_swipe(self, current_time):
        """
        Detect swipes by analyzing hand position history.
        A swipe is defined as active hand positions changing significantly
        within the time window, allowing closed/missing hands in between.
        """
        # If in cooldown period, no new gestures
        if current_time - self.last_gesture_time < self.cooldown_time:
            return None

        # Find active hand positions in history
        active_hand_entries = [entry for entry in self.hand_history if entry[2]]  # entry[2] is is_active

        if len(active_hand_entries) < 2:
            # Need at least 2 active hands to detect a swipe
            return None

        def get_speed(a:tuple[int, tuple[int, int]], b:tuple[int, tuple[int, int]]):
            _time = abs(a[0] - b[0])
            if _time <= 0.1:
                return 0
            return math.hypot(a[1][0] - b[1][0], a[1][1] - b[1][1]) / _time

        # # Sort by timestamp (newest to oldest)
        # active_hand_entries.sort(key=lambda entry: entry[0], reverse=True)
        # # Get most recent and earliest active hand positions within time window
        # oldest_entry = active_hand_entries[-1]
        # fastest_entry = active_hand_entries[0]

        oldest_entry = min(active_hand_entries, key=lambda entry: entry[0])
        fastest_entry = max(active_hand_entries, key=lambda entry: get_speed(oldest_entry, entry))

        # Check if we have enough time difference between them
        time_diff = fastest_entry[0] - oldest_entry[0]
        if time_diff < 0.1:
            return None

        # Calculate distance between oldest and newest active hand positions
        start_pos = oldest_entry[1]  # position of earliest active hand
        end_pos = fastest_entry[1]  # position of most recent active hand

        delta_x = end_pos[0] - start_pos[0]
        delta_y = end_pos[1] - start_pos[1]

        # Calculate threshold based on frame dimensions
        threshold_delta = self.swipe_speed_threshold * time_diff

        # Determine swipe direction based on the larger movement component
        swipe_direction = None
        distance = math.hypot(delta_x, delta_y)
        print(f"{distance:10.2f} {threshold_delta:10.2f}")
        if abs(delta_x) > abs(delta_y) / 2:
            if delta_x > threshold_delta:
                swipe_direction = "right"
            elif delta_x < -threshold_delta:
                swipe_direction = "left"
        else:
            if delta_y < -threshold_delta:  # Moving up (y decreases)
                swipe_direction = "up"
            elif delta_y > threshold_delta:  # Moving down (y increases)
                swipe_direction = "down"

        # If swipe detected, set cooldown
        if swipe_direction:
            self.last_gesture_time = current_time

            # Clear history after a successful swipe
            self.hand_history = []

        return swipe_direction

    def visualize_hand_history(self, frame):
        """Draw the hand history positions on the frame for debugging."""
        # Draw paths for active and closed hands
        for i in range(1, len(self.hand_history)):
            prev_pos = self.hand_history[i - 1][1]  # Previous position
            curr_pos = self.hand_history[i][1]  # Current position
            is_active = self.hand_history[i][2]  # Is hand active

            if prev_pos and curr_pos:
                # Draw line with color based on hand state (green=active, red=closed)
                color = (0, 255, 0) if is_active else (0, 0, 255)
                cv2.line(frame,
                         (int(prev_pos[0]), int(prev_pos[1])),
                         (int(curr_pos[0]), int(curr_pos[1])),
                         color, 2)

        # Draw points for active hands
        for entry in self.hand_history:
            timestamp, pos, is_active = entry
            if is_active and pos:
                cv2.circle(frame, (int(pos[0]), int(pos[1])), 5, (0, 255, 0), -1)


class HandSwipeControlApp:
    def __init__(self):
        # Initialize webcam
        self.cap = cv2.VideoCapture(0)
        self.gesture_tracker = HandGestureTracker()
        self.running = False

    def start(self):
        """Start the hand swipe control application."""
        self.running = True
        print("Hand Swipe Control - Started")
        print("Swipe left: Press RIGHT arrow key")
        print("Swipe right: Press LEFT arrow key")
        print("Swipe up: Press DOWN arrow key")
        print("Swipe down: Press UP arrow key")
        print("A swipe is detected when an active hand moves significantly within 1 second")
        print("Hand can close or disappear between active positions")
        print("Press 'q' to quit")

        try:
            self.run_loop()
        finally:
            self.cleanup()

    def run_loop(self):
        """Main processing loop."""
        WIN_NAME = 'Hand Swipe Control'

        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to grab frame")
                break

            # Flip frame horizontally for a mirror effect
            frame = cv2.flip(frame, 1)

            # Process the current frame
            frame, swipe_direction = self.gesture_tracker.process_frame(frame)

            # Execute action based on detected swipe
            if swipe_direction:
                self.execute_swipe_action(swipe_direction)

            # Display the frame
            cv2.imshow(WIN_NAME, frame)

            # Check for quit command
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
            if cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_VISIBLE) < 1:
                self.running = False

    def execute_swipe_action(self, direction):
        """Execute action based on detected swipe direction."""
        if direction == "left":
            pyautogui.press('right')
            print('Executed: LEFT swipe')
        elif direction == "right":
            pyautogui.press('left')
            print('Executed: RIGHT swipe')
        elif direction == "up":
            pyautogui.press('down')
            print('Executed: UP swipe')
        elif direction == "down":
            pyautogui.press('up')
            print('Executed: DOWN swipe')

    def cleanup(self):
        """Release resources when application exits."""
        self.cap.release()
        cv2.destroyAllWindows()
        print("Hand Swipe Control - Stopped")


if __name__ == "__main__":
    app = HandSwipeControlApp()
    app.start()