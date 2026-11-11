# importa a conexão com o banco
from banco import conectar

# importa as classes de interface
from PySide6.QtWidgets import (
    QDialog,        # janela de diálogo (abre por cima e trava a de trás)
    QLabel,         # texto
    QLineEdit,      # campo de digitação
    QPushButton,    # botão
    QVBoxLayout,    # layout vertical
    QHBoxLayout,    # layout horizontal
)


def resumo_exclusao(codigo):
    """Junta o que será apagado e o que será mantido, para mostrar antes de excluir.
    Devolve um dicionário, ou None se o morador não existir."""
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    # dados do morador e se ele tem rosto cadastrado
    cursor.execute(
        """
        SELECT id, nome, bloco, apartamento,
               (rosto_embedding IS NOT NULL) AS tem_rosto
        FROM moradores WHERE codigo = %s
        """,
        (codigo,),
    )
    morador = cursor.fetchone()

    if morador is None:
        cursor.close()
        conexao.close()
        return None

    # quantos veículos serão apagados junto
    cursor.execute("SELECT COUNT(*) AS total FROM veiculos WHERE morador_id = %s", (morador["id"],))
    morador["veiculos"] = cursor.fetchone()["total"]

    # quantos registros de acesso ficarão anônimos
    cursor.execute("SELECT COUNT(*) AS total FROM acessos WHERE morador_id = %s", (morador["id"],))
    morador["acessos"] = cursor.fetchone()["total"]

    cursor.close()
    conexao.close()
    return morador


def excluir_morador(codigo):
    """Apaga o morador. O banco cuida do resto:
    veículos -> apagados (ON DELETE CASCADE)
    acessos  -> mantidos com morador_id NULL (ON DELETE SET NULL)
    Devolve True se apagou."""
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("DELETE FROM moradores WHERE codigo = %s", (codigo,))
    conexao.commit()

    # rowcount = quantas linhas foram apagadas (1 se deu certo)
    apagou = cursor.rowcount == 1

    cursor.close()
    conexao.close()
    return apagou


class DialogoExcluirMorador(QDialog):
    """Confirmação de exclusão: mostra o impacto e exige digitar o código."""

    def __init__(self, codigo, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Excluir morador")
        self.setMinimumWidth(460)

        # guarda o código e busca o resumo do que será apagado
        self.codigo = codigo
        resumo = resumo_exclusao(codigo)

        # monta o local (bloco/apartamento) para exibir
        local = f"Bloco {resumo['bloco']} - Apto {resumo['apartamento']}" if resumo["bloco"] \
            else f"Apto {resumo['apartamento']}"

        # texto explicando o impacto da exclusão
        texto = QLabel(
            f"<b>Atenção: esta ação não pode ser desfeita.</b><br><br>"
            f"Morador: <b>{resumo['nome']}</b> ({local})<br>"
            f"Código: <b>{codigo}</b><br><br>"
            f"<b>Será apagado:</b><br>"
            f"• cadastro e senha<br>"
            f"• rosto cadastrado: {'sim' if resumo['tem_rosto'] else 'não possui'}<br>"
            f"• veículos: {resumo['veiculos']}<br><br>"
            f"<b>Será mantido (sem identificação):</b><br>"
            f"• {resumo['acessos']} registro(s) no histórico de acessos"
        )
        texto.setWordWrap(True)

        # instrução e campo para digitar o código
        instrucao = QLabel(f"Para confirmar, digite o código <b>{codigo}</b>:")
        self.campo_confirmacao = QLineEdit()

        # a cada letra digitada, confere se o botão Excluir pode ser liberado
        self.campo_confirmacao.textChanged.connect(self.conferir_confirmacao)

        # mensagem de erro (vermelha)
        self.erro = QLabel("")
        self.erro.setStyleSheet("color: #f87171;")

        # botão Excluir (vermelho) começa DESLIGADO
        self.botao_excluir = QPushButton("Excluir definitivamente")
        self.botao_excluir.setStyleSheet("background-color: #b91c1c; font-weight: bold;")
        self.botao_excluir.setEnabled(False)
        self.botao_excluir.clicked.connect(self.excluir)

        # botão Cancelar
        botao_cancelar = QPushButton("Cancelar")
        botao_cancelar.clicked.connect(self.reject)

        linha_botoes = QHBoxLayout()
        linha_botoes.addStretch()
        linha_botoes.addWidget(botao_cancelar)
        linha_botoes.addWidget(self.botao_excluir)

        # layout geral
        layout = QVBoxLayout(self)
        layout.addWidget(texto)
        layout.addWidget(instrucao)
        layout.addWidget(self.campo_confirmacao)
        layout.addWidget(self.erro)
        layout.addLayout(linha_botoes)

        # guarda o nome para o painel usar na mensagem final
        self.nome = resumo["nome"]

    def conferir_confirmacao(self, texto):
        """Só liga o botão Excluir quando o código digitado for igual ao do morador."""
        self.botao_excluir.setEnabled(texto.strip() == self.codigo)

    def excluir(self):
        """Apaga o morador e fecha a janela."""
        if excluir_morador(self.codigo):
            self.accept()
        else:
            self.erro.setText("Não foi possível excluir: o morador não foi encontrado.")
