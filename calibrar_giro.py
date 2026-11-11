# importa o OpenCV para câmera e desenho
import cv2

# importa o criador do detector YuNet do rosto.py
from rosto import criar_detector


def indice_de_giro(rosto):
    """Calcula o quanto o rosto está virado para um lado.
    ~0 = de frente; o sinal (+/-) indica o lado; o tamanho indica o quanto virou."""
    # posições 4 a 7: olho 1 (x, y) e olho 2 (x, y); posições 8 e 9: ponta do nariz (x, y)
    olho1_x, olho2_x = rosto[4], rosto[6]
    nariz_x = rosto[8]

    # ponto do meio entre os olhos (na horizontal)
    meio_olhos = (olho1_x + olho2_x) / 2

    # distância entre os olhos (usada para não depender de estar perto ou longe)
    distancia_olhos = abs(olho2_x - olho1_x)

    # evita divisão por zero se os olhos não forem detectados direito
    if distancia_olhos < 1:
        return 0.0

    # deslocamento do nariz em relação ao meio dos olhos, proporcional à distância dos olhos
    return (nariz_x - meio_olhos) / distancia_olhos


# cria o detector e abre a câmera
detector = criar_detector()
camera = cv2.VideoCapture(0)
if not camera.isOpened():
    print("Erro: não foi possível abrir a câmera.")
    exit()

print("Vire a cabeça devagar para os lados. Pressione Q na janela para sair.")

while True:
    # lê um frame
    ok, frame = camera.read()
    if not ok:
        continue

    # procura rostos
    altura, largura = frame.shape[:2]
    detector.setInputSize((largura, altura))
    _, rostos = detector.detect(frame)

    if rostos is not None and len(rostos) == 1:
        rosto = rostos[0]

        # desenha os 5 pontos (olhos, nariz e cantos da boca) em amarelo
        for i in range(5):
            x, y = int(rosto[4 + i * 2]), int(rosto[5 + i * 2])
            cv2.circle(frame, (x, y), 4, (0, 255, 255), -1)

        # calcula e mostra o índice de giro em letras grandes
        indice = indice_de_giro(rosto)
        cv2.putText(frame, f"Indice de giro: {indice:+.2f}", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    else:
        cv2.putText(frame, "Um rosto, por favor", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    # mostra a imagem
    cv2.imshow("Teste de Movimento", frame)

    # Q sai
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
