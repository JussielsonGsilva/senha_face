# importa o OpenCV
import cv2

# caminho do modelo detector de rosto baixado na etapa 3.1
MODELO_YUNET = "modelos/face_detection_yunet_2023mar.onnx"

# cria o detector de rostos YuNet
detector = cv2.FaceDetectorYN.create(
    MODELO_YUNET,   # arquivo do modelo
    "",             # arquivo de configuração extra (não precisa para .onnx)
    (320, 320),     # tamanho inicial da imagem (será ajustado ao tamanho real abaixo)
    0.9,            # confiança mínima: só aceita rostos com 90% ou mais de certeza
    0.3,            # limite para descartar quadrados repetidos sobre o mesmo rosto
    5000,           # máximo de candidatos analisados antes do filtro
)

# abre a webcam (índice 0)
camera = cv2.VideoCapture(0)

# se a câmera não abriu, avisa e encerra
if not camera.isOpened():
    print("Erro: não foi possível abrir a câmera.")
    exit()

# avisa como sair
print("Detecção ativa. Pressione Q na janela do vídeo para sair.")

# laço principal: repete até apertar Q
while True:
    # lê um frame da câmera
    ok, frame = camera.read()

    # se a leitura falhou, sai do laço
    if not ok:
        print("Erro: falha ao ler a imagem da câmera.")
        break

    # pega altura e largura do frame (shape = altura, largura, canais de cor)
    altura, largura = frame.shape[:2]

    # informa ao detector o tamanho real da imagem que ele vai analisar
    detector.setInputSize((largura, altura))

    # procura rostos no frame; 'rostos' é uma lista de linhas ou None se não achou nenhum
    _, rostos = detector.detect(frame)

    # se encontrou pelo menos um rosto
    if rostos is not None:
        # percorre cada rosto encontrado
        for rosto in rostos:
            # as 4 primeiras posições são x, y, largura e altura do retângulo
            x, y, w, h = rosto[0:4].astype(int)

            # a última posição (índice 14) é a confiança da detecção (0 a 1)
            confianca = rosto[14]

            # desenha o retângulo verde em volta do rosto (cor BGR, espessura 2)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # escreve a confiança em % logo acima do retângulo
            cv2.putText(frame, f"{confianca * 100:.0f}%", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # mostra o frame com os desenhos numa janela
    cv2.imshow("Teste de Deteccao", frame)

    # se apertar Q, sai do laço
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# libera a câmera e fecha as janelas
camera.release()
cv2.destroyAllWindows()
