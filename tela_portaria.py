# importa o sys para passar argumentos ao Qt e encerrar o programa
import sys

# importa o time para controlar o tempo limite da verificação facial
import time

# importa o painel da câmera PRIMEIRO: ele remove o conflito entre o Qt do OpenCV e o PySide6
from painel_camera import PainelCamera

# importa do acesso.py as funções e regras já testadas na etapa 4 e 5
from acesso import (
    verificar_credenciais,   # confere código e senha
    registrar_acesso,        # grava a tentativa na tabela acessos
    LIMITE_SEMELHANCA,       # nota mínima (0.5)
    FRAMES_PARA_CONFIRMAR,   # frames seguidos aprovados (5)
    TEMPO_LIMITE,            # segundos para confirmar o rosto (10)
    COMPARACAO_COSSENO,      # tipo de comparação do SFace
)

# importa do rosto.py os criadores dos modelos e o gerador de assinatura
from rosto import criar_detector, criar_reconhecedor, gerar_assinatura

# importa as classes de interface que vamos usar
from PySide6.QtWidgets import (
    QApplication,   # a aplicação Qt
    QWidget,        # janela/área genérica
    QLabel,         # texto
    QLineEdit,      # campo de digitação
    QPushButton,    # botão
    QGridLayout,    # layout em grade, usado no teclado
    QVBoxLayout,    # layout vertical
    QHBoxLayout,    # layout horizontal
)

# Qt = constantes; QTimer = relógio; QRegularExpression = regra de validação
from PySide6.QtCore import Qt, QTimer, QRegularExpression

# validador que só deixa digitar o que combina com a expressão regular
from PySide6.QtGui import QRegularExpressionValidator

# intervalo, em milissegundos, entre uma análise de rosto e outra
INTERVALO_ANALISE_MS = 100

# tempo, em milissegundos, que o resultado fica na tela antes de reiniciar
TEMPO_RESULTADO_MS = 4000

# cores da faixa de status
COR_NEUTRA = "#2d2d2d"
COR_AVISO = "#b45309"
COR_LIBERADO = "#15803d"
COR_NEGADO = "#b91c1c"


class TelaPortaria(QWidget):
    """Tela principal da portaria: câmera, campos, teclado e status."""

    def __init__(self):
        # inicializa a QWidget (classe "mãe")
        super().__init__()

        # título da janela
        self.setWindowTitle("Portaria - Controle de Acesso")

        # estilo geral: fundo escuro, texto claro, botões arredondados
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #f0f0f0; font-size: 18px; }
            QLineEdit { background-color: #2d2d2d; border: 2px solid #555; border-radius: 6px; padding: 8px; font-size: 24px; }
            QLineEdit:focus { border: 2px solid #3b82f6; }
            QPushButton { background-color: #333; border: 1px solid #555; border-radius: 8px; padding: 14px; font-size: 22px; }
            QPushButton:pressed { background-color: #555; }
            QPushButton:disabled { color: #777; }
        """)

        # ---------- modelos de rosto (criados uma vez só, ao abrir a tela) ----------

        # detector YuNet: acha onde está o rosto
        self.detector = criar_detector()

        # reconhecedor SFace: gera e compara assinaturas
        self.reconhecedor = criar_reconhecedor()

        # ---------- dados da verificação em andamento ----------

        # dados do morador que passou no código e senha (preenchidos em entrar())
        self.codigo_atual = None
        self.morador_id = None
        self.nome = None
        self.assinatura_salva = None

        # controle da verificação facial
        self.inicio_verificacao = 0.0
        self.acertos_seguidos = 0
        self.melhor_nota = 0.0

        # relógio que analisa os frames durante a verificação facial
        self.timer_verificacao = QTimer(self)
        self.timer_verificacao.timeout.connect(self.analisar_frame)

        # ---------- lado esquerdo: câmera ----------

        # cria o painel da câmera (começa desligado)
        self.painel_camera = PainelCamera()
        self.painel_camera.setText("Digite seu código e senha")

        # ---------- lado direito: título ----------

        titulo = QLabel("CONTROLE DE ACESSO")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 26px; font-weight: bold;")

        # ---------- campo código ----------

        rotulo_codigo = QLabel("Código:")
        self.campo_codigo = QLineEdit()

        # só aceita números, no máximo 10 dígitos (igual à coluna do banco)
        self.campo_codigo.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\d{0,10}"))
        )

        # ---------- campo senha ----------

        rotulo_senha = QLabel("Senha:")
        self.campo_senha = QLineEdit()

        # mostra bolinhas no lugar dos caracteres
        self.campo_senha.setEchoMode(QLineEdit.Password)

        # limita o tamanho da senha
        self.campo_senha.setMaxLength(64)

        # ---------- teclado numérico ----------

        grade_teclado = QGridLayout()

        # disposição das teclas
        teclas = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["Limpar", "0", "Apagar"],
        ]

        # guarda os botões do teclado para poder bloquear/desbloquear depois
        self.botoes_teclado = []

        for linha, lista in enumerate(teclas):
            for coluna, texto in enumerate(lista):
                botao = QPushButton(texto)

                # clicar no botão não tira a seleção do campo de texto
                botao.setFocusPolicy(Qt.NoFocus)

                # liga o clique à função que trata a tecla
                botao.clicked.connect(lambda _, t=texto: self.tecla_pressionada(t))

                grade_teclado.addWidget(botao, linha, coluna)
                self.botoes_teclado.append(botao)

        # ---------- botão entrar ----------

        self.botao_entrar = QPushButton("ENTRAR")
        self.botao_entrar.setStyleSheet("background-color: #2563eb; font-weight: bold;")
        self.botao_entrar.setFocusPolicy(Qt.NoFocus)
        self.botao_entrar.clicked.connect(self.entrar)

        # Enter na senha = entrar; Enter no código = pula para a senha
        self.campo_senha.returnPressed.connect(self.entrar)
        self.campo_codigo.returnPressed.connect(self.campo_senha.setFocus)

        # ---------- faixa de status ----------

        self.status = QLabel()
        self.status.setAlignment(Qt.AlignCenter)
        self.definir_status("Aguardando...", COR_NEUTRA)

        # ---------- montagem dos layouts ----------

        coluna_direita = QVBoxLayout()
        coluna_direita.addWidget(titulo)
        coluna_direita.addWidget(rotulo_codigo)
        coluna_direita.addWidget(self.campo_codigo)
        coluna_direita.addWidget(rotulo_senha)
        coluna_direita.addWidget(self.campo_senha)
        coluna_direita.addLayout(grade_teclado)
        coluna_direita.addWidget(self.botao_entrar)

        linha_principal = QHBoxLayout()
        linha_principal.addWidget(self.painel_camera, 3)
        linha_principal.addLayout(coluna_direita, 2)

        layout_geral = QVBoxLayout(self)
        layout_geral.addLayout(linha_principal)
        layout_geral.addWidget(self.status)

        # começa com o cursor no campo código
        self.campo_codigo.setFocus()

    # ================= funções de apoio da tela =================

    def definir_status(self, texto, cor):
        """Muda o texto e a cor de fundo da faixa de status."""
        self.status.setText(texto)
        self.status.setStyleSheet(
            f"font-size: 22px; padding: 12px; font-weight: bold; background-color: {cor};"
        )

    def bloquear_entrada(self, bloquear):
        """Bloqueia (True) ou libera (False) os campos e botões."""
        self.campo_codigo.setEnabled(not bloquear)
        self.campo_senha.setEnabled(not bloquear)
        self.botao_entrar.setEnabled(not bloquear)
        for botao in self.botoes_teclado:
            botao.setEnabled(not bloquear)

    def campo_selecionado(self):
        """Devolve o campo (código ou senha) que está selecionado agora."""
        if self.campo_senha.hasFocus():
            return self.campo_senha
        return self.campo_codigo

    def tecla_pressionada(self, texto):
        """Trata o clique em uma tecla do teclado numérico."""
        campo = self.campo_selecionado()
        if texto == "Limpar":
            campo.clear()
        elif texto == "Apagar":
            campo.backspace()
        else:
            campo.insert(texto)

    def reiniciar_tela(self):
        """Volta a tela ao estado inicial, pronta para o próximo morador."""
        self.campo_codigo.clear()
        self.campo_senha.clear()
        self.bloquear_entrada(False)
        self.painel_camera.setText("Digite seu código e senha")
        self.definir_status("Aguardando...", COR_NEUTRA)
        self.campo_codigo.setFocus()

    # ================= fluxo de acesso =================

    def entrar(self):
        """Passo 1 e 2: confere código e senha; se certos, inicia a verificação facial."""
        codigo = self.campo_codigo.text()
        senha = self.campo_senha.text()

        # campos vazios: só avisa, sem registrar tentativa
        if not codigo or not senha:
            self.definir_status("Preencha código e senha.", COR_AVISO)
            return

        # bloqueia a tela enquanto confere (evita cliques repetidos)
        self.bloquear_entrada(True)

        # confere no banco (a senha só é usada aqui e não é guardada em lugar nenhum)
        situacao, morador_id, nome, assinatura = verificar_credenciais(codigo, senha)

        # apaga a senha do campo imediatamente
        self.campo_senha.clear()

        # código ou senha inválidos: registra, mostra mensagem genérica e reinicia depois
        if situacao == "invalido":
            registrar_acesso(codigo, morador_id, "NEGADO", "código ou senha inválidos")
            self.mostrar_resultado(False, "ACESSO NEGADO: código ou senha inválidos.")
            return

        # sem rosto cadastrado
        if situacao == "sem_rosto":
            registrar_acesso(codigo, morador_id, "NEGADO", "rosto não cadastrado")
            self.mostrar_resultado(False, "ACESSO NEGADO: rosto não cadastrado.")
            return

        # código e senha certos: guarda os dados para a verificação facial
        self.codigo_atual = codigo
        self.morador_id = morador_id
        self.nome = nome
        self.assinatura_salva = assinatura

        # liga a câmera; se falhar, registra e nega
        if not self.painel_camera.ligar():
            registrar_acesso(codigo, morador_id, "NEGADO", "câmera não abriu")
            self.mostrar_resultado(False, "ACESSO NEGADO: câmera indisponível.")
            return

        # zera os controles e começa a contar o tempo
        self.acertos_seguidos = 0
        self.melhor_nota = 0.0
        self.inicio_verificacao = time.time()

        # liga o relógio que analisa os frames
        self.timer_verificacao.start(INTERVALO_ANALISE_MS)
        self.definir_status("Olhe para a câmera...", COR_AVISO)

    def analisar_frame(self):
        """Passo 3: chamado pelo relógio a cada 100 ms durante a verificação facial."""
        # calcula o tempo restante
        restante = TEMPO_LIMITE - (time.time() - self.inicio_verificacao)

        # tempo esgotado: nega
        if restante <= 0:
            self.finalizar_verificacao(False, "tempo esgotado")
            return

        # pega o frame mais recente que o painel leu da câmera
        frame = self.painel_camera.ultimo_frame
        if frame is None:
            return

        # ajusta o detector ao tamanho do frame e procura rostos
        altura, largura = frame.shape[:2]
        self.detector.setInputSize((largura, altura))
        _, rostos = self.detector.detect(frame)

        # só avalia com exatamente UM rosto na frente da câmera
        if rostos is not None and len(rostos) == 1:
            # gera a assinatura do rosto ao vivo e compara com a salva
            assinatura_ao_vivo = gerar_assinatura(self.reconhecedor, frame, rostos[0])
            nota = self.reconhecedor.match(
                self.assinatura_salva, assinatura_ao_vivo, COMPARACAO_COSSENO
            )

            # guarda a maior nota vista
            self.melhor_nota = max(self.melhor_nota, nota)

            # passou no limite: soma acerto; senão, zera a sequência
            if nota >= LIMITE_SEMELHANCA:
                self.acertos_seguidos += 1
            else:
                self.acertos_seguidos = 0
        else:
            # nenhum rosto ou mais de um: zera a sequência
            self.acertos_seguidos = 0

        # mostra o progresso no status
        self.definir_status(
            f"Olhe para a câmera: {self.acertos_seguidos}/{FRAMES_PARA_CONFIRMAR}  ({restante:.0f} s)",
            COR_AVISO,
        )

        # confirmou os frames necessários: libera
        if self.acertos_seguidos >= FRAMES_PARA_CONFIRMAR:
            self.finalizar_verificacao(True, "rosto confirmado")

    def finalizar_verificacao(self, aprovado, motivo):
        """Encerra a verificação facial, registra e mostra o resultado."""
        # para o relógio de análise e desliga a câmera
        self.timer_verificacao.stop()
        self.painel_camera.desligar()

        # registra o resultado com a melhor nota
        resultado = "LIBERADO" if aprovado else "NEGADO"
        registrar_acesso(self.codigo_atual, self.morador_id, resultado, motivo, self.melhor_nota)

        # mostra a mensagem final
        if aprovado:
            self.mostrar_resultado(True, f"ACESSO LIBERADO. Bem-vindo(a), {self.nome}!")
        else:
            self.mostrar_resultado(False, f"ACESSO NEGADO: {motivo}.")

        # apaga da memória os dados do morador desta tentativa
        self.codigo_atual = self.morador_id = self.nome = self.assinatura_salva = None

    def mostrar_resultado(self, aprovado, mensagem):
        """Mostra o resultado em verde ou vermelho e agenda o reinício da tela."""
        self.definir_status(mensagem, COR_LIBERADO if aprovado else COR_NEGADO)

        # depois de alguns segundos, volta ao estado inicial
        QTimer.singleShot(TEMPO_RESULTADO_MS, self.reiniciar_tela)


# este bloco só roda com "python tela_portaria.py"
if __name__ == "__main__":
    app = QApplication(sys.argv)
    tela = TelaPortaria()

    # garante que a câmera seja liberada ao fechar
    app.aboutToQuit.connect(tela.painel_camera.desligar)

    tela.resize(1100, 650)
    tela.show()
    sys.exit(app.exec())
