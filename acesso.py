# importa o time para medir o tempo limite da verificação facial
import time

# importa o OpenCV para câmera e desenho na tela
import cv2

# importa o bcrypt para conferir a senha com o hash salvo
import bcrypt

# importa o getpass para ler a senha sem mostrar na tela
from getpass import getpass

# importa a conexão com o banco
from banco import conectar

# importa as funções de rosto criadas na etapa 3
from rosto import criar_detector, criar_reconhecedor, gerar_assinatura, bytes_para_assinatura

# nota mínima de semelhança, definida no teste da etapa 4.1
LIMITE_SEMELHANCA = 0.5

# quantos frames seguidos o rosto precisa passar no limite para confirmar
FRAMES_PARA_CONFIRMAR = 5

# tempo máximo, em segundos, para a verificação facial
TEMPO_LIMITE = 10

# quantas falhas de leitura da câmera são toleradas antes de desistir
MAX_FALHAS_LEITURA = 30

# tipo de comparação do SFace: 0 = similaridade de cosseno
COMPARACAO_COSSENO = 0

# tamanho máximo do código, igual à coluna codigo_digitado (VARCHAR(10))
TAMANHO_MAX_CODIGO = 10


def registrar_acesso(codigo_digitado, morador_id, resultado, motivo, nota_facial=None):
    """Grava uma tentativa de acesso na tabela 'acessos'."""
    # abre a conexão e o cursor
    conexao = conectar()
    cursor = conexao.cursor()

    # insere a tentativa; data_hora é preenchida automaticamente pelo MySQL
    cursor.execute(
        """
        INSERT INTO acessos (morador_id, codigo_digitado, resultado, motivo, nota_facial)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            morador_id,                                  # id do morador ou None
            codigo_digitado[:TAMANHO_MAX_CODIGO],        # corta em 10 caracteres para caber na coluna
            resultado,                                   # 'LIBERADO' ou 'NEGADO'
            motivo,                                      # texto explicando o resultado
            None if nota_facial is None else round(nota_facial, 3),  # nota com 3 casas ou NULL
        ),
    )

    # confirma a gravação e fecha tudo
    conexao.commit()
    cursor.close()
    conexao.close()


def verificar_credenciais(codigo, senha):
    """Confere código e senha.
    Devolve (situacao, morador_id, nome, assinatura), onde situacao é:
    'ok'         -> código e senha certos, rosto cadastrado
    'sem_rosto'  -> código e senha certos, mas sem rosto cadastrado
    'invalido'   -> código inexistente ou senha errada"""
    # busca o morador ativo pelo código
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id, nome, senha_hash, rosto_embedding FROM moradores WHERE codigo = %s AND ativo = 1",
        (codigo,),
    )
    morador = cursor.fetchone()
    cursor.close()
    conexao.close()

    # código não existe ou morador inativo: não há id para registrar
    if morador is None:
        return ("invalido", None, None, None)

    # separa os campos da linha encontrada
    morador_id, nome, senha_hash, rosto_bytes = morador

    # senha errada: devolve o id para o histórico mostrar QUEM foi alvo da tentativa
    if not bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8")):
        return ("invalido", morador_id, None, None)

    # senha certa, mas o rosto ainda não foi cadastrado
    if rosto_bytes is None:
        return ("sem_rosto", morador_id, nome, None)

    # tudo certo: devolve também a assinatura convertida dos bytes
    return ("ok", morador_id, nome, bytes_para_assinatura(rosto_bytes))


def verificar_rosto(assinatura_salva):
    """Abre a câmera e tenta confirmar o rosto.
    Devolve (aprovado, motivo, melhor_nota)."""
    # cria os modelos de detecção e reconhecimento
    detector = criar_detector()
    reconhecedor = criar_reconhecedor()

    # abre a webcam
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        return (False, "câmera não abriu", 0.0)

    # contador de frames seguidos aprovados
    acertos_seguidos = 0

    # contador de leituras da câmera que falharam
    falhas_leitura = 0

    # maior nota vista durante a verificação
    melhor_nota = 0.0

    # resultado inicial
    aprovado = False
    motivo = "tempo esgotado"

    # guarda o momento em que a verificação começou
    inicio = time.time()

    while True:
        # calcula quantos segundos ainda restam
        restante = TEMPO_LIMITE - (time.time() - inicio)

        # se o tempo acabou, encerra (o motivo já é "tempo esgotado")
        if restante <= 0:
            break

        # lê um frame da câmera
        ok, frame = camera.read()

        # se a leitura falhou, conta a falha e tenta de novo em vez de desistir
        if not ok:
            falhas_leitura += 1
            if falhas_leitura >= MAX_FALHAS_LEITURA:
                motivo = "falha ao ler a câmera"
                break
            continue

        # ajusta o detector ao tamanho do frame e procura rostos
        altura, largura = frame.shape[:2]
        detector.setInputSize((largura, altura))
        _, rostos = detector.detect(frame)

        # cópia só para desenhar
        tela = frame.copy()

        # texto padrão da nota, quando não há rosto avaliado
        texto_nota = "Nota: --"

        # só avalia quando há exatamente UM rosto na frente da câmera
        if rostos is not None and len(rostos) == 1:
            # gera a assinatura do rosto ao vivo e calcula a nota
            assinatura_ao_vivo = gerar_assinatura(reconhecedor, frame, rostos[0])
            nota = reconhecedor.match(assinatura_salva, assinatura_ao_vivo, COMPARACAO_COSSENO)

            # guarda a maior nota já vista
            melhor_nota = max(melhor_nota, nota)

            # prepara o texto da nota para a tela
            texto_nota = f"Nota: {nota:.2f}"

            # se passou no limite, soma um acerto; se não, zera a sequência
            if nota >= LIMITE_SEMELHANCA:
                acertos_seguidos += 1
                cor = (0, 255, 0)
            else:
                acertos_seguidos = 0
                cor = (0, 0, 255)

            # desenha o retângulo em volta do rosto
            x, y, w, h = rostos[0][0:4].astype(int)
            cv2.rectangle(tela, (x, y), (x + w, y + h), cor, 2)
        else:
            # nenhum rosto ou mais de um: zera a sequência
            acertos_seguidos = 0

        # linha 1: tempo restante e progresso da confirmação
        cv2.putText(tela, f"Tempo: {restante:.0f}s  Confirmando: {acertos_seguidos}/{FRAMES_PARA_CONFIRMAR}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # linha 2: nota atual
        cv2.putText(tela, texto_nota, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # mostra a imagem
        cv2.imshow("Verificacao Facial", tela)

        # Q permite cancelar
        if cv2.waitKey(1) & 0xFF == ord("q"):
            motivo = "cancelado pelo usuário"
            break

        # atingiu os frames seguidos necessários: aprovado
        if acertos_seguidos >= FRAMES_PARA_CONFIRMAR:
            aprovado = True
            motivo = "rosto confirmado"
            break

    # libera a câmera e fecha a janela
    camera.release()
    cv2.destroyAllWindows()

    return (aprovado, motivo, melhor_nota)


# este bloco só roda com "python acesso.py"
if __name__ == "__main__":
    print("=== PORTARIA ===")

    # passo 1: código
    codigo = input("Código de acesso: ").strip()

    # passo 2: senha (não aparece na tela e nunca é gravada)
    senha = getpass("Senha: ")

    # confere código e senha juntos
    situacao, morador_id, nome, assinatura_salva = verificar_credenciais(codigo, senha)

    # código ou senha inválidos: registra e mostra mensagem genérica
    if situacao == "invalido":
        registrar_acesso(codigo, morador_id, "NEGADO", "código ou senha inválidos")
        print("ACESSO NEGADO: código ou senha inválidos.")
        exit()

    # senha certa, mas sem rosto cadastrado: registra e avisa
    if situacao == "sem_rosto":
        registrar_acesso(codigo, morador_id, "NEGADO", "rosto não cadastrado")
        print("ACESSO NEGADO: rosto não cadastrado. Procure a administração.")
        exit()

    # passo 3: verificação facial
    print("Olhe para a câmera...")
    aprovado, motivo, melhor_nota = verificar_rosto(assinatura_salva)

    # registra o resultado final com o motivo e a melhor nota
    if aprovado:
        registrar_acesso(codigo, morador_id, "LIBERADO", motivo, melhor_nota)
        print(f"ACESSO LIBERADO. Bem-vindo(a), {nome}!")
    else:
        registrar_acesso(codigo, morador_id, "NEGADO", motivo, melhor_nota)
        print(f"ACESSO NEGADO: {motivo} (melhor nota: {melhor_nota:.2f}).")
