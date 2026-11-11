# importa o time para controlar o intervalo entre as amostras
import time

# importa o painel da câmera (ele também resolve o conflito do Qt do OpenCV)
from painel_camera import PainelCamera

# importa do rosto.py as funções e regras já testadas
from rosto import (
    criar_detector,          # YuNet: acha onde está o rosto
    criar_reconhecedor,      # SFace: gera a assinatura
    gerar_assinatura,        # assinatura de um rosto
    media_das_assinaturas,   # média normalizada das amostras
    buscar_morador,          # (id, nome) do morador ativo pelo código
    salvar_assinatura,       # grava a assinatura no banco
    TOTAL_AMOSTRAS,          # 5 amostras
    INTERVALO_AMOSTRAS,      # 0.7 segundo entre amostras
)

# importa a regra do código (4 dígitos)
from regras import DIGITOS_CODIGO_MORADOR, codigo_morador_valido

# importa as classes de interface
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout

# QTimer = relógio; Qt = constantes; QRegularExpression = regra de validação
from PySide6.QtCore import QTimer, Qt, QRegularExpression

# validador do campo código
from PySide6.QtGui import QRegularExpressionValidator

# intervalo, em milissegundos, entre uma análise de frame e outra
INTERVALO_ANALISE_MS = 150

# cores do aviso embaixo da câmera
COR_SUCESSO = "#4ade80"   # verde
COR_ERRO = "#f87171"      # vermelho

# estilo do botão "Iniciar captura": verde quando ligado, cinza quando desligado
ESTILO_BOTAO_CAPTURA = """
    QPushButton { background-color: #15803d; font-weight: bold; }
    QPushButton:disabled { background-color: #2a2a2a; color: #777; }
"""


class AbaRosto(QWidget):
    """Aba do painel para cadastrar (ou refazer) o rosto de um morador."""

    def __init__(self):
        super().__init__()

        # modelos de rosto (criados uma vez só)
        self.detector = criar_detector()
        self.reconhecedor = criar_reconhecedor()

        # dados do morador escolhido e controle da captura
        self.morador_id = None
        self.nome = None
        self.capturando = False
        self.amostras = []
        self.ultima_captura = 0.0

        # relógio que analisa os frames enquanto a câmera está ligada
        self.timer_analise = QTimer(self)
        self.timer_analise.timeout.connect(self.analisar_frame)

        # ---------- lado esquerdo: câmera e aviso logo abaixo ----------
        self.painel_camera = PainelCamera()
        self.painel_camera.setText("Busque um morador pelo código")

        # aviso embaixo da câmera: detecção do rosto e mensagem de sucesso
        self.aviso_rosto = QLabel("")
        self.aviso_rosto.setAlignment(Qt.AlignCenter)

        coluna_camera = QVBoxLayout()
        coluna_camera.addWidget(self.painel_camera)
        coluna_camera.addWidget(self.aviso_rosto)

        # ---------- lado direito: busca e botões ----------

        # campo do código (4 dígitos)
        self.campo_codigo = QLineEdit()
        self.campo_codigo.setPlaceholderText(f"código ({DIGITOS_CODIGO_MORADOR} dígitos)")
        self.campo_codigo.setValidator(
            QRegularExpressionValidator(QRegularExpression(rf"\d{{0,{DIGITOS_CODIGO_MORADOR}}}"))
        )
        self.campo_codigo.returnPressed.connect(self.buscar)

        botao_buscar = QPushButton("Buscar")
        botao_buscar.clicked.connect(self.buscar)

        linha_busca = QHBoxLayout()
        linha_busca.addWidget(self.campo_codigo)
        linha_busca.addWidget(botao_buscar)

        # nome do morador encontrado
        self.rotulo_morador = QLabel("Nenhum morador selecionado.")
        self.rotulo_morador.setWordWrap(True)

        # botão que inicia a captura: cinza enquanto desligado, verde quando liberado
        self.botao_capturar = QPushButton("Iniciar captura")
        self.botao_capturar.setStyleSheet(ESTILO_BOTAO_CAPTURA)
        self.botao_capturar.setEnabled(False)
        self.botao_capturar.clicked.connect(self.iniciar_captura)

        # botão que cancela e desliga a câmera
        self.botao_cancelar = QPushButton("Cancelar")
        self.botao_cancelar.setEnabled(False)
        self.botao_cancelar.clicked.connect(self.cancelar)

        # progresso da captura e mensagens de erro (coluna da direita)
        self.status = QLabel("")
        self.status.setWordWrap(True)

        # instruções fixas
        instrucoes = QLabel(
            "<b>Como fazer:</b><br>"
            "1. Digite o código e clique em Buscar.<br>"
            "2. Peça ao morador para olhar para a câmera.<br>"
            "3. Clique em Iniciar captura.<br>"
            "4. O morador mexe a cabeça devagar (esquerda, direita, cima, baixo).<br><br>"
            "Se o morador já tiver rosto cadastrado, ele será <b>substituído</b>."
        )
        instrucoes.setWordWrap(True)
        instrucoes.setStyleSheet("color: #a3a3a3;")

        coluna_direita = QVBoxLayout()
        coluna_direita.addLayout(linha_busca)
        coluna_direita.addWidget(self.rotulo_morador)
        coluna_direita.addWidget(self.botao_capturar)
        coluna_direita.addWidget(self.botao_cancelar)
        coluna_direita.addWidget(self.status)
        coluna_direita.addWidget(instrucoes)
        coluna_direita.addStretch()

        # ---------- layout geral: câmera à esquerda (peso 3), controles à direita (peso 2) ----------
        layout = QHBoxLayout(self)
        layout.addLayout(coluna_camera, 3)
        layout.addLayout(coluna_direita, 2)

    # ================= apoio =================

    def mostrar_aviso(self, texto, cor):
        """Mostra um aviso embaixo da câmera, na cor indicada."""
        self.aviso_rosto.setText(texto)
        self.aviso_rosto.setStyleSheet(
            f"font-size: 18px; font-weight: bold; padding: 8px; color: {cor};"
        )

    # ================= fluxo =================

    def buscar(self):
        """Procura o morador pelo código e liga a câmera."""
        # se estava capturando outro morador, encerra antes (e limpa avisos antigos)
        self.cancelar()

        codigo = self.campo_codigo.text().strip()

        if not codigo_morador_valido(codigo):
            self.status.setText(f"Digite um código com {DIGITOS_CODIGO_MORADOR} dígitos.")
            return

        morador = buscar_morador(codigo)
        if morador is None:
            self.status.setText("Código não encontrado ou morador inativo.")
            return

        # guarda o morador escolhido
        self.morador_id, self.nome = morador
        self.rotulo_morador.setText(f"Morador: <b>{self.nome}</b> (código {codigo})")

        # liga a câmera e a análise dos frames
        if not self.painel_camera.ligar():
            self.status.setText("Câmera não encontrada.")
            return

        self.timer_analise.start(INTERVALO_ANALISE_MS)
        self.botao_capturar.setEnabled(True)
        self.botao_cancelar.setEnabled(True)
        self.status.setText("Posicione o morador e clique em Iniciar captura.")

    def iniciar_captura(self):
        """Começa a juntar as amostras."""
        self.amostras = []
        self.ultima_captura = 0.0
        self.capturando = True
        self.botao_capturar.setEnabled(False)
        self.status.setText(f"Capturando 0/{TOTAL_AMOSTRAS}... mexa a cabeça devagar.")

    def analisar_frame(self):
        """Chamado pelo relógio: verifica o rosto e, se estiver capturando, guarda amostras."""
        frame = self.painel_camera.ultimo_frame
        if frame is None:
            return

        # procura rostos no frame
        altura, largura = frame.shape[:2]
        self.detector.setInputSize((largura, altura))
        _, rostos = self.detector.detect(frame)
        quantidade = 0 if rostos is None else len(rostos)

        # aviso embaixo do vídeo
        if quantidade == 1:
            self.mostrar_aviso("Rosto detectado", COR_SUCESSO)
        elif quantidade == 0:
            self.mostrar_aviso("Nenhum rosto encontrado", COR_ERRO)
        else:
            self.mostrar_aviso("Apenas UMA pessoa na frente da câmera", COR_ERRO)

        # guarda amostra: capturando + um rosto só + passou o intervalo
        if self.capturando and quantidade == 1 and time.time() - self.ultima_captura >= INTERVALO_AMOSTRAS:
            self.amostras.append(gerar_assinatura(self.reconhecedor, frame, rostos[0]))
            self.ultima_captura = time.time()
            self.status.setText(
                f"Capturando {len(self.amostras)}/{TOTAL_AMOSTRAS}... mexa a cabeça devagar."
            )

            # juntou todas: calcula a média, salva e encerra
            if len(self.amostras) >= TOTAL_AMOSTRAS:
                salvar_assinatura(self.morador_id, media_das_assinaturas(self.amostras))
                nome = self.nome

                # desliga a câmera e limpa o estado
                self.cancelar()

                # mensagem de sucesso em verde, logo abaixo da tela da câmera
                self.mostrar_aviso(f"Rosto de {nome} cadastrado com sucesso!", COR_SUCESSO)

    def cancelar(self):
        """Para tudo, desliga a câmera e limpa o estado (não salva nada)."""
        self.timer_analise.stop()
        self.painel_camera.desligar()
        self.painel_camera.setText("Busque um morador pelo código")
        self.capturando = False
        self.amostras = []
        self.morador_id = None
        self.nome = None
        self.rotulo_morador.setText("Nenhum morador selecionado.")
        self.aviso_rosto.setText("")
        self.botao_capturar.setEnabled(False)
        self.botao_cancelar.setEnabled(False)
        self.status.setText("")
