# importa o OpenCV para câmera e desenho na tela
import cv2

# importa a conexão com o banco
from banco import conectar

# importa do rosto.py as funções que já criamos na etapa 3
from rosto import criar_detector, criar_reconhecedor, gerar_assinatura, bytes_para_assinatura

# nota mínima para considerar a mesma pessoa (valor recomendado para o SFace)
LIMITE_SEMELHANCA = 0.363

# tipo de comparação do SFace: 0 = similaridade de cosseno (quanto maior, mais parecido)
COMPARACAO_COSSENO = 0

# pede o código do morador cujo rosto será comparado
codigo = input("Código do morador para comparar: ").strip()

# busca no banco o nome e a assinatura salva desse morador
conexao = conectar()
cursor = conexao.cursor()
cursor.execute("SELECT nome, rosto_embedding FROM moradores WHERE codigo = %s", (codigo,))
resultado = cursor.fetchone()
cursor.close()
conexao.close()

# se o código não existe ou o rosto ainda não foi cadastrado, avisa e encerra
if resultado is None or resultado[1] is None:
    print("Morador não encontrado ou sem rosto cadastrado.")
    exit()

# separa o nome e converte os bytes do banco de volta para a assinatura 1x128
nome, dados = resultado
assinatura_salva = bytes_para_assinatura(dados)
print(f"Comparando com: {nome}. Pressione Q na janela para sair.")

# cria os modelos de detecção e reconhecimento
detector = criar_detector()
reconhecedor = criar_reconhecedor()

# abre a webcam
camera = cv2.VideoCapture(0)
if not camera.isOpened():
    print("Erro: não foi possível abrir a câmera.")
    exit()

while True:
    # lê um frame da câmera
    ok, frame = camera.read()
    if not ok:
        break

    # ajusta o detector ao tamanho do frame e procura rostos
    altura, largura = frame.shape[:2]
    detector.setInputSize((largura, altura))
    _, rostos = detector.detect(frame)

    # cópia só para desenhar, mantendo o frame original limpo
    tela = frame.copy()

    if rostos is not None:
        # compara cada rosto encontrado com a assinatura salva
        for rosto in rostos:
            # gera a assinatura do rosto que está na câmera agora
            assinatura_ao_vivo = gerar_assinatura(reconhecedor, frame, rosto)

            # calcula a nota de semelhança entre o rosto ao vivo e o salvo
            nota = reconhecedor.match(assinatura_salva, assinatura_ao_vivo, COMPARACAO_COSSENO)

            # decide: nota acima do limite = mesma pessoa (verde); abaixo = outra pessoa (vermelho)
            if nota >= LIMITE_SEMELHANCA:
                texto, cor = f"{nome} ({nota:.2f})", (0, 255, 0)
            else:
                texto, cor = f"Desconhecido ({nota:.2f})", (0, 0, 255)

            # desenha o retângulo e o texto em cima do rosto
            x, y, w, h = rosto[0:4].astype(int)
            cv2.rectangle(tela, (x, y), (x + w, y + h), cor, 2)
            cv2.putText(tela, texto, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)

    # mostra a imagem
    cv2.imshow("Teste de Comparacao", tela)

    # Q sai do teste
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# libera a câmera e fecha a janela
camera.release()
cv2.destroyAllWindows()
