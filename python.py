import cv2
import numpy as np
import pyautogui
import keyboard
import random
from mss import mss
from time import sleep, time
import time
import logging
import sys
import os

# Import the camouflage module
from kernel_camouflage import KernelCamouflage, add_kernel_camouflage, implement_kernel_camouflage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration settings
class Config:
    # Target color settings
    TARGET_COLOR = (128, 0, 128)  # Purple in RGB (enemies in Valorant)
    COLOR_SENSITIVITY = 70
    
    # Aimbot settings
    LOCK_POWER = 25  # Base for aimbot, dynamically adjusted
    SCAN_AREA_X = 15
    SCAN_AREA_Y = 15
    
    # Control keys
    ACTIVATE_KEY = 'p'
    RECOIL_KEY = 'o'
    WEAPON_SWITCH_KEY = 'u'
    
    # Recoil patterns adjusted for Vandal and Phantom (based on real descriptions)
    RECOIL_PATTERNS = {
        'vandal': [  # Inverted "T" pattern
            (0, 0), (0, 2), (0, 4), (0, 6), (0, 8), 
            (0, 10), (0, 12), (0, 14), (-1, 15), (1, 16), 
            (-1, 17), (1, 18), (-2, 19), (2, 20), (-2, 21)
        ],
        'phantom': [  # Mirrored "7" pattern
            (0, 0), (0, 1), (0, 2), (0, 3), (0, 4), 
            (0, 5), (0, 6), (0, 7), (0, 8), (-1, 9), 
            (1, 10), (-1, 11), (2, 12), (-2, 13), (1, 14)
        ]
    }


class AimbotController:
    def __init__(self):
        # Bot state
        self.active = False
        self.recoil_active = False
        self.current_weapon = 'vandal'
        self.firing = False
        self.last_shot_time = 0
        self.human_like_movements = True
        
        # Convert target color to HSV (BGR)
        target_bgr = np.uint8([[Config.TARGET_COLOR[::-1]]])  # Convert RGB to BGR
        target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)[0][0]

        # Main color limits
        self.lower = np.array([
            max(0, target_hsv[0] - Config.COLOR_SENSITIVITY),
            max(0, target_hsv[1] - Config.COLOR_SENSITIVITY),
            max(0, target_hsv[2] - Config.COLOR_SENSITIVITY)
        ])
        self.upper = np.array([
            min(179, target_hsv[0] + Config.COLOR_SENSITIVITY),
            min(255, target_hsv[1] + Config.COLOR_SENSITIVITY),
            min(255, target_hsv[2] + Config.COLOR_SENSITIVITY)
        ])

        # Second color range for purple variations
        self.lower2 = np.array([110, 50, 50])  # Darker tones
        self.upper2 = np.array([150, 255, 255])  # Lighter tones
        
        # Lock power (will be dynamically adjusted)
        self.lock_power = Config.LOCK_POWER
        
        logger.info("AimbotController initialized")

    def apply_recoil_control(self):
        if not self.firing and keyboard.is_pressed('mouse left'):
            self.firing = True
            self.last_shot_time = time()
            logger.info(f"Recoil control activated for {self.current_weapon}")
        elif self.firing and not keyboard.is_pressed('mouse left'):
            self.firing = False
            return
        
        if self.firing:
            current_time = time()
            shot_duration = current_time - self.last_shot_time
            pattern = Config.RECOIL_PATTERNS[self.current_weapon]
            
            # Adjust index based on 0.1s per step
            pattern_index = min(int(shot_duration / 0.1), len(pattern) - 1)
            x, y = pattern[pattern_index]
            
            # Add human variation
            if self.human_like_movements:
                x += random.uniform(-0.5, 0.5)
                y += random.uniform(-0.5, 0.5)
            
            # Apply anti-recoil movement
            pyautogui.move(-x, -y, _pause=False)

    def aggressive_aimbot(self, img_bgr, hsv):
        # Masks for multiple color ranges
        mask1 = cv2.inRange(hsv, self.lower, self.upper)
        mask2 = cv2.inRange(hsv, self.lower2, self.upper2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # Morphological operations with larger kernel
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        mask = cv2.erode(mask, kernel, iterations=1)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Find largest contour
            largest = max(contours, key=cv2.contourArea)
            M = cv2.moments(largest)

            if M["m00"] != 0:
                # Calculate contour center
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                
                # Adjust to aim for the head
                head_offset = -5
                cY += head_offset
                
                # Calculate distance to target
                distance_to_target = abs(cX - Config.SCAN_AREA_X) + abs(cY - Config.SCAN_AREA_Y)
                
                # Adjust lock_power based on distance
                adjusted_lock = 10 if distance_to_target > 50 else 25
                
                # Calculate movement with dynamic adjustment
                rel_x = (cX - Config.SCAN_AREA_X) * (adjusted_lock + 10) / 100
                rel_y = (cY - Config.SCAN_AREA_Y) * (adjusted_lock + 10) / 100
                
                # Add human movement
                if self.human_like_movements:
                    rel_x += random.uniform(-0.5, 0.5)
                    rel_y += random.uniform(-0.5, 0.5)
                
                # Add random delay to simulate human reaction
                sleep(random.uniform(0.05, 0.2))
                
                # Move mouse with smoothing
                pyautogui.move(rel_x, rel_y, _pause=False)
                
                # Auto-fire if very close
                if distance_to_target < 5 and keyboard.is_pressed(Config.ACTIVATE_KEY):
                    pyautogui.click(_pause=False)

    def run(self):
        logger.info("""
        Valorant Advanced Aimbot
        -----------------------
        Keys:
        P - Activate/Deactivate Aimbot
        O - Activate/Deactivate Recoil Control
        U - Switch between Vandal/Phantom
        """)
        
        with mss() as sct:
            while True:
                # Controls
                if keyboard.is_pressed(Config.ACTIVATE_KEY):
                    self.active = not self.active
                    logger.info(f"Aimbot {'activated' if self.active else 'deactivated'}")
                    sleep(0.3)
                    
                if keyboard.is_pressed(Config.RECOIL_KEY):
                    self.recoil_active = not self.recoil_active
                    logger.info(f"Recoil control {'activated' if self.recoil_active else 'deactivated'}")
                    sleep(0.3)
                    
                if keyboard.is_pressed(Config.WEAPON_SWITCH_KEY):
                    self.current_weapon = 'phantom' if self.current_weapon == 'vandal' else 'vandal'
                    logger.info(f"Weapon changed to: {self.current_weapon}")
                    sleep(0.3)

                # Apply recoil control if active
                if self.recoil_active:
                    self.apply_recoil_control()

                # Aimbot
                if not self.active:
                    sleep(0.01)
                    continue

                # Get mouse position
                x, y = pyautogui.position()

                # Define capture area
                monitor = {
                    "left": x - Config.SCAN_AREA_X,
                    "top": y - Config.SCAN_AREA_Y,
                    "width": Config.SCAN_AREA_X * 2 + 1,
                    "height": Config.SCAN_AREA_Y * 2 + 1
                }

                # Capture screen
                img = np.array(sct.grab(monitor))
                img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

                # Aggressive aimbot
                self.aggressive_aimbot(img_bgr, hsv)

                # Performance adjustment
                sleep(0.01)  # Reduced from 0.005 to balance CPU and response


# Apply kernel camouflage to the AimbotController
AimbotController = add_kernel_camouflage(AimbotController)

def main():
    logger.info("Starting Valorant Advanced Aimbot with Kernel Camouflage protection")
    
    try:
        # Create and run the aimbot controller
        # The kernel camouflage will be automatically started and stopped
        # by the decorated AimbotController
        aimbot = AimbotController()
        aimbot.run()
    except Exception as e:
        logger.error(f"Error in main program: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Program terminated")


if __name__ == "__main__":
    main()