import cv2
import numpy as np
import pyautogui
import keyboard
from mss import mss
from time import sleep

# ===== CONFIGURAÇÕES =====
target_color = (128, 0, 128)  # Roxo em RGB
color_sens = 65  # Reduzido para evitar overflowp
lock_power = 20
scan_area_x = 8
scan_area_y = 8
activate_key = 'p'
active = False  # Definindo a variável global

# ===== SISTEMA DE APRENDIZADO =====
learning_data = []
learning_interval = 50

# ===== INICIALIZAÇÃO HSV =====
target_bgr = np.uint8([[list(target_color)[::-1]]])  # RGB → BGR
target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)[0][0]

# Função segura para calcular limites
def get_hsv_limits(hsv_val, sensitivity):
    h = np.clip(hsv_val[0], 0, 179)
    s = np.clip(hsv_val[1], 0, 255)
    v = np.clip(hsv_val[2], 0, 255)
    
    lower = np.array([
        max(0, h - sensitivity),
        max(0, s - sensitivity),
        max(0, v - sensitivity)
    ], dtype=np.uint8)
    
    upper = np.array([
        min(179, h + sensitivity),
        min(255, s + sensitivity),
        min(255, v + sensitivity)
    ], dtype=np.uint8)
    
    return lower, upper

lower, upper = get_hsv_limits(target_hsv, color_sens)

# ... (restante do código permanece igual até a função main) ...

def main():
    global active, learning_data, lower, upper
    
    print("ColorBot iniciado. Pressione P para ativar/desativar")
    
    with mss() as sct:
        while True:
            if keyboard.is_pressed(activate_key):
                active = not active
                print(f"Bot {'ativado' if active else 'desativado'}")
                sleep(0.5)

            if not active:
                sleep(0.02)
                continue

            # ... (restante do loop principal permanece igual) ...

if __name__ == "__main__":
    try:
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            cv2.cuda.setDevice(0)
            print("GPU ativada para processamento")
        main()
    except Exception as e:
        print(f"Erro crítico: {str(e)}")