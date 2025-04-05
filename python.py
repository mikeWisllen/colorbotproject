import cv2
import numpy as np
import pyautogui
import keyboard
import random
from mss import mss
import time  # Importa o módulo completo
from time import sleep  # Mantém sleep direto
import logging
import sys
import os
import mouse

pyautogui.FAILSAFE = False  # Adicionar com aviso de segurança

# Import the camouflage module
from kernel_camouflage import KernelCamouflage, add_kernel_camouflage, implement_kernel_camouflage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration settings
class Config:
    # Target color settings
    TARGET_COLOR = (128, 0, 128)  # Purple in RGB (enemies in Valorant)
    COLOR_SENSITIVITY = 90
    
    # Aimbot settings
    LOCK_POWER = 45  # Base for aimbot, dynamically adjusted
    SCAN_AREA_X = 30
    SCAN_AREA_Y = 30
    
    # Control keys
    ACTIVATE_KEY = 'p'
    RECOIL_KEY = 'o'
    WEAPON_SWITCH_KEY = 'u'
    
    # Recoil patterns adjusted for Vandal and Phantom (based on real descriptions)
    RECOIL_PATTERNS = {
        'vandal': [
            # Fase inicial - subida vertical leve
            (0, -1), (0, -2), (0, -3), (0, -4), (0, -5),
            # Fase média - subida vertical forte com leve desvio
            (0, -6), (0, -7), (0, -8), (0, -9), (0, -10),
            # Fase de spray - padrão em T invertido
            (-1, -10), (1, -9), (-1, -8), (1, -7), (-2, -7),
            (2, -6), (-2, -6), (2, -5), (-3, -5), (3, -4),
            # Continuação do spray - oscilação horizontal mais forte
            (-4, -3), (4, -3), (-5, -3), (5, -2), (-4, -2),
            (4, -1), (-3, -1), (3, -1), (-2, -1), (2, -1),
            # Fase final do spray - estabilização com micro-ajustes
            (-1, -0.5), (1, -0.5), (-0.5, -0.5), (0.5, -0.5), (0, -0.5)
        ],
        'phantom': [
            # Fase inicial - recuo mais suave que o Vandal
            (0, -0.5), (0, -1), (0, -1.5), (0, -2), (0, -2.5),
            # Fase média - padrão mais controlado
            (0, -3), (0, -3.5), (0, -4), (0, -4.5), (0, -5),
            # Fase de spray - padrão em 7 espelhado
            (-0.5, -5), (0.5, -5), (-1, -5), (1, -4.5), (-1.5, -4.5),
            (1.5, -4), (-2, -4), (2, -3.5), (-2, -3), (2, -3),
            # Continuação do spray - oscilação mais previsível
            (-2, -2.5), (2, -2.5), (-1.5, -2), (1.5, -2), (-1, -1.5),
            (1, -1.5), (-0.5, -1), (0.5, -1), (-0.5, -0.5), (0.5, -0.5),
            # Fase final do spray - estabilização suave
            (-0.3, -0.3), (0.3, -0.3), (-0.2, -0.2), (0.2, -0.2), (0, -0.1)
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
        self.last_target_position = None  # Armazena a última posição do alvo
        self.target_prediction = [0, 0]  # Predição de movimento do alvo
        
        # Convert target color to HSV (BGR)
        target_bgr = np.uint8([[Config.TARGET_COLOR[::-1]]])  # Convert RGB to BGR
        target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)[0][0]

        # Main color limits - add dtype=np.uint8
        self.lower = np.clip([
            max(0, target_hsv[0] - Config.COLOR_SENSITIVITY),
            max(0, target_hsv[1] - Config.COLOR_SENSITIVITY),
            max(0, target_hsv[2] - Config.COLOR_SENSITIVITY)
        ], 0, 255).astype(np.uint8)  # Add this dtype parameter

        self.upper = np.clip([
            min(179, target_hsv[0] + Config.COLOR_SENSITIVITY),
            min(255, target_hsv[1] + Config.COLOR_SENSITIVITY),
            min(255, target_hsv[2] + Config.COLOR_SENSITIVITY)
        ], 0, 255).astype(np.uint8)  # Add this dtype parameter

        # Second color range for purple variations - Expandindo a faixa de detecção
        self.lower2 = np.array([100, 40, 40])  # Expandido de [110, 50, 50]
        self.upper2 = np.array([160, 255, 255])  # Expandido de [150, 255, 255]
        
        # Adicionando terceira faixa para detecção mais agressiva
        self.lower3 = np.array([120, 30, 30])
        self.upper3 = np.array([140, 255, 255])
        
        # Lock power (will be dynamically adjusted)
        self.lock_power = Config.LOCK_POWER
        
        logger.info("AimbotController initialized")

    def apply_recoil_control(self):
        if not self.firing and mouse.is_pressed('left'):  # 'mouse left' -> 'left'
            self.firing = True
            self.last_shot_time = time.time()
            logger.info(f"Recoil control activated for {self.current_weapon}")
        elif self.firing and not mouse.is_pressed('left'):
            self.firing = False
            return
        
        if self.firing:
            current_time = time.time()
            shot_duration = current_time - self.last_shot_time
            pattern = Config.RECOIL_PATTERNS[self.current_weapon]
            
            # Adjust index based on 0.1s per step
            pattern_index = min(int(shot_duration / 0.1), len(pattern) - 1)
            x, y = pattern[pattern_index]
            
            self.move_mouse_safely(-x, -y)  # Usar movimento seguro
            
            # Add human variation
            if self.human_like_movements:
                x += random.uniform(-0.3, 0.3)
                y += random.uniform(-0.3, 0.3)
            
            # Apply anti-recoil movement
            pyautogui.move(-x, -y, _pause=False)
            
    def predict_target_movement(self, current_position):
            """Predicts target movement based on previous positions"""
            
            if current_position is None:
                 return [0, 0]  # Retorno seguro se não houver posição
            
            if self.last_target_position is None:
                self.last_target_position = current_position
                return [0, 0]  # Sem predição inicial
            
            # Calculate movement vector
            dx = current_position[0] - self.last_target_position[0]
            dy = current_position[1] - self.last_target_position[1]
                
            # Update prediction with smoothing (70% new, 30% old)
            self.target_prediction[0] = 0.7 * dx + 0.3 * self.target_prediction[0] 
            self.target_prediction[1] = 0.7 * dy + 0.3 * self.target_prediction[1]
            
                # Inicializar a predição se for a primeira vez              
            self.last_target_position = current_position.copy()
                
            return self.target_prediction.copy()  # Retornar uma cópia para evitar referência

    def move_mouse_safely(self, target_x, target_y):
        
        # Aumentar margem de segurança
        margin = 100
        screen_width, screen_height = pyautogui.size()
        
        # Get current position
        current_x, current_y = pyautogui.position()
        
        # Calculate new position
        new_x = current_x + target_x
        new_y = current_y + target_y
        
        # Get screen dimensions
        screen_width, screen_height = pyautogui.size()
        
        # Set safe margins (20 pixels from edges)
        margin = 30
        
        # Limit to safe area
        new_x = max(margin, min(new_x, screen_width - margin))
        new_y = max(margin, min(new_y, screen_height - margin))
        
        # Move relative to current position but respecting bounds
        safe_rel_x = new_x - current_x
        safe_rel_y = new_y - current_y
        
         # Check if the move would trigger failsafe
        if (new_x < margin or new_x > screen_width - margin or 
            new_y < margin or new_y > screen_height - margin):
            logger.warning("Movement prevented to avoid corner trigger")
            return
        
        # Adicionar movimento suave
        pyautogui.move(
                target_x, 
                target_y,
                duration=random.uniform(0.05, 0.15),
                tween=pyautogui.easeInOutQuad,
                _pause=False
            )
        
        # Perform the move
        pyautogui.move(safe_rel_x, safe_rel_y, _pause=False)


    def aggressive_aimbot(self, img_bgr, hsv):       
        # Get dimensions for center calculation
        height, width = img_bgr.shape[:2]
        width_half, height_half = width // 2, height // 2
        
        # Masks for multiple color ranges
        mask1 = cv2.inRange(hsv, self.lower, self.upper)
        mask2 = cv2.inRange(hsv, self.lower2, self.upper2)
        mask3 = cv2.inRange(hsv, self.lower3, self.upper3)
        mask = cv2.bitwise_or(mask1, mask2, mask3)
        
        # Combine all masks
        mask = cv2.bitwise_or(cv2.bitwise_or(mask1, mask2), mask3)
        
        # Morphological operations with larger kernel
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)
        mask = cv2.erode(mask, kernel, iterations=1)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Find largest contour
            largest = max(contours, key=cv2.contourArea)
            M = cv2.moments(largest)
            
            if cv2.contourArea(largest) > 5:  # Filtro de área mínima
                M = cv2.moments(largest)

            if M["m00"] != 0:
                # Calculate contour center
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                
                # Adjust to aim for the head
                head_offset = -8
                cY += head_offset
                
                # Predict movement
                prediction = self.predict_target_movement([cX, cY])
                
                # Verificação crítica de segurança
                if prediction is None or len(prediction) < 2:
                    logger.warning("Predição inválida, ignorando movimento")
                    return
                    
                # Apply prediction with damping factor
                prediction_strength = 1.5  # Multiplicador de predição
                predict_x = cX + prediction[0] * prediction_strength
                predict_y = cY + prediction[1] * prediction_strength
                
                # Calculate distance to target
                distance_to_target = abs(cX - Config.SCAN_AREA_X) + abs(cY - Config.SCAN_AREA_Y)
                
                # Adjust lock_power based on distance
                adjusted_lock = self.lock_power
                if distance_to_target > 50:
                    adjusted_lock = int(self.lock_power * 1.3)  # 30% more aggressive for distant targets
                
                # Calculate movement with dynamic adjustment
                rel_x = (cX - Config.SCAN_AREA_X) * adjusted_lock / 100
                rel_y = (cY - Config.SCAN_AREA_Y) * adjusted_lock / 100
                
                # Add human movement
                if self.human_like_movements:
                    rel_x += random.uniform(-0.3, 0.3)
                    rel_y += random.uniform(-0.3, 0.3)
                
                # Add random delay to simulate human reaction
                sleep(random.uniform(0.01, 0.05))
                
                # Move mouse with safety check
                self.move_mouse_safely(rel_x, rel_y)
                                          
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
                sleep(0.005)  # Reduced from 0.005 to balance CPU and response


# Apply kernel camouflage to the AimbotController
AimbotController = add_kernel_camouflage(AimbotController)

def main():
    logger.info("Starting Valorant Advanced Aimbot with Kernel Camouflage protection")
    logger.warning("FAILSAFE desativado - Movimentos do mouse não serão interrompidos automaticamente")
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