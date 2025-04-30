import cv2
from cvzone.HandTrackingModule import HandDetector
import pyautogui
import time

class ClickStatus:
    UP = 0
    PENDING = 1
    DOWN = 2

class ClickHandler:
    def __init__(self, button: str, threshold=0.5):
        """

        :param button: ["left", "right"]
        """
        self._threshold = threshold
        self._button = button
        self._prev_time = None
        self._status = ClickStatus.UP

    def update(self, finger_down: bool):
        if self._status == ClickStatus.UP:
            if finger_down:
                self._prev_time = time.time()
                self._status = ClickStatus.PENDING

        elif self._status == ClickStatus.PENDING:
            if time.time() < self._prev_time + self._threshold:
                return
            if finger_down:
                pyautogui.mouseDown(button=self._button)
                self._status = ClickStatus.DOWN
            else:
                pyautogui.mouseDown(button=self._button)
                pyautogui.mouseUp(button=self._button)
                self._status = ClickStatus.UP

        elif self._status == ClickStatus.DOWN:
            if not finger_down:
                pyautogui.mouseUp(button=self._button)
                self._status = ClickStatus.UP

class HandCursorControl:
    def __init__(self):
        # Initialize HandDetector from cvzone
        self.detector = HandDetector(staticMode=False, maxHands=1, minTrackCon=0.5, detectionCon=0.8)

        # Screen dimensions
        screen = pyautogui.size()
        self.screen_width = screen[0]
        self.screen_height = screen[1]

        # Camera frame dimensions (will be updated on first frame)
        self.frame_width = 640
        self.frame_height = 480

        # Mapping factor
        self.mapping_factor = 4.0

        # Flags to track mouse button states
        self.left_handler = ClickHandler("left")
        self.right_handler = ClickHandler("right")

        # Debug visualization
        self.debug_mode = True

        # Wrist landmark index.
        self.wrist_landmark = 0

    def process_hand(self, hand, frame):
        lm_list = hand["lmList"]  # List of landmark coordinates
        fingers = self.detector.fingersUp(hand)  # Get finger states

        # Check if wrist landmark is detected
        if lm_list and len(lm_list) < self.wrist_landmark:
            return

        wrist_x, wrist_y = lm_list[self.wrist_landmark][0], lm_list[self.wrist_landmark][1]

        # Map hand coordinates to a larger virtual screen
        virtual_screen_width = self.frame_width * self.mapping_factor
        virtual_screen_height = self.frame_height * self.mapping_factor

        mapped_x = (wrist_x / self.frame_width) * virtual_screen_width - (
                    virtual_screen_width - self.screen_width) / 2
        mapped_y = (wrist_y / self.frame_height) * virtual_screen_height - (
                    virtual_screen_height - self.screen_height) / 2 - 300

        # Clamp the mapped coordinates to the actual screen boundaries
        screen_x = int(max(0, min(mapped_x, self.screen_width - 1)))
        screen_y = int(max(0, min(mapped_y, self.screen_height - 1)))

        # Move the mouse cursor
        pyautogui.moveTo(screen_x, screen_y)

        # Handle mouse clicks based on finger states
        index_finger_closed = not fingers[1]
        middle_finger_closed = not fingers[2]

        self.left_handler.update(index_finger_closed)
        self.right_handler.update(middle_finger_closed)

        # Debug visualization: Draw circles on the wrist and finger tips
        if self.debug_mode:
            cv2.circle(frame, (wrist_x, wrist_y), 10, (255, 165, 0), cv2.FILLED)  # Orange for wrist
            if lm_list and len(lm_list) > 8:
                cv2.circle(frame, (lm_list[8][0], lm_list[8][1]), 5, (255, 0, 255),
                           cv2.FILLED)  # Magenta for index finger tip
            if lm_list and len(lm_list) > 12:
                cv2.circle(frame, (lm_list[12][0], lm_list[12][1]), 5, (0, 255, 255),
                           cv2.FILLED)  # Yellow for middle finger tip

    def process_frame(self, frame):
        frame_height, frame_width = frame.shape[:2]
        self.frame_height, self.frame_width = frame_height, frame_width

        # Find hands in frame
        hands, frame = self.detector.findHands(frame, draw=False)

        if hands:
            self.process_hand(hands[0], frame)
        else:
            self.left_handler.update(False)
            self.left_handler.update(False)

        return frame


class CursorControlApp:
    def __init__(self):
        # Initialize webcam
        self.cap = cv2.VideoCapture(0)
        self.cursor_control = HandCursorControl()
        self.running = False

    def start(self):
        """Start the hand cursor control application."""
        self.running = True
        print("Hand Wrist Cursor Control - v2 - Started")
        print("Move your wrist to control the cursor (expanded range).")
        print("Close your index finger to hold left click.")
        print("Close your middle finger to hold right click.")
        print("Close both index and middle fingers to left click and release.")
        print("Open fingers to release clicks.")
        print("Press 'q' to quit")

        try:
            self.run_loop()
        finally:
            self.cleanup()

    def run_loop(self):
        """Main processing loop."""
        WIN_NAME = 'Hand Wrist Cursor Control - v3'
        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to grab frame")
                break

            # Flip frame horizontally for a mirror effect
            frame = cv2.flip(frame, 1)

            # Process the current frame
            frame = self.cursor_control.process_frame(frame)

            # Display the frame
            cv2.imshow(WIN_NAME, frame)

            # Check for quit command
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
            if cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_VISIBLE) < 1:
                self.running = False

    def cleanup(self):
        """Release resources when application exits."""
        self.cap.release()
        cv2.destroyAllWindows()
        print("Hand Wrist Cursor Control - v3 - Stopped")



if __name__ == "__main__":
    pyautogui.FAILSAFE = False
    app = CursorControlApp()
    app.start()
