import cv2
import numpy as np
import pyautogui
import keyboard
from mss import mss
from time import sleep
import random
import os
import sys
import logging

# ===== CONFIGURAÇÕES =====
target_color = (102, 0, 153)  # Roxo escuro em RGB
color_sens = 60  # Sensibilidade ampla para testes
lock_power = 80  # Movimento mais forte para testes
scan_area_x = 20  # Área maior para testes
scan_area_y = 20
activate_key = 'p'
active = False

# ===== CONFIGURAÇÃO DE LOG =====
logging.basicConfig(
    level=logging.DEBUG,
    filename='colorbot.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ===== FUNÇÕES DE DIAGNÓSTICO =====
def teste_hardware():
    """Verifica se todos os módulos estão funcionando"""
    logging.info("Executando teste de hardware...")
    
    # Teste de captura de tela
    try:
        with mss() as sct:
            img = sct.grab({"top": 0, "left": 0, "width": 100, "height": 100})
            logging.info("✅ Captura de tela funcionando")
    except Exception as e:
        logging.error(f"❌ Falha na captura: {str(e)}")
    
    # Teste de controle do mouse
    try:
        pos = pyautogui.position()
        pyautogui.moveTo(pos.x + 10, pos.y + 10)
        logging.info("✅ Controle do mouse funcionando")
    except Exception as e:
        logging.error(f"❌ Falha no mouse: {str(e)}")
    
    # Teste de teclado
    try:
        logging.info("✅ Módulo de teclado carregado (pressione ESC para testar)")
        keyboard.wait('esc', timeout=5)
        logging.info("✅ Teclado respondendo")
    except Exception as e:
        logging.error(f"❌ Falha no teclado: {str(e)}")

def vs_code_fix():
    """Correções específicas para execução no VS Code"""
    if 'VSCODE_PID' in os.environ:
        os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '1'
        logging.info("Aplicando ajustes para VS Code")

# ===== FUNÇÕES PRINCIPAIS =====
def get_hsv_limits(hsv_val, sensitivity):
    """Calcula limites HSV com proteção contra overflow"""
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

def human_like_move(dx, dy):
    """Movimento humanoide com variação aleatória"""
    steps = random.randint(3, 8)
    for _ in range(steps):
        pyautogui.move(
            dx/steps + random.uniform(-1, 1),
            dy/steps + random.uniform(-1, 1),
            duration=random.uniform(0.01, 0.05)
        )
        sleep(random.uniform(0.01, 0.03))

def safe_activate():
    """Ativação mais segura com combinação de teclas"""
    global active
    if keyboard.is_pressed('ctrl+alt') and keyboard.is_pressed(activate_key):
        active = not active
        logging.info(f"Bot {'ativado' if active else 'desativado'}")
        sleep(1)  # Delay anti-spam

# ===== LOOP PRINCIPAL =====
def main():
    global active
    
    # Configuração inicial
    vs_code_fix()
    teste_hardware()
    
    # Conversão de cor inicial
    target_bgr = np.uint8([[list(target_color)[::-1]]])
    target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)[0][0]
    lower, upper = get_hsv_limits(target_hsv, color_sens)
    
    logging.info(f"Alvo HSV: {target_hsv} | Limites: {lower} - {upper}")
    
    with mss() as sct:
        while True:
            safe_activate()
            
            if not active:
                sleep(0.1)
                continue
            
            # Captura de tela
            x, y = pyautogui.position()
            monitor = {
                "left": x - scan_area_x,
                "top": y - scan_area_y,
                "width": scan_area_x * 2 + 1,
                "height": scan_area_y * 2 + 1
            }
            
            try:
                img = np.array(sct.grab(monitor))
                img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
                
                # Pré-processamento
                blur = cv2.GaussianBlur(hsv, (5, 5), 0)
                mask = cv2.inRange(blur, lower, upper)
                mask = cv2.erode(mask, None, iterations=1)
                mask = cv2.dilate(mask, None, iterations=2)
                
                # Debug visual
                cv2.imshow('Mascara', mask)
                cv2.waitKey(1)
                
                # Detecção de contornos
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if contours:
                    # Priorização de alvos
                    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:3]
                    
                    for cnt in contours:
                        if cv2.contourArea(cnt) < 5:
                            continue
                            
                        x, y, w, h = cv2.boundingRect(cnt)
                        center_x = x + w//2
                        center_y = y + h//2
                        
                        # Movimento humanoide
                        rel_x = (center_x - scan_area_x) * (lock_power / 50)
                        rel_y = (center_y - scan_area_y) * (lock_power / 50)
                        human_like_move(rel_x, rel_y)
                        break
                
                # Delay com variação humana
                sleep(random.uniform(0.05, 0.2))
                
            except Exception as e:
                logging.error(f"Erro no loop principal: {str(e)}")
                sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Script encerrado pelo usuário")
    except Exception as e:
        logging.critical(f"Erro crítico: {str(e)}")
    finally:
        cv2.destroyAllWindows()