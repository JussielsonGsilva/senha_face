# importa o sys para passar argumentos ao Qt e encerrar o programa
import sys

# importa o time para controlar os tempos limite
import time

# importa o painel da câmera PRIMEIRO: ele remove o conflito entre o Qt do OpenCV e o PySide6
from painel_camera import PainelCamera

# importa do acesso.py as funções e regras já testadas
from acesso import (
    verificar_credenciais,   # confere bloqueio, código e senha
    registrar_acesso,        # grava a tentativa na tabela acessos
    minutos_de_espera,       # converte segundos de bloqueio em minutos
    LIMITE_SEMELHANCA,       # nota mínima (0.5)
    FRAMES_PARA_CONFIRMAR,   # frames seguidos aprovados (5)
    TEMPO_LIMITE,            # segundos para reconhecer o rosto (10)
    COMPARACAO_COSSENO,      # tipo de comparação do SFace
)

# importa a prova de vida (desafio de movimento)
from vivacidade import (
    sortear_desafio,         # ordem sorteada dos movimentos
    girou_para,              # confere se virou para o lado pedido
    esta_de_frente,          # confere se voltou de frente
    TEXTO_DO_LADO,           # "ESQUERDA" / "DIREITA"
    FRAMES_GIRO,             # frames seguidos de giro (3)
    FRAMES_CONFIRMACAO,      # frames seguidos na confirmação final (3)
    TEMPO_DESAFIO,           # segundos para desafio + confirmação (12)
    MAX_FRAMES_SEM_ROSTO,    # tolerância de frames sem rosto (5)
)

# importa o comando de abrir a porta pela ESP32
from fechadura import abrir_porta

# importa as regras centralizadas
from regras import DIGITOS_CODIGO_MORADOR, MOTIVO_CREDENCIAIS_INVALIDAS, MOTIVO_BLOQUEADO

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
COR_DESAFIO = "#1d4ed8"
COR_LIBERADO = "#15803d"
COR_NEGADO = "#b91c1c"
COR_ALERTA = "#c2410c"   # laranja: liberado, mas a porta não abriu

# fases da verificação facial
FASE_ROSTO = "rosto"              # 1. reconhecer o rosto
FASE_DESAFIO = "desafio"          # 2. virar o rosto para os lados sorteados
FASE_CONFIRMACAO = "confirmacao"  # 3. voltar de frente e ser reconhecido de novo


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
        self.detector = criar_detector()
        self.reconhecedor = criar_reconhecedor()

        # ---------- dados da verificação em andamento ----------
        self.codigo_atual = None
        self.morador_id = None
        self.nome = None
        self.assinatura_salva = None
        self.melhor_nota = 0.0

        # controle das fases
        self.fase = None
        self.inicio_fase = 0.0
        self.acertos_seguidos = 0
        self.passos_desafio = []
        self.passo_atual = 0
        self.frames_sem_rosto = 0

        # relógio que analisa os frames durante a verificação facial
        self.timer_verificacao = QTimer(self)
        self.timer_verificacao.timeout.connect(self.analisar_frame)

        # ---------- lado esquerdo: câmera ----------
        self.painel_camera = PainelCamera()
        self.painel_camera.setText("Digite seu código e senha")

        # ---------- lado direito: título ----------
        titulo = QLabel("CONTROLE DE ACESSO")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 26px; font-weight: bold;")

        # ---------- campo código: só números, no máximo 4 dígitos (regras.py) ----------
        rotulo_codigo = QLabel("Código:")
        self.campo_codigo = QLineEdit()
        self.campo_codigo.setValidator(
            QRegularExpressionValidator(QRegularExpression(rf"\d{{0,{DIGITOS_CODIGO_MORADOR}}}"))
        )

        # ---------- campo senha ----------
        rotulo_senha = QLabel("Senha:")
        self.campo_senha = QLineEdit()
        self.campo_senha.setEchoMode(QLineEdit.Password)   # bolinhas no lugar dos caracteres
        self.campo_senha.setMaxLength(64)

        # ---------- teclado numérico ----------
        grade_teclado = QGridLayout()
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
                botao.setFocusPolicy(Qt.NoFocus)   # não tira a seleção do campo
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
        self.status.setWordWrap(True)
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

    def mudar_fase(self, fase):
        """Troca de fase e zera os contadores da fase nova."""
        self.fase = fase
        self.acertos_seguidos = 0
        self.frames_sem_rosto = 0

    # ================= fluxo de acesso =================

    def entrar(self):
        """Passo 1 e 2: confere bloqueio, código e senha; se certos, inicia a verificação facial."""
        codigo = self.campo_codigo.text()
        senha = self.campo_senha.text()

        # campos vazios: só avisa, sem registrar tentativa
        if not codigo or not senha:
            self.definir_status("Preencha código e senha.", COR_AVISO)
            return

        # bloqueia a tela enquanto confere (evita cliques repetidos)
        self.bloquear_entrada(True)

        # confere no banco (a senha só é usada aqui e não é guardada em lugar nenhum)
        situacao, morador_id, nome, extra = verificar_credenciais(codigo, senha)

        # apaga a senha do campo imediatamente
        self.campo_senha.clear()

        # muitas tentativas: registra e mostra quanto tempo falta (extra = segundos)
        if situacao == "bloqueado":
            registrar_acesso(codigo, None, "NEGADO", MOTIVO_BLOQUEADO)
            self.mostrar_resultado(COR_NEGADO, f"Muitas tentativas. Aguarde {minutos_de_espera(extra)} min.")
            return

        # código ou senha inválidos
        if situacao == "invalido":
            registrar_acesso(codigo, morador_id, "NEGADO", MOTIVO_CREDENCIAIS_INVALIDAS)
            self.mostrar_resultado(COR_NEGADO, "ACESSO NEGADO: código ou senha inválidos.")
            return

        # sem rosto cadastrado
        if situacao == "sem_rosto":
            registrar_acesso(codigo, morador_id, "NEGADO", "rosto não cadastrado")
            self.mostrar_resultado(COR_NEGADO, "ACESSO NEGADO: rosto não cadastrado.")
            return

        # código e senha certos: guarda os dados para a verificação facial (extra = assinatura)
        self.codigo_atual = codigo
        self.morador_id = morador_id
        self.nome = nome
        self.assinatura_salva = extra
        self.melhor_nota = 0.0

        # liga a câmera; se falhar, registra e nega
        if not self.painel_camera.ligar():
            registrar_acesso(codigo, morador_id, "NEGADO", "câmera não abriu")
            self.mostrar_resultado(COR_NEGADO, "ACESSO NEGADO: câmera indisponível.")
            return

        # começa pela fase 1 (reconhecer o rosto)
        self.mudar_fase(FASE_ROSTO)
        self.inicio_fase = time.time()
        self.timer_verificacao.start(INTERVALO_ANALISE_MS)
        self.definir_status("Olhe para a câmera...", COR_AVISO)

    def nota_do_rosto(self, frame, rosto):
        """Gera a assinatura do rosto ao vivo, compara com a salva e devolve a nota."""
        assinatura_ao_vivo = gerar_assinatura(self.reconhecedor, frame, rosto)
        nota = self.reconhecedor.match(self.assinatura_salva, assinatura_ao_vivo, COMPARACAO_COSSENO)
        self.melhor_nota = max(self.melhor_nota, nota)
        return nota

    def analisar_frame(self):
        """Chamado pelo relógio a cada 100 ms: trata a fase atual."""
        # pega o frame mais recente que o painel leu da câmera
        frame = self.painel_camera.ultimo_frame
        if frame is None:
            return

        # procura rostos
        altura, largura = frame.shape[:2]
        self.detector.setInputSize((largura, altura))
        _, rostos = self.detector.detect(frame)

        # há exatamente um rosto?
        um_rosto = rostos is not None and len(rostos) == 1
        rosto = rostos[0] if um_rosto else None

        if self.fase == FASE_ROSTO:
            self.fase_rosto(frame, rosto)
        else:
            self.fase_desafio_e_confirmacao(frame, rosto)

    def fase_rosto(self, frame, rosto):
        """Fase 1: reconhecer o rosto do morador."""
        restante = TEMPO_LIMITE - (time.time() - self.inicio_fase)
        if restante <= 0:
            self.finalizar_verificacao(False, "tempo esgotado")
            return

        # conta frames seguidos com o rosto certo
        if rosto is not None and self.nota_do_rosto(frame, rosto) >= LIMITE_SEMELHANCA:
            self.acertos_seguidos += 1
        else:
            self.acertos_seguidos = 0

        self.definir_status(
            f"Olhe para a câmera: {self.acertos_seguidos}/{FRAMES_PARA_CONFIRMAR}  ({restante:.0f} s)",
            COR_AVISO,
        )

        # reconheceu: sorteia o desafio e vai para a fase 2
        if self.acertos_seguidos >= FRAMES_PARA_CONFIRMAR:
            self.passos_desafio = sortear_desafio()
            self.passo_atual = 0
            self.inicio_fase = time.time()
            self.mudar_fase(FASE_DESAFIO)

    def fase_desafio_e_confirmacao(self, frame, rosto):
        """Fases 2 e 3: virar o rosto para os lados sorteados e voltar de frente."""
        restante = TEMPO_DESAFIO - (time.time() - self.inicio_fase)
        if restante <= 0:
            self.finalizar_verificacao(False, "prova de vida não concluída")
            return

        # o rosto precisa continuar presente (um só) durante toda a prova
        if rosto is None:
            self.frames_sem_rosto += 1
            if self.frames_sem_rosto > MAX_FRAMES_SEM_ROSTO:
                self.finalizar_verificacao(False, "rosto perdido durante a prova de vida")
            return
        self.frames_sem_rosto = 0

        if self.fase == FASE_DESAFIO:
            # lado pedido agora
            lado = self.passos_desafio[self.passo_atual]

            # conta frames seguidos com o rosto virado para o lado certo
            if girou_para(rosto, lado):
                self.acertos_seguidos += 1
            else:
                self.acertos_seguidos = 0

            self.definir_status(
                f"Vire o rosto para a sua {TEXTO_DO_LADO[lado]}  "
                f"({self.passo_atual + 1}/{len(self.passos_desafio)})  ({restante:.0f} s)",
                COR_DESAFIO,
            )

            # cumpriu este passo: vai para o próximo ou para a confirmação final
            if self.acertos_seguidos >= FRAMES_GIRO:
                self.passo_atual += 1
                self.acertos_seguidos = 0
                if self.passo_atual >= len(self.passos_desafio):
                    self.mudar_fase(FASE_CONFIRMACAO)

        else:  # FASE_CONFIRMACAO
            # precisa estar de frente E ser reconhecido de novo como o morador
            if esta_de_frente(rosto) and self.nota_do_rosto(frame, rosto) >= LIMITE_SEMELHANCA:
                self.acertos_seguidos += 1
            else:
                self.acertos_seguidos = 0

            self.definir_status(
                f"Agora olhe de FRENTE para a câmera  ({restante:.0f} s)",
                COR_DESAFIO,
            )

            if self.acertos_seguidos >= FRAMES_CONFIRMACAO:
                self.finalizar_verificacao(True, "rosto e prova de vida confirmados")

    def finalizar_verificacao(self, aprovado, motivo):
        """Encerra a verificação facial; se aprovado, manda abrir a porta; registra e mostra o resultado."""
        self.timer_verificacao.stop()
        self.painel_camera.desligar()

        if aprovado:
            # mostra "abrindo" enquanto fala com a ESP32 (pode levar até 3 s se ela não responder)
            self.definir_status("Abrindo a porta...", COR_LIBERADO)
            QApplication.processEvents()

            # manda a ESP32 acionar a fechadura
            porta_abriu, _ = abrir_porta()

            if porta_abriu is False:
                # morador reconhecido, mas a fechadura falhou: registra o aviso e pede ajuda ao porteiro
                registrar_acesso(self.codigo_atual, self.morador_id, "LIBERADO",
                                 f"{motivo} (fechadura não respondeu)", self.melhor_nota)
                self.mostrar_resultado(
                    COR_ALERTA,
                    f"ACESSO LIBERADO, mas a porta não abriu. Chame o porteiro.",
                )
            else:
                # porta aberta (True) ou sistema sem fechadura configurada (None)
                registrar_acesso(self.codigo_atual, self.morador_id, "LIBERADO", motivo, self.melhor_nota)
                self.mostrar_resultado(COR_LIBERADO, f"ACESSO LIBERADO. Bem-vindo(a), {self.nome}!")
        else:
            registrar_acesso(self.codigo_atual, self.morador_id, "NEGADO", motivo, self.melhor_nota)
            self.mostrar_resultado(COR_NEGADO, f"ACESSO NEGADO: {motivo}.")

        # apaga da memória os dados do morador desta tentativa
        self.codigo_atual = self.morador_id = self.nome = self.assinatura_salva = None
        self.fase = None

    def mostrar_resultado(self, cor, mensagem):
        """Mostra o resultado na cor indicada e agenda o reinício da tela."""
        self.definir_status(mensagem, cor)
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
