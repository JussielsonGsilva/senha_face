# importa o OpenCV, a biblioteca que acessa a câmera e trata imagens
import cv2

# abre a câmera de índice 0 (normalmente a webcam do notebook ou a primeira USB)
camera = cv2.VideoCapture(0)

# confere se a câmera abriu; se não abriu, avisa e encerra o programa
if not camera.isOpened():
    print("Erro: não foi possível abrir a câmera.")
    exit()

# avisa no terminal como sair do teste
print("Câmera aberta. Pressione a tecla Q na janela do vídeo para sair.")

# repete sem parar até o usuário mandar sair
while True:
    # lê uma imagem (frame) da câmera; 'ok' diz se a leitura funcionou
    ok, frame = camera.read()

    # se a leitura falhou, avisa e sai do laço
    if not ok:
        print("Erro: falha ao ler a imagem da câmera.")
        break

    # mostra o frame numa janela chamada "Teste da Camera"
    cv2.imshow("Teste da Camera", frame)

    # espera 1 milissegundo por uma tecla; se for 'q', sai do laço
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# libera a câmera para outros programas poderem usá-la
camera.release()

# fecha todas as janelas abertas pelo OpenCV
cv2.destroyAllWindows()
