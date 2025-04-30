import cv2
from cvzone.HandTrackingModule import HandDetector
import pyautogui
import time


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

        # Mapping factor (adjust to make the mapping larger)
        self.mapping_factor = 4.0  # Example: 2.0 means map hand movement to twice the screen size

        # Flag to track if left mouse button is held
        self.left_click_held = False

        # Debug visualization
        self.debug_mode = True

        # Wrist landmark index
        self.wrist_landmark = 0

    def process_frame(self, frame):
        frame_height, frame_width = frame.shape[:2]
        self.frame_height, self.frame_width = frame_height, frame_width

        # Find hands in frame
        hands, frame = self.detector.findHands(frame, draw=False)

        if hands:
            hand = hands[0]  # Assuming only one hand
            lm_list = hand["lmList"]  # List of landmark coordinates
            fingers = self.detector.fingersUp(hand)

            # Check if wrist landmark is detected
            if lm_list and len(lm_list) > self.wrist_landmark:
                wrist_x, wrist_y = lm_list[self.wrist_landmark][0], lm_list[self.wrist_landmark][1]

                # Map hand coordinates to a larger virtual screen
                virtual_screen_width = self.frame_width * self.mapping_factor
                virtual_screen_height = self.frame_height * self.mapping_factor

                mapped_x = (wrist_x / self.frame_width) * virtual_screen_width - (virtual_screen_width - self.screen_width) / 2
                mapped_y = (wrist_y / self.frame_height) * virtual_screen_height - (virtual_screen_height - self.screen_height) / 2 - 300

                # Clamp the mapped coordinates to the actual screen boundaries
                screen_x = int(max(0, min(mapped_x, self.screen_width - 1)))
                screen_y = int(max(0, min(mapped_y, self.screen_height - 1)))

                # Move the mouse cursor
                pyautogui.moveTo(screen_x, screen_y)

                # Determine mouse click state based on finger state (index)
                if not fingers[1]:  # Index finger is closed
                    if not self.left_click_held:
                        pyautogui.mouseDown()
                        self.left_click_held = True
                else:  # Index finger is open
                    if self.left_click_held:
                        pyautogui.mouseUp()
                        self.left_click_held = False

                # Debug visualization: Draw a circle on the wrist
                if self.debug_mode:
                    cv2.circle(frame, (wrist_x, wrist_y), 10, (255, 165, 0), cv2.FILLED)  # Orange color
                    cv2.circle(frame, (lm_list[8][0], lm_list[8][1]), 5, (255, 0, 255), cv2.FILLED) # Show index finger tip

        else:
            # If no hand is detected, release the mouse button
            if self.left_click_held:
                pyautogui.mouseUp()
                self.left_click_held = False

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
        print("Hand Wrist Cursor Control - Expanded Mapping - Started")
        print("Move your wrist to control the cursor (expanded range).")
        print("Close your index finger to hold left click.")
        print("Open your index finger to release left click.")
        print("Press 'q' to quit")

        try:
            self.run_loop()
        finally:
            self.cleanup()

    def run_loop(self):
        """Main processing loop."""
        WIN_NAME = 'Hand Wrist Cursor Control - Expanded Mapping'

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
        print("Hand Wrist Cursor Control - Expanded Mapping - Stopped")


if __name__ == "__main__":
    app = CursorControlApp()
    app.start()