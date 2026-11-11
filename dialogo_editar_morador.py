# importa as funções de leitura e atualização do morador
from moradores import obter_morador, atualizar_morador

# importa a regra de tamanho mínimo da senha
from regras import TAMANHO_MIN_SENHA_MORADOR

# importa as classes de interface
from PySide6.QtWidgets import (
    QDialog,            # janela de diálogo (abre por cima e trava a de trás)
    QFormLayout,        # formulário: rótulo à esquerda, campo à direita
    QLineEdit,          # campo de digitação
    QLabel,             # texto
    QComboBox,          # lista de opções (Ativo / Inativo)
    QDialogButtonBox,   # botões Salvar / Cancelar
    QVBoxLayout,        # layout vertical
)


class DialogoEditarMorador(QDialog):
    """Formulário de edição de um morador já cadastrado."""

    def __init__(self, codigo, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Editar morador")
        self.setMinimumWidth(440)

        # guarda o código (não editável) e busca os dados atuais no banco
        self.codigo = codigo
        morador = obter_morador(codigo)

        # código: só exibe, não deixa editar
        rotulo_codigo = QLabel(f"<b>{codigo}</b>  (o código não pode ser alterado)")

        # campos já preenchidos com os dados atuais
        self.campo_nome = QLineEdit(morador["nome"])
        self.campo_nome.setMaxLength(100)

        self.campo_bloco = QLineEdit(morador["bloco"] or "")
        self.campo_bloco.setMaxLength(10)

        self.campo_apartamento = QLineEdit(morador["apartamento"])
        self.campo_apartamento.setMaxLength(10)

        # situação: Ativo (índice 0) ou Inativo (índice 1)
        self.campo_situacao = QComboBox()
        self.campo_situacao.addItems(["Ativo", "Inativo"])
        self.campo_situacao.setCurrentIndex(0 if morador["ativo"] else 1)

        # nova senha: opcional; em branco = mantém a atual
        self.campo_senha = QLineEdit()
        self.campo_senha.setEchoMode(QLineEdit.Password)
        self.campo_senha.setPlaceholderText("deixe em branco para manter a atual")
        self.campo_confirmacao = QLineEdit()
        self.campo_confirmacao.setEchoMode(QLineEdit.Password)

        # formulário
        formulario = QFormLayout()
        formulario.addRow("Código:", rotulo_codigo)
        formulario.addRow("Nome completo:", self.campo_nome)
        formulario.addRow("Bloco (opcional):", self.campo_bloco)
        formulario.addRow("Apartamento:", self.campo_apartamento)
        formulario.addRow("Situação:", self.campo_situacao)
        formulario.addRow("Nova senha:", self.campo_senha)
        formulario.addRow("Confirme a nova senha:", self.campo_confirmacao)

        # aviso sobre a situação inativa
        aviso = QLabel("Morador <b>inativo</b> não consegue entrar pela portaria. O histórico é mantido.")
        aviso.setWordWrap(True)
        aviso.setStyleSheet("color: #a3a3a3;")

        # mensagem de erro (vermelha)
        self.erro = QLabel("")
        self.erro.setStyleSheet("color: #f87171;")
        self.erro.setWordWrap(True)

        # botões Salvar / Cancelar
        botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botoes.button(QDialogButtonBox.Save).setText("Salvar")
        botoes.button(QDialogButtonBox.Cancel).setText("Cancelar")
        botoes.accepted.connect(self.salvar)
        botoes.rejected.connect(self.reject)

        # layout geral
        layout = QVBoxLayout(self)
        layout.addLayout(formulario)
        layout.addWidget(aviso)
        layout.addWidget(self.erro)
        layout.addWidget(botoes)

    def salvar(self):
        """Valida os campos; se tudo certo, atualiza e fecha a janela."""
        nome = self.campo_nome.text().strip()
        bloco = self.campo_bloco.text().strip()
        apartamento = self.campo_apartamento.text().strip()
        ativo = self.campo_situacao.currentIndex() == 0   # índice 0 = Ativo
        nova_senha = self.campo_senha.text()

        # validações
        if not nome:
            self.erro.setText("Informe o nome completo.")
            return
        if not apartamento:
            self.erro.setText("Informe o apartamento.")
            return

        # a senha só é validada se o funcionário quis trocar
        if nova_senha:
            if len(nova_senha) < TAMANHO_MIN_SENHA_MORADOR:
                self.erro.setText(f"A nova senha precisa ter pelo menos {TAMANHO_MIN_SENHA_MORADOR} caracteres.")
                return
            if nova_senha != self.campo_confirmacao.text():
                self.erro.setText("As senhas não conferem.")
                return

        # grava (nova_senha vazia vira None = mantém a senha atual)
        atualizar_morador(self.codigo, nome, bloco, apartamento, ativo, nova_senha or None)

        # guarda se a senha foi trocada, para o painel avisar
        self.senha_trocada = bool(nova_senha)
        self.accept()
