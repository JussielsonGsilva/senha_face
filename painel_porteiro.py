# importa o sys para passar argumentos ao Qt e encerrar o programa
import sys

# importa as consultas do painel
from consultas import listar_moradores_veiculos, formatar_placa

# importa a tela de login (o painel só abre depois do login com 2FA)
from tela_login import TelaLogin

# importa os formulários de cadastro e de edição
from dialogos import DialogoMorador, DialogoVeiculo
from dialogo_editar_morador import DialogoEditarMorador

# importa as classes de interface
from PySide6.QtWidgets import (
    QApplication,       # a aplicação Qt
    QWidget,            # janela/área genérica
    QLabel,             # texto
    QLineEdit,          # campo de digitação
    QPushButton,        # botão
    QVBoxLayout,        # layout vertical
    QHBoxLayout,        # layout horizontal
    QTabWidget,         # abas
    QTableWidget,       # tabela
    QTableWidgetItem,   # célula da tabela
    QHeaderView,        # cabeçalho da tabela (para ajustar largura das colunas)
    QDialog,            # usado para conferir se o diálogo foi salvo (Accepted)
)

# Qt = constantes de alinhamento
from PySide6.QtCore import Qt

# títulos das colunas da tabela de moradores
COLUNAS_MORADORES = ["Código", "Nome", "Bloco", "Apto", "Rosto", "Veículo", "Cor", "Placa", "Situação"]


class PainelPorteiro(QWidget):
    """Painel do funcionário da portaria (abre só depois do login com 2FA)."""

    def __init__(self, funcionario, ao_sair):
        # inicializa a QWidget (classe "mãe")
        super().__init__()

        # guarda o funcionário logado e a função a chamar quando clicar em Sair
        self.funcionario = funcionario
        self.ao_sair = ao_sair

        # título e tamanho
        self.setWindowTitle("Portaria - Painel do funcionário")
        self.resize(1150, 650)

        # mesmo estilo escuro das outras telas
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #f0f0f0; font-size: 15px; }
            QLineEdit, QComboBox { background-color: #2d2d2d; border: 2px solid #555; border-radius: 6px; padding: 6px; }
            QLineEdit:focus { border: 2px solid #3b82f6; }
            QPushButton { background-color: #333; border: 1px solid #555; border-radius: 6px; padding: 8px 14px; }
            QPushButton:pressed { background-color: #555; }
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #2d2d2d; padding: 8px 18px; }
            QTabBar::tab:selected { background: #2563eb; }
            QTableWidget { background-color: #252525; gridline-color: #444; }
            QHeaderView::section { background-color: #333; padding: 6px; border: none; }
        """)

        # ---------- barra do topo: funcionário logado + Sair ----------
        rotulo_funcionario = QLabel(f"Funcionário: <b>{funcionario['nome']}</b>")
        botao_sair = QPushButton("Sair")
        botao_sair.clicked.connect(self.sair)

        barra_topo = QHBoxLayout()
        barra_topo.addWidget(rotulo_funcionario)
        barra_topo.addStretch()
        barra_topo.addWidget(botao_sair)

        # ---------- abas ----------
        self.abas = QTabWidget()
        self.abas.addTab(self.criar_aba_moradores(), "Moradores e veículos")
        self.abas.addTab(QLabel("Em construção"), "Rosto")
        self.abas.addTab(QLabel("Em construção"), "Histórico")

        # ---------- layout geral ----------
        layout = QVBoxLayout(self)
        layout.addLayout(barra_topo)
        layout.addWidget(self.abas)

        # carrega a tabela ao abrir
        self.carregar_moradores()

    # ================= aba moradores e veículos =================

    def criar_aba_moradores(self):
        """Monta a aba com busca, botões e tabela de moradores e veículos."""
        aba = QWidget()

        # campo de busca: filtra enquanto digita
        self.campo_busca = QLineEdit()
        self.campo_busca.setPlaceholderText("Buscar por nome, bloco, apartamento, código, veículo ou placa...")
        self.campo_busca.textChanged.connect(self.carregar_moradores)

        # botão para recarregar do banco
        botao_atualizar = QPushButton("Atualizar")
        botao_atualizar.clicked.connect(self.carregar_moradores)

        # botão para abrir o formulário de novo morador
        botao_novo_morador = QPushButton("+ Novo morador")
        botao_novo_morador.setStyleSheet("background-color: #15803d;")
        botao_novo_morador.clicked.connect(self.novo_morador)

        # botão para editar o morador selecionado
        botao_editar_morador = QPushButton("Editar morador")
        botao_editar_morador.setStyleSheet("background-color: #a16207;")
        botao_editar_morador.clicked.connect(self.editar_morador)

        # botão para cadastrar veículo do morador selecionado
        botao_novo_veiculo = QPushButton("+ Novo veículo")
        botao_novo_veiculo.setStyleSheet("background-color: #1d4ed8;")
        botao_novo_veiculo.clicked.connect(self.novo_veiculo)

        linha_busca = QHBoxLayout()
        linha_busca.addWidget(self.campo_busca)
        linha_busca.addWidget(botao_atualizar)
        linha_busca.addWidget(botao_novo_morador)
        linha_busca.addWidget(botao_editar_morador)
        linha_busca.addWidget(botao_novo_veiculo)

        # tabela com as colunas definidas lá em cima
        self.tabela_moradores = QTableWidget(0, len(COLUNAS_MORADORES))
        self.tabela_moradores.setHorizontalHeaderLabels(COLUNAS_MORADORES)

        # só leitura: o funcionário não edita direto na célula
        self.tabela_moradores.setEditTriggers(QTableWidget.NoEditTriggers)

        # clicar seleciona a linha inteira, e só uma linha por vez
        self.tabela_moradores.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela_moradores.setSelectionMode(QTableWidget.SingleSelection)

        # dois cliques numa linha abre a edição do morador
        self.tabela_moradores.cellDoubleClicked.connect(lambda linha, coluna: self.editar_morador())

        # esconde a numeração de linhas da esquerda
        self.tabela_moradores.verticalHeader().setVisible(False)

        # colunas se ajustam à largura; a do nome ocupa o espaço que sobrar
        cabecalho = self.tabela_moradores.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeToContents)
        cabecalho.setSectionResizeMode(1, QHeaderView.Stretch)

        # contador de resultados / mensagens da aba
        self.total_moradores = QLabel("")

        layout = QVBoxLayout(aba)
        layout.addLayout(linha_busca)
        layout.addWidget(self.tabela_moradores)
        layout.addWidget(self.total_moradores)
        return aba

    def carregar_moradores(self):
        """Busca no banco e preenche a tabela."""
        linhas = listar_moradores_veiculos(self.campo_busca.text())

        # ajusta a quantidade de linhas da tabela
        self.tabela_moradores.setRowCount(len(linhas))

        for i, linha in enumerate(linhas):
            # valores de cada coluna, na mesma ordem de COLUNAS_MORADORES
            valores = [
                linha["codigo"],
                linha["nome"],
                linha["bloco"] or "",
                linha["apartamento"],
                "Sim" if linha["tem_rosto"] else "Não",
                linha["modelo"] or "—",
                linha["cor"] or "—",
                formatar_placa(linha["placa"]) or "—",
                "Ativo" if linha["ativo"] else "Inativo",
            ]

            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                # centraliza tudo, menos o nome
                if coluna != 1:
                    item.setTextAlignment(Qt.AlignCenter)
                self.tabela_moradores.setItem(i, coluna, item)

        # mostra quantas linhas apareceram
        self.total_moradores.setText(f"{len(linhas)} registro(s)")

    def morador_selecionado(self):
        """Devolve (codigo, nome) da linha selecionada na tabela, ou None."""
        linha = self.tabela_moradores.currentRow()

        # -1 = nenhuma linha selecionada
        if linha < 0:
            return None

        # coluna 0 = código, coluna 1 = nome
        codigo = self.tabela_moradores.item(linha, 0).text()
        nome = self.tabela_moradores.item(linha, 1).text()
        return codigo, nome

    def novo_morador(self):
        """Abre o formulário de novo morador e atualiza a tabela se salvar."""
        dialogo = DialogoMorador(self)

        # exec() abre a janela e ESPERA até ela fechar; devolve Accepted se clicou Salvar
        if dialogo.exec() == QDialog.Accepted:
            self.campo_busca.clear()
            self.carregar_moradores()
            self.total_moradores.setText(
                self.total_moradores.text() + "  —  morador cadastrado. Cadastre o rosto na aba Rosto."
            )

    def editar_morador(self):
        """Abre o formulário de edição para o morador selecionado."""
        selecionado = self.morador_selecionado()

        # sem linha selecionada: avisa e não abre o formulário
        if selecionado is None:
            self.total_moradores.setText("Selecione um morador na tabela antes de editar.")
            return

        codigo, nome = selecionado
        dialogo = DialogoEditarMorador(codigo, self)

        if dialogo.exec() == QDialog.Accepted:
            self.carregar_moradores()
            aviso = f"  —  dados de {nome} atualizados"
            if dialogo.senha_trocada:
                aviso += " (senha alterada)"
            self.total_moradores.setText(self.total_moradores.text() + aviso + ".")

    def novo_veiculo(self):
        """Abre o formulário de veículo para o morador selecionado."""
        selecionado = self.morador_selecionado()

        # sem linha selecionada: avisa e não abre o formulário
        if selecionado is None:
            self.total_moradores.setText("Selecione um morador na tabela antes de cadastrar o veículo.")
            return

        codigo, nome = selecionado
        dialogo = DialogoVeiculo(codigo, nome, self)

        if dialogo.exec() == QDialog.Accepted:
            self.carregar_moradores()
            self.total_moradores.setText(
                self.total_moradores.text() + f"  —  veículo cadastrado para {nome}."
            )

    # ================= sair =================

    def sair(self):
        """Fecha o painel e volta para a tela de login."""
        self.close()
        self.ao_sair()


# este bloco só roda com "python painel_porteiro.py"
# fluxo completo: login com 2FA -> painel -> Sair -> login de novo
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # guarda as janelas abertas (sem isso o Python poderia apagar o painel da memória)
    janelas = {}

    tela_login = TelaLogin()

    def mostrar_login():
        """Mostra a tela de login (usada no início e ao clicar em Sair)."""
        tela_login.show()

    def abrir_painel(funcionario):
        """Chamado pelo sinal login_aprovado: fecha o login e abre o painel."""
        tela_login.hide()
        janelas["painel"] = PainelPorteiro(funcionario, ao_sair=mostrar_login)
        janelas["painel"].show()

    # liga o sinal do login à função que abre o painel
    tela_login.login_aprovado.connect(abrir_painel)

    mostrar_login()
    sys.exit(app.exec())
