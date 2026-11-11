# importa as funções de cadastro de morador criadas na etapa 2
from moradores import codigo_existe, cadastrar_morador

# importa as funções de veículo
from veiculos import normalizar_placa, placa_valida, placa_existe, cadastrar_veiculo

# importa as regras centralizadas (4 dígitos no código, senha com 8 ou mais)
from regras import DIGITOS_CODIGO_MORADOR, TAMANHO_MIN_SENHA_MORADOR, codigo_morador_valido

# importa as classes de interface
from PySide6.QtWidgets import (
    QDialog,            # janela de diálogo (abre por cima e trava a de trás)
    QFormLayout,        # layout de formulário: rótulo à esquerda, campo à direita
    QLineEdit,          # campo de digitação
    QLabel,             # texto
    QDialogButtonBox,   # botões padrão (Salvar / Cancelar)
    QVBoxLayout,        # layout vertical
)

# QRegularExpression = regra de validação
from PySide6.QtCore import QRegularExpression

# validador que só deixa digitar o que segue a regra
from PySide6.QtGui import QRegularExpressionValidator


def criar_botoes(dialogo):
    """Cria os botões Salvar/Cancelar padrão, já ligados ao diálogo."""
    botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
    botoes.button(QDialogButtonBox.Save).setText("Salvar")
    botoes.button(QDialogButtonBox.Cancel).setText("Cancelar")
    botoes.accepted.connect(dialogo.salvar)   # Salvar -> valida e grava
    botoes.rejected.connect(dialogo.reject)   # Cancelar -> fecha sem gravar
    return botoes


def criar_rotulo_erro():
    """Cria o texto vermelho de erro usado nos formulários."""
    erro = QLabel("")
    erro.setStyleSheet("color: #f87171;")
    erro.setWordWrap(True)
    return erro


# =====================================================================
# NOVO MORADOR
# =====================================================================
class DialogoMorador(QDialog):
    """Formulário de cadastro de novo morador."""

    def __init__(self, parent=None):
        # inicializa o QDialog; parent = janela "dona" (o painel)
        super().__init__(parent)

        # título e largura mínima
        self.setWindowTitle("Novo morador")
        self.setMinimumWidth(420)

        # código: só números, no máximo a quantidade de dígitos da regra (4)
        self.campo_codigo = QLineEdit()
        self.campo_codigo.setValidator(
            QRegularExpressionValidator(QRegularExpression(rf"\d{{0,{DIGITOS_CODIGO_MORADOR}}}"))
        )
        self.campo_codigo.setPlaceholderText(f"{DIGITOS_CODIGO_MORADOR} dígitos")

        # nome completo (até 100, igual à coluna do banco)
        self.campo_nome = QLineEdit()
        self.campo_nome.setMaxLength(100)

        # bloco (opcional) e apartamento (até 10, igual ao banco)
        self.campo_bloco = QLineEdit()
        self.campo_bloco.setMaxLength(10)
        self.campo_apartamento = QLineEdit()
        self.campo_apartamento.setMaxLength(10)

        # senha e confirmação (bolinhas)
        self.campo_senha = QLineEdit()
        self.campo_senha.setEchoMode(QLineEdit.Password)
        self.campo_senha.setPlaceholderText(f"mínimo {TAMANHO_MIN_SENHA_MORADOR} caracteres")
        self.campo_confirmacao = QLineEdit()
        self.campo_confirmacao.setEchoMode(QLineEdit.Password)

        # formulário
        formulario = QFormLayout()
        formulario.addRow("Código de acesso:", self.campo_codigo)
        formulario.addRow("Nome completo:", self.campo_nome)
        formulario.addRow("Bloco (opcional):", self.campo_bloco)
        formulario.addRow("Apartamento:", self.campo_apartamento)
        formulario.addRow("Senha:", self.campo_senha)
        formulario.addRow("Confirme a senha:", self.campo_confirmacao)

        # erro e botões
        self.erro = criar_rotulo_erro()
        layout = QVBoxLayout(self)
        layout.addLayout(formulario)
        layout.addWidget(self.erro)
        layout.addWidget(criar_botoes(self))

    def salvar(self):
        """Valida os campos; se tudo certo, grava e fecha a janela."""
        codigo = self.campo_codigo.text().strip()
        nome = self.campo_nome.text().strip()
        bloco = self.campo_bloco.text().strip()
        apartamento = self.campo_apartamento.text().strip()
        senha = self.campo_senha.text()

        # validações (a primeira que falhar mostra o erro)
        if not codigo_morador_valido(codigo):
            self.erro.setText(f"O código precisa ter exatamente {DIGITOS_CODIGO_MORADOR} dígitos.")
            return
        if not nome:
            self.erro.setText("Informe o nome completo.")
            return
        if not apartamento:
            self.erro.setText("Informe o apartamento.")
            return
        if len(senha) < TAMANHO_MIN_SENHA_MORADOR:
            self.erro.setText(f"A senha precisa ter pelo menos {TAMANHO_MIN_SENHA_MORADOR} caracteres.")
            return
        if senha != self.campo_confirmacao.text():
            self.erro.setText("As senhas não conferem.")
            return
        if codigo_existe(codigo):
            self.erro.setText(f"O código {codigo} já está em uso. Escolha outro.")
            return

        # grava (a senha vira hash bcrypt dentro de cadastrar_morador)
        novo_id = cadastrar_morador(codigo, nome, bloco, apartamento, senha)
        if novo_id is None:
            self.erro.setText(f"O código {codigo} acabou de ser usado. Escolha outro.")
            return

        self.novo_id = novo_id
        self.accept()


# =====================================================================
# NOVO VEÍCULO
# =====================================================================
class DialogoVeiculo(QDialog):
    """Formulário de cadastro de veículo para um morador já escolhido."""

    def __init__(self, codigo_morador, nome_morador, parent=None):
        super().__init__(parent)

        # guarda o código do morador dono do veículo
        self.codigo_morador = codigo_morador

        self.setWindowTitle("Novo veículo")
        self.setMinimumWidth(420)

        # mostra de quem é o veículo (não editável)
        dono = QLabel(f"<b>{nome_morador}</b> (código {codigo_morador})")

        # modelo e cor (tamanhos iguais às colunas do banco)
        self.campo_modelo = QLineEdit()
        self.campo_modelo.setMaxLength(50)
        self.campo_modelo.setPlaceholderText("ex.: Onix, CG 160")
        self.campo_cor = QLineEdit()
        self.campo_cor.setMaxLength(30)
        self.campo_cor.setPlaceholderText("ex.: Prata")

        # placa: só letras, números e hífen, até 8 caracteres (ABC-1D23)
        self.campo_placa = QLineEdit()
        self.campo_placa.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"[A-Za-z0-9-]{0,8}"))
        )
        self.campo_placa.setPlaceholderText("ABC1D23 ou ABC-1234")

        # formulário
        formulario = QFormLayout()
        formulario.addRow("Morador:", dono)
        formulario.addRow("Modelo:", self.campo_modelo)
        formulario.addRow("Cor:", self.campo_cor)
        formulario.addRow("Placa:", self.campo_placa)

        # erro e botões
        self.erro = criar_rotulo_erro()
        layout = QVBoxLayout(self)
        layout.addLayout(formulario)
        layout.addWidget(self.erro)
        layout.addWidget(criar_botoes(self))

    def salvar(self):
        """Valida os campos; se tudo certo, grava e fecha a janela."""
        modelo = self.campo_modelo.text().strip()
        cor = self.campo_cor.text().strip()

        # deixa a placa no formato do banco (sem hífen, maiúsculas)
        placa = normalizar_placa(self.campo_placa.text())

        # validações
        if not modelo:
            self.erro.setText("Informe o modelo do veículo.")
            return
        if not cor:
            self.erro.setText("Informe a cor do veículo.")
            return
        if not placa_valida(placa):
            self.erro.setText("Placa inválida. Use o padrão ABC1234 (antigo) ou ABC1D23 (Mercosul).")
            return
        if placa_existe(placa):
            self.erro.setText(f"A placa {placa} já está cadastrada.")
            return

        # grava
        novo_id = cadastrar_veiculo(self.codigo_morador, modelo, cor, placa)
        if novo_id is None:
            self.erro.setText("Não foi possível salvar: placa repetida ou morador não encontrado.")
            return

        self.novo_id = novo_id
        self.accept()
