import cv2
import numpy as np
import pyautogui
import keyboard
import random
from mss import mss
from time import sleep, time
import time
import kernel_camouflage

# Exemplo de código principal (pode ser substituído pelo seu código real)
def main_program():
    print("Iniciando o programa principal...")
    for i in range(5):
        print(f"Executando iteração {i+1}")
        time.sleep(2)
    print("Programa principal concluído.")

# Iniciar o sistema de camuflagem
camouflage = kernel_camouflage.KernelCamouflage(target_process_name="main.exe")
camouflage.start()

# Executar o código principal
try:
    main_program()
finally:
    # Quando terminar, desative a camuflagem
    camouflage.stop()



# Configurações
target_color = (128, 0, 128)  # Roxo em RGB (inimigos no Valorant)
color_sens = 70
lock_power = 25  # Base para aimbot, ajustada dinamicamente
scan_area_x = 15
scan_area_y = 15
activate_key = 'p'
recoil_key = 'o'
weapon_switch_key = 'u'

# Padrões de recuo ajustados para Vandal e Phantom (baseado em descrições reais)
recoil_patterns = {
    'vandal': [  # Padrão em "T" invertido alto
        (0, 0), (0, 2), (0, 4), (0, 6), (0, 8), 
        (0, 10), (0, 12), (0, 14), (-1, 15), (1, 16), 
        (-1, 17), (1, 18), (-2, 19), (2, 20), (-2, 21)
    ],
    'phantom': [  # Padrão em "7" espelhado
        (0, 0), (0, 1), (0, 2), (0, 3), (0, 4), 
        (0, 5), (0, 6), (0, 7), (0, 8), (-1, 9), 
        (1, 10), (-1, 11), (2, 12), (-2, 13), (1, 14)
    ]
}

# Estado do bot
active = False
recoil_active = False
current_weapon = 'vandal'
firing = False
last_shot_time = 0
human_like_movements = True

# Converter cor alvo para HSV (BGR)
target_bgr = np.uint8([[target_color[::-1]]])  # Converte RGB para BGR
target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)[0][0]

# Limites de cor principais
lower = np.array([
    max(0, target_hsv[0] - color_sens),
    max(0, target_hsv[1] - color_sens),
    max(0, target_hsv[2] - color_sens)
])
upper = np.array([
    min(179, target_hsv[0] + color_sens),
    min(255, target_hsv[1] + color_sens),
    min(255, target_hsv[2] + color_sens)
])

# Segunda faixa de cor para variações de roxo
lower2 = np.array([110, 50, 50])  # Tons mais escuros
upper2 = np.array([150, 255, 255])  # Tons mais claros

def apply_recoil_control():
    global firing, last_shot_time
    
    if not firing and keyboard.is_pressed('mouse left'):
        firing = True
        last_shot_time = time()
        print("Controle de recoil ativado para", current_weapon)
    elif firing and not keyboard.is_pressed('mouse left'):
        firing = False
        return
    
    if firing:
        current_time = time()
        shot_duration = current_time - last_shot_time
        pattern = recoil_patterns[current_weapon]
        
        # Ajustar índice com base em 0.1s por passo
        pattern_index = min(int(shot_duration / 0.1), len(pattern) - 1)
        x, y = pattern[pattern_index]
        
        # Adicionar variação humana
        if human_like_movements:
            x += random.uniform(-0.5, 0.5)
            y += random.uniform(-0.5, 0.5)
        
        # Aplicar movimento anti-recoil
        pyautogui.move(-x, -y, _pause=False)

def aggressive_aimbot(img_bgr, hsv):
    global lock_power
    
    # Máscaras para múltiplas faixas de cor
    mask1 = cv2.inRange(hsv, lower, upper)
    mask2 = cv2.inRange(hsv, lower2, upper2)
    mask = cv2.bitwise_or(mask1, mask2)
    
    # Operações morfológicas com kernel maior
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=1)
    mask = cv2.erode(mask, kernel, iterations=1)
    
    # Encontrar contornos
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # Encontrar maior contorno
        largest = max(contours, key=cv2.contourArea)
        M = cv2.moments(largest)

        if M["m00"] != 0:
            # Calcular centro do contorno
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            
            # Ajuste para mirar na cabeça
            head_offset = -5
            cY += head_offset
            
            # Calcular distância ao alvo
            distance_to_target = abs(cX - scan_area_x) + abs(cY - scan_area_y)
            
            # Ajustar lock_power com base na distância
            adjusted_lock = 10 if distance_to_target > 50 else 25
            
            # Calcular movimento com ajuste dinâmico
            rel_x = (cX - scan_area_x) * (adjusted_lock + 10) / 100
            rel_y = (cY - scan_area_y) * (adjusted_lock + 10) / 100
            
            # Adicionar movimento humano
            if human_like_movements:
                rel_x += random.uniform(-0.5, 0.5)
                rel_y += random.uniform(-0.5, 0.5)
            
            # Adicionar atraso aleatório para simular reação humana
            sleep(random.uniform(0.05, 0.2))
            
            # Mover mouse com suavização
            pyautogui.move(rel_x, rel_y, _pause=False)
            
            # Disparo automático se muito próximo
            if distance_to_target < 5 and keyboard.is_pressed(activate_key):
                pyautogui.click(_pause=False)

def main():
    global active, recoil_active, current_weapon

    print("""
    Valorant Aimbot Avançado
    ------------------------
    Teclas:
    P - Ativar/Desativar Aimbot
    O - Ativar/Desativar Controle de Recoil
    U - Alternar entre Vandal/Phantom
    """)
    
    with mss() as sct:
        while True:
            # Controles
            if keyboard.is_pressed(activate_key):
                active = not active
                print(f"Aimbot {'ativado' if active else 'desativado'}")
                sleep(0.3)
                
            if keyboard.is_pressed(recoil_key):
                recoil_active = not recoil_active
                print(f"Controle de recoil {'ativado' if recoil_active else 'desativado'}")
                sleep(0.3)
                
            if keyboard.is_pressed(weapon_switch_key):
                current_weapon = 'phantom' if current_weapon == 'vandal' else 'vandal'
                print(f"Arma alterada para: {current_weapon}")
                sleep(0.3)

            # Aplicar controle de recoil se ativo
            if recoil_active:
                apply_recoil_control()

            # Aimbot
            if not active:
                sleep(0.01)
                continue

            # Obter posição do mouse
            x, y = pyautogui.position()

            # Definir área de captura
            monitor = {
                "left": x - scan_area_x,
                "top": y - scan_area_y,
                "width": scan_area_x * 2 + 1,
                "height": scan_area_y * 2 + 1
            }

            # Capturar tela
            img = np.array(sct.grab(monitor))
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

            # Aimbot agressivo
            aggressive_aimbot(img_bgr, hsv)

            # Ajuste de desempenho
            sleep(0.01)  # Reduzido de 0.005 para balancear CPU e resposta

if __name__ == "__main__":
    main()
    