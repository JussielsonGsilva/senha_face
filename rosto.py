# importa o time para controlar o intervalo entre as amostras
import time

# importa o OpenCV para câmera, detecção e reconhecimento
import cv2

# importa o numpy para calcular a média e converter a assinatura em bytes
import numpy as np

# importa a função de conexão com o banco
from banco import conectar

# caminhos dos modelos baixados na etapa 3.1
MODELO_YUNET = "modelos/face_detection_yunet_2023mar.onnx"
MODELO_SFACE = "modelos/face_recognition_sface_2021dec.onnx"

# quantas amostras do rosto são capturadas no cadastro
TOTAL_AMOSTRAS = 5

# intervalo mínimo, em segundos, entre uma amostra e outra
INTERVALO_AMOSTRAS = 0.7


def criar_detector():
    """Cria o detector de rostos YuNet (acha ONDE está o rosto)."""
    return cv2.FaceDetectorYN.create(
        MODELO_YUNET,   # arquivo do modelo
        "",             # configuração extra (não precisa para .onnx)
        (320, 320),     # tamanho inicial (ajustado a cada frame)
        0.9,            # confiança mínima de 90%
        0.3,            # limite para descartar quadrados repetidos
        5000,           # máximo de candidatos analisados
    )


def criar_reconhecedor():
    """Cria o reconhecedor SFace (gera a assinatura de QUEM é o rosto)."""
    return cv2.FaceRecognizerSF.create(MODELO_SFACE, "")


def gerar_assinatura(reconhecedor, frame, rosto):
    """Recebe o frame e um rosto detectado e devolve a assinatura (128 números)."""
    # recorta o rosto e o alinha pelos olhos, no tamanho que o SFace espera
    rosto_alinhado = reconhecedor.alignCrop(frame, rosto)

    # gera a assinatura: uma matriz 1x128 de números decimais (float32)
    return reconhecedor.feature(rosto_alinhado)


def media_das_assinaturas(lista_assinaturas):
    """Calcula a assinatura média de várias amostras e normaliza o resultado."""
    # empilha as assinaturas numa matriz (5 linhas x 128 colunas)
    matriz = np.vstack(lista_assinaturas)

    # tira a média de cada coluna, mantendo o formato 1x128
    media = np.mean(matriz, axis=0, keepdims=True)

    # normaliza (deixa com tamanho 1): a comparação por cosseno usa só a "direção" do vetor
    media = media / np.linalg.norm(media)

    # devolve no tipo float32, o mesmo usado pelo SFace
    return media.astype(np.float32)


def assinatura_para_bytes(assinatura):
    """Converte a assinatura em bytes para gravar na coluna BLOB."""
    # garante float32 (4 bytes cada) e transforma em bytes: 128 x 4 = 512 bytes
    return assinatura.astype(np.float32).tobytes()


def bytes_para_assinatura(dados):
    """Converte os bytes do banco de volta para a assinatura 1x128."""
    # lê os bytes como float32 e devolve no formato 1 linha x 128 colunas
    return np.frombuffer(dados, dtype=np.float32).reshape(1, 128)


def buscar_morador(codigo):
    """Devolve (id, nome) do morador ativo com esse código, ou None."""
    # abre a conexão e o cursor
    conexao = conectar()
    cursor = conexao.cursor()

    # procura o morador pelo código, somente se estiver ativo
    cursor.execute("SELECT id, nome FROM moradores WHERE codigo = %s AND ativo = 1", (codigo,))

    # pega a linha encontrada (ou None)
    morador = cursor.fetchone()

    # fecha cursor e conexão
    cursor.close()
    conexao.close()

    return morador


def salvar_assinatura(morador_id, assinatura):
    """Grava a assinatura do rosto no cadastro do morador."""
    # abre a conexão e o cursor
    conexao = conectar()
    cursor = conexao.cursor()

    # atualiza a coluna rosto_embedding do morador indicado
    cursor.execute(
        "UPDATE moradores SET rosto_embedding = %s WHERE id = %s",
        (assinatura_para_bytes(assinatura), morador_id),
    )

    # confirma a gravação
    conexao.commit()

    # fecha cursor e conexão
    cursor.close()
    conexao.close()


def capturar_assinatura():
    """Abre a câmera, captura várias amostras e devolve a assinatura média.
    Devolve None se o usuário apertar Q para cancelar."""
    # cria os dois modelos
    detector = criar_detector()
    reconhecedor = criar_reconhecedor()

    # abre a webcam
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Erro: não foi possível abrir a câmera.")
        return None

    # instruções no terminal
    print("ESPAÇO = começar a captura | Q = cancelar")
    print("Durante a captura, mexa levemente a cabeça (esquerda, direita, cima, baixo).")

    # lista onde ficam as assinaturas capturadas
    amostras = []

    # indica se a captura automática já começou (depois do ESPAÇO)
    capturando = False

    # momento da última amostra (começa em 0 para a primeira sair na hora)
    ultima_captura = 0.0

    # resultado final
    assinatura_final = None

    while True:
        # lê um frame
        ok, frame = camera.read()

        # se a leitura falhar, só tenta de novo
        if not ok:
            continue

        # ajusta o detector ao tamanho do frame e procura rostos
        altura, largura = frame.shape[:2]
        detector.setInputSize((largura, altura))
        _, rostos = detector.detect(frame)

        # conta quantos rostos foram encontrados (0 se veio None)
        quantidade = 0 if rostos is None else len(rostos)

        # cópia do frame só para desenhar
        tela = frame.copy()

        if quantidade == 1:
            # exatamente um rosto: desenha retângulo verde
            x, y, w, h = rostos[0][0:4].astype(int)
            cv2.rectangle(tela, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # se a captura está ativa e já passou o intervalo, guarda uma amostra
            if capturando and time.time() - ultima_captura >= INTERVALO_AMOSTRAS:
                amostras.append(gerar_assinatura(reconhecedor, frame, rostos[0]))
                ultima_captura = time.time()

            # mensagem de acordo com a situação
            if capturando:
                mensagem, cor = f"Capturando {len(amostras)}/{TOTAL_AMOSTRAS} - mexa a cabeca", (0, 255, 0)
            else:
                mensagem, cor = "Rosto OK - aperte ESPACO para comecar", (0, 255, 0)
        elif quantidade == 0:
            # nenhum rosto: a captura pausa até o rosto voltar
            mensagem, cor = "Nenhum rosto encontrado", (0, 0, 255)
        else:
            # mais de um rosto: a captura pausa, para não misturar pessoas
            mensagem, cor = "Apenas UMA pessoa na frente da camera", (0, 0, 255)

        # escreve a mensagem no topo da imagem
        cv2.putText(tela, mensagem, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor, 2)

        # mostra a imagem
        cv2.imshow("Cadastro de Rosto", tela)

        # lê a tecla pressionada
        tecla = cv2.waitKey(1) & 0xFF

        # Q cancela tudo
        if tecla == ord("q"):
            break

        # ESPAÇO (código 32) inicia a captura automática, se houver um rosto
        if tecla == 32 and quantidade == 1 and not capturando:
            capturando = True

        # juntou todas as amostras: calcula a média e encerra
        if len(amostras) >= TOTAL_AMOSTRAS:
            assinatura_final = media_das_assinaturas(amostras)
            break

    # libera a câmera e fecha a janela
    camera.release()
    cv2.destroyAllWindows()

    return assinatura_final


# este bloco só roda com "python rosto.py"
if __name__ == "__main__":
    print("=== Cadastro de rosto ===")

    # pede o código do morador já cadastrado
    codigo = input("Código de acesso do morador: ").strip()

    # procura o morador no banco
    morador = buscar_morador(codigo)
    if morador is None:
        print("Código não encontrado ou morador inativo.")
        exit()

    # separa id e nome
    morador_id, nome = morador
    print(f"Morador: {nome}")

    # abre a câmera e faz a captura das amostras
    assinatura = capturar_assinatura()
    if assinatura is None:
        print("Captura cancelada. Nada foi salvo.")
        exit()

    # grava no banco (substitui o rosto anterior, se houver)
    salvar_assinatura(morador_id, assinatura)
    print(f"Rosto de {nome} cadastrado com sucesso ({TOTAL_AMOSTRAS} amostras)!")
