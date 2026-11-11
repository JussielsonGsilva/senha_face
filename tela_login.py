# importa o sys para passar argumentos ao Qt e encerrar o programa
import sys

# importa as funções de autenticação criadas na etapa 6.9
from autenticacao import (
    verificar_login,         # confere usuário e senha
    gerar_e_enviar_codigo,   # gera o código e envia por e-mail
    verificar_codigo,        # confere o código digitado
    mascarar_email,          # esconde parte do e-mail para mostrar na tela
    DIGITOS_CODIGO,          # quantidade de dígitos do código (6)
)

# importa as classes de interface
from PySide6.QtWidgets import (
    QApplication,     # a aplicação Qt
    QWidget,          # janela/área genérica
    QLabel,           # texto
    QLineEdit,        # campo de digitação
    QPushButton,      # botão
    QVBoxLayout,      # layout vertical
    QHBoxLayout,      # layout horizontal
    QStackedWidget,   # "pilha" de páginas: mostra uma de cada vez
    QMessageBox,      # caixa de mensagem (usada só no teste)
)

# Qt = constantes; QTimer = relógio; Signal = aviso que outras partes podem escutar;
# QRegularExpression = regra de validação
from PySide6.QtCore import Qt, QTimer, Signal, QRegularExpression

# QRegularExpressionValidator = só deixa digitar o que segue a regra; QApplication já importado acima
from PySide6.QtGui import QRegularExpressionValidator

# segundos de espera antes de liberar o botão "Reenviar código"
ESPERA_REENVIO_SEGUNDOS = 30


class TelaLogin(QWidget):
    """Tela de login do funcionário com 2FA por e-mail."""

    # sinal emitido quando o login termina com sucesso; leva o dicionário do funcionário
    login_aprovado = Signal(dict)

    def __init__(self):
        # inicializa a QWidget (classe "mãe")
        super().__init__()

        # título e tamanho da janela
        self.setWindowTitle("Portaria - Login do funcionário")
        self.resize(420, 380)

        # mesmo estilo escuro da tela da portaria
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #f0f0f0; font-size: 16px; }
            QLineEdit { background-color: #2d2d2d; border: 2px solid #555; border-radius: 6px; padding: 8px; font-size: 18px; }
            QLineEdit:focus { border: 2px solid #3b82f6; }
            QPushButton { background-color: #333; border: 1px solid #555; border-radius: 8px; padding: 10px; }
            QPushButton:pressed { background-color: #555; }
            QPushButton:disabled { color: #777; }
        """)

        # funcionário que passou na senha e aguarda o código (preenchido depois)
        self.funcionario = None

        # segundos restantes para liberar o reenvio
        self.segundos_reenvio = 0

        # relógio que conta a espera do reenvio, de 1 em 1 segundo
        self.timer_reenvio = QTimer(self)
        self.timer_reenvio.timeout.connect(self.contar_reenvio)

        # cria a pilha de páginas
        self.paginas = QStackedWidget()
        self.paginas.addWidget(self.criar_pagina_senha())    # página 0
        self.paginas.addWidget(self.criar_pagina_codigo())   # página 1

        # mensagem de status embaixo das páginas
        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setWordWrap(True)

        # layout geral: título, páginas e status
        titulo = QLabel("PAINEL DA PORTARIA")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 22px; font-weight: bold;")

        layout = QVBoxLayout(self)
        layout.addWidget(titulo)
        layout.addWidget(self.paginas)
        layout.addWidget(self.status)

    # ================= montagem das páginas =================

    def criar_pagina_senha(self):
        """Página 1: usuário e senha."""
        pagina = QWidget()

        # campo usuário
        self.campo_usuario = QLineEdit()
        self.campo_usuario.setPlaceholderText("usuário")

        # campo senha (mostra bolinhas)
        self.campo_senha = QLineEdit()
        self.campo_senha.setPlaceholderText("senha")
        self.campo_senha.setEchoMode(QLineEdit.Password)

        # botão entrar
        self.botao_entrar = QPushButton("Entrar")
        self.botao_entrar.setStyleSheet("background-color: #2563eb; font-weight: bold;")
        self.botao_entrar.clicked.connect(self.entrar)

        # Enter no usuário pula para a senha; Enter na senha = entrar
        self.campo_usuario.returnPressed.connect(self.campo_senha.setFocus)
        self.campo_senha.returnPressed.connect(self.entrar)

        # organiza de cima para baixo
        layout = QVBoxLayout(pagina)
        layout.addWidget(QLabel("Usuário:"))
        layout.addWidget(self.campo_usuario)
        layout.addWidget(QLabel("Senha:"))
        layout.addWidget(self.campo_senha)
        layout.addWidget(self.botao_entrar)
        layout.addStretch()   # empurra tudo para cima

        return pagina

    def criar_pagina_codigo(self):
        """Página 2: código 2FA recebido por e-mail."""
        pagina = QWidget()

        # texto que avisa para qual e-mail o código foi enviado
        self.aviso_email = QLabel("")
        self.aviso_email.setWordWrap(True)

        # campo do código: só números, exatamente 6 dígitos no máximo
        self.campo_codigo = QLineEdit()
        self.campo_codigo.setPlaceholderText("000000")
        self.campo_codigo.setAlignment(Qt.AlignCenter)
        self.campo_codigo.setStyleSheet("font-size: 28px; letter-spacing: 8px;")
        self.campo_codigo.setValidator(
            QRegularExpressionValidator(QRegularExpression(rf"\d{{0,{DIGITOS_CODIGO}}}"))
        )
        self.campo_codigo.returnPressed.connect(self.confirmar_codigo)

        # botão confirmar
        self.botao_confirmar = QPushButton("Confirmar")
        self.botao_confirmar.setStyleSheet("background-color: #2563eb; font-weight: bold;")
        self.botao_confirmar.clicked.connect(self.confirmar_codigo)

        # botões reenviar e voltar, lado a lado
        self.botao_reenviar = QPushButton("Reenviar código")
        self.botao_reenviar.clicked.connect(self.reenviar_codigo)

        botao_voltar = QPushButton("Voltar")
        botao_voltar.clicked.connect(self.voltar)

        linha_botoes = QHBoxLayout()
        linha_botoes.addWidget(self.botao_reenviar)
        linha_botoes.addWidget(botao_voltar)

        # organiza de cima para baixo
        layout = QVBoxLayout(pagina)
        layout.addWidget(self.aviso_email)
        layout.addWidget(self.campo_codigo)
        layout.addWidget(self.botao_confirmar)
        layout.addLayout(linha_botoes)
        layout.addStretch()

        return pagina

    # ================= funções de apoio =================

    def mostrar_status(self, texto, erro=False):
        """Mostra uma mensagem embaixo; vermelha se for erro."""
        self.status.setText(texto)
        self.status.setStyleSheet("color: #f87171;" if erro else "color: #a3a3a3;")

    def enviar_codigo(self):
        """Gera e envia o código; inicia a contagem do reenvio. Devolve True se enviou."""
        # avisa que está enviando e força a tela a se redesenhar antes do envio (que leva ~1 s)
        self.mostrar_status("Enviando código por e-mail...")
        QApplication.processEvents()

        if not gerar_e_enviar_codigo(self.funcionario):
            self.mostrar_status("Não foi possível enviar o e-mail. Tente novamente.", erro=True)
            return False

        # bloqueia o reenvio por alguns segundos
        self.segundos_reenvio = ESPERA_REENVIO_SEGUNDOS
        self.botao_reenviar.setEnabled(False)
        self.timer_reenvio.start(1000)
        self.contar_reenvio()
        return True

    def contar_reenvio(self):
        """Chamado a cada segundo: atualiza o botão reenviar."""
        if self.segundos_reenvio <= 0:
            # acabou a espera: libera o botão
            self.timer_reenvio.stop()
            self.botao_reenviar.setText("Reenviar código")
            self.botao_reenviar.setEnabled(True)
            return

        # mostra a contagem no próprio botão
        self.botao_reenviar.setText(f"Reenviar ({self.segundos_reenvio}s)")
        self.segundos_reenvio -= 1

    # ================= fluxo do login =================

    def entrar(self):
        """Página 1: confere usuário e senha e envia o código."""
        usuario = self.campo_usuario.text().strip().lower()
        senha = self.campo_senha.text()

        if not usuario or not senha:
            self.mostrar_status("Preencha usuário e senha.", erro=True)
            return

        # confere no banco e já apaga a senha do campo
        self.funcionario = verificar_login(usuario, senha)
        self.campo_senha.clear()

        if self.funcionario is None:
            self.mostrar_status("Usuário ou senha inválidos.", erro=True)
            return

        # envia o código; se falhar, fica na página 1
        if not self.enviar_codigo():
            self.funcionario = None
            return

        # vai para a página 2
        self.aviso_email.setText(
            f"Enviamos um código de {DIGITOS_CODIGO} dígitos para "
            f"{mascarar_email(self.funcionario['email'])}. Ele vale por 5 minutos."
        )
        self.campo_codigo.clear()
        self.paginas.setCurrentIndex(1)
        self.mostrar_status("")
        self.campo_codigo.setFocus()

    def confirmar_codigo(self):
        """Página 2: confere o código digitado."""
        codigo = self.campo_codigo.text().strip()

        if len(codigo) != DIGITOS_CODIGO:
            self.mostrar_status(f"Digite os {DIGITOS_CODIGO} dígitos.", erro=True)
            return

        situacao = verificar_codigo(self.funcionario["id"], codigo)
        self.campo_codigo.clear()

        if situacao == "ok":
            # login completo: avisa quem estiver escutando e reinicia a tela
            funcionario = self.funcionario
            self.voltar()
            self.login_aprovado.emit(funcionario)
        elif situacao == "incorreto":
            self.mostrar_status("Código incorreto. Tente novamente.", erro=True)
        elif situacao == "bloqueado":
            self.mostrar_status("Muitas tentativas. Peça um novo código.", erro=True)
        else:  # expirado
            self.mostrar_status("Código expirado ou já usado. Peça um novo código.", erro=True)

    def reenviar_codigo(self):
        """Página 2: envia um código novo (o anterior deixa de valer)."""
        if self.enviar_codigo():
            self.mostrar_status("Novo código enviado. O anterior não vale mais.")
            self.campo_codigo.setFocus()

    def voltar(self):
        """Volta para a página 1 e limpa tudo."""
        self.timer_reenvio.stop()
        self.funcionario = None
        self.campo_usuario.clear()
        self.campo_senha.clear()
        self.campo_codigo.clear()
        self.mostrar_status("")
        self.paginas.setCurrentIndex(0)
        self.campo_usuario.setFocus()


# este bloco só roda com "python tela_login.py" (teste)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    tela = TelaLogin()

    # no teste, ao aprovar o login, só mostra uma mensagem de boas-vindas
    tela.login_aprovado.connect(
        lambda f: QMessageBox.information(tela, "Login aprovado", f"Bem-vindo(a), {f['nome']}!")
    )

    tela.show()
    sys.exit(app.exec())
