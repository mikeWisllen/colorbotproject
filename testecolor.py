import cv2
import numpy as np
import pyautogui
import keyboard
from mss import mss
from time import sleep, time
import random
from collections import deque

# ===== CONFIGURAÇÕES =====
target_color = (128, 0, 128)  # Roxo em RGB
color_sens = 65
lock_power = 40
scan_area_x = 5
scan_area_y = 5
LOCK_DISTANCE_THRESHOLD = 20  # Distância máxima para travar (em pixels)
STICKINESS_FACTOR = 0.4     # Fator de aderência (0.1 a 0.5)
activate_key = 'p'
active = False

# ===== INICIALIZAÇÃO GPU =====
def init_gpu():
    if cv2.cuda.getCudaEnabledDeviceCount() > 0:
        cv2.cuda.setDevice(0)
        print(f"GPU Detectada: {cv2.cuda.printCudaDeviceInfo(0)}")
        
        # Configuração específica para GTX 1660 Super (6GB VRAM)
        cv2.cuda.setBufferPoolUsage(True)
        cv2.cuda.setBufferPoolConfig(0, 512 * 1024 * 1024, 6)
        
        # Pré-aloca buffers
        stream = cv2.cuda_Stream()
        hsv_gpu = cv2.cuda_GpuMat()
        mask_gpu = cv2.cuda_GpuMat()
        
        return stream, hsv_gpu, mask_gpu
    else:
        print("GPU não detectada - Usando CPU")
        return None, None, None

stream, hsv_gpu, mask_gpu = init_gpu()

# ===== PIPELINE DE PROCESSAMENTO GPU =====
def gpu_pipeline(frame, lower, upper):
    # Upload para GPU (assíncrono)
    frame_gpu = cv2.cuda_GpuMat()
    frame_gpu.upload(frame, stream=stream)
    
    # Conversão HSV
    hsv_gpu = cv2.cuda.cvtColor(frame_gpu, cv2.COLOR_BGR2HSV, stream=stream)
    
    # Thresholding
    mask_gpu = cv2.cuda.inRange(hsv_gpu, lower, upper, stream=stream)
    
    # Operações morfológicas
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
    erode = cv2.cuda.createMorphologyFilter(cv2.MORPH_ERODE, mask_gpu.type(), kernel)
    dilate = cv2.cuda.createMorphologyFilter(cv2.MORPH_DILATE, mask_gpu.type(), kernel)
    
    mask_gpu = erode.apply(mask_gpu, stream=stream)
    mask_gpu = dilate.apply(mask_gpu, stream=stream)
    
    # Download assíncrono
    mask = mask_gpu.download(stream=stream)
    stream.waitForCompletion()
    
    return mask

# ===== CONVERSÃO DE COR =====
target_bgr = np.uint8([[list(target_color)[::-1]]])
target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)[0][0]
lower = np.array([max(0, target_hsv[0]-color_sens), 100, 100])
upper = np.array([min(179, target_hsv[0]+color_sens), 255, 255])

# ===== LOOP PRINCIPAL =====
def main():
    global active
    
    # Buffer para frames
    frame_buffer = deque(maxlen=3)
    last_time = time()
    
    with mss() as sct:
        while True:
            start_time = time()
            
            # Controle de ativação
            if keyboard.is_pressed(activate_key):
                active = not active
                print(f"Bot {'ativado' if active else 'desativado'}")
                sleep(0.5)

            if not active:
                sleep(0.01)
                continue

            # Captura de tela
            monitor = {
                "left": pyautogui.position().x - scan_area_x,
                "top": pyautogui.position().y - scan_area_y,
                "width": scan_area_x * 2 + 1,
                "height": scan_area_y * 2 + 1
            }
            
            try:
                # Processamento acelerado
                frame = np.array(sct.grab(monitor))
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                frame_buffer.append(frame_bgr)
                
                # Usa GPU se disponível
                if stream is not None:
                    mask = gpu_pipeline(frame_bgr, lower, upper)
                else:
                    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
                    mask = cv2.inRange(hsv, lower, upper)
                    mask = cv2.erode(mask, None, iterations=1)
                    mask = cv2.dilate(mask, None, iterations=2)
                
                # Detecção de contornos
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if contours:
                    best_target = max(contours, key=cv2.contourArea)
                    x, y, w, h = cv2.boundingRect(best_target)
                    target_center = (x + w//2, y + h//2)
                    
                    # Calcula vetor de distância
                    dx = target_center[0] - scan_area_x
                    dy = target_center[1] - scan_area_y
                    distance = (dx**2 + dy**2)**0.5
                    
                    if distance < LOCK_DISTANCE_THRESHOLD:
                        # Modo "trava suave" - ajuste dinâmico
                        power = min(lock_power/100, STICKINESS_FACTOR * (1 - distance/LOCK_DISTANCE_THRESHOLD))
                        
                        # Movimento proporcional com inércia
                        move_x = dx * power * random.uniform(0.9, 1.1)
                        move_y = dy * power * random.uniform(0.9, 1.1)
                        
                        # Movimento humanoide em etapas
                        steps = max(2, int(distance/3))
                        for _ in range(steps):
                            pyautogui.move(
                                move_x/steps,
                                move_y/steps,
                                duration=random.uniform(0.01, 0.03)
                            )
                            if keyboard.is_pressed(activate_key):  # Permite cancelar
                                break
                
                # Monitoramento de desempenho
                fps = 1 / (time() - last_time)
                latency = (time() - start_time) * 1000
                last_time = time()
                
                print(f"FPS: {fps:.1f} | Latência: {latency:.1f}ms | Alvos: {len(contours)}", end='\r')

            except Exception as e:
                print(f"\nErro: {str(e)}")
                continue

if __name__ == "__main__":
    main()