# importa o sys para passar argumentos ao Qt e encerrar o programa
import sys

# importa o math para arredondar os minutos para cima
import math

# importa as consultas do painel
from consultas import listar_moradores_veiculos, formatar_placa

# importa a tela de login (o painel só abre depois do login com 2FA)
from tela_login import TelaLogin

# importa os formulários de cadastro, edição e exclusão
from dialogos import DialogoMorador, DialogoVeiculo
from dialogo_editar_morador import DialogoEditarMorador
from exclusao_morador import DialogoExcluirMorador

# importa as abas de rosto e de histórico
from aba_rosto import AbaRosto
from aba_historico import AbaHistorico

# importa a consulta e o desbloqueio da portaria
from bloqueio import situacao_bloqueio, desbloquear

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
    QMessageBox,        # caixa de confirmação do desbloqueio
)

# Qt = constantes de alinhamento; QTimer = relógio da verificação de bloqueio
from PySide6.QtCore import Qt, QTimer

# títulos das colunas da tabela de moradores
COLUNAS_MORADORES = ["Código", "Nome", "Bloco", "Apto", "Rosto", "Veículo", "Cor", "Placa", "Situação"]

# posição de cada aba (para saber qual está aberta)
ABA_MORADORES = 0
ABA_ROSTO = 1
ABA_HISTORICO = 2

# de quanto em quanto tempo o painel confere se há bloqueio (5 segundos)
INTERVALO_ALERTA_MS = 5_000


def em_minutos(segundos):
    """Converte segundos em minutos inteiros, arredondando para cima (mínimo 1)."""
    return max(math.ceil(segundos / 60), 1)


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
        self.resize(1250, 700)

        # mesmo estilo escuro das outras telas
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #f0f0f0; font-size: 15px; }
            QLineEdit, QComboBox { background-color: #2d2d2d; border: 2px solid #555; border-radius: 6px; padding: 6px; }
            QLineEdit:focus { border: 2px solid #3b82f6; }
            QPushButton { background-color: #333; border: 1px solid #555; border-radius: 6px; padding: 8px 14px; }
            QPushButton:pressed { background-color: #555; }
            QPushButton:disabled { color: #777; background-color: #2a2a2a; }
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

        # ---------- faixa vermelha de bloqueio (escondida até haver bloqueio) ----------
        self.faixa_alerta = QWidget()
        self.faixa_alerta.setStyleSheet("background-color: #7f1d1d; border-radius: 6px;")

        self.texto_alerta = QLabel("")
        self.texto_alerta.setWordWrap(True)
        self.texto_alerta.setStyleSheet("font-size: 16px; font-weight: bold; padding: 6px;")

        botao_desbloquear = QPushButton("Desbloquear")
        botao_desbloquear.setStyleSheet("background-color: #b91c1c; font-weight: bold;")
        botao_desbloquear.clicked.connect(self.desbloquear_portaria)

        layout_alerta = QHBoxLayout(self.faixa_alerta)
        layout_alerta.addWidget(self.texto_alerta, 1)
        layout_alerta.addWidget(botao_desbloquear)

        self.faixa_alerta.hide()

        # relógio que confere o bloqueio a cada 5 s, em qualquer aba
        self.timer_alerta = QTimer(self)
        self.timer_alerta.timeout.connect(self.atualizar_alerta)
        self.timer_alerta.start(INTERVALO_ALERTA_MS)

        # ---------- abas ----------
        self.aba_rosto = AbaRosto()
        self.aba_historico = AbaHistorico()

        self.abas = QTabWidget()
        self.abas.addTab(self.criar_aba_moradores(), "Moradores e veículos")   # índice 0
        self.abas.addTab(self.aba_rosto, "Rosto")                             # índice 1
        self.abas.addTab(self.aba_historico, "Histórico")                     # índice 2

        # ao trocar de aba: desliga a câmera e atualiza o conteúdo da aba aberta
        self.abas.currentChanged.connect(self.trocou_aba)

        # ---------- layout geral ----------
        layout = QVBoxLayout(self)
        layout.addLayout(barra_topo)
        layout.addWidget(self.faixa_alerta)
        layout.addWidget(self.abas)

        # carrega a tabela e confere o bloqueio ao abrir
        self.carregar_moradores()
        self.atualizar_alerta()

    # ================= alerta e desbloqueio =================

    def atualizar_alerta(self):
        """Confere o bloqueio no banco e mostra ou esconde a faixa vermelha."""
        situacao = situacao_bloqueio()
        partes = []

        # trava da portaria inteira
        if situacao["portaria"] > 0:
            partes.append(
                f"⚠️ PORTARIA BLOQUEADA por excesso de tentativas — libera em "
                f"{em_minutos(situacao['portaria'])} min."
            )

        # códigos bloqueados individualmente
        if situacao["codigos"]:
            lista = ", ".join(f"{codigo} ({em_minutos(seg)} min)" for codigo, seg in situacao["codigos"])
            partes.append(f"Códigos bloqueados: {lista}.")

        # mostra a faixa só se houver algum bloqueio
        if partes:
            self.texto_alerta.setText("  ".join(partes))
            self.faixa_alerta.show()
        else:
            self.faixa_alerta.hide()

    def desbloquear_portaria(self):
        """Pede confirmação, registra o desbloqueio e atualiza a faixa."""
        resposta = QMessageBox.question(
            self,
            "Desbloquear portaria",
            "Confirme que você verificou a situação na portaria.\n\n"
            "O desbloqueio libera a portaria e todos os códigos bloqueados agora.\n"
            "Os registros de tentativas continuam no histórico e o desbloqueio\n"
            "fica registrado com o seu nome.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,   # botão padrão = Não (evita desbloquear por engano com Enter)
        )

        if resposta == QMessageBox.Yes:
            desbloquear(self.funcionario["id"])
            self.atualizar_alerta()

    def trocou_aba(self, indice):
        """Chamado quando o funcionário muda de aba."""
        # saiu da aba Rosto: desliga a câmera e cancela qualquer captura
        if indice != ABA_ROSTO:
            self.aba_rosto.cancelar()

        # voltou para Moradores: recarrega para mostrar mudanças (ex.: Rosto = Sim)
        if indice == ABA_MORADORES:
            self.carregar_moradores()

        # o Histórico se recarrega sozinho ao aparecer (showEvent da AbaHistorico)

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

        # botão para excluir o morador selecionado
        botao_excluir_morador = QPushButton("Excluir morador")
        botao_excluir_morador.setStyleSheet("background-color: #b91c1c;")
        botao_excluir_morador.clicked.connect(self.excluir_morador)

        # botão para cadastrar veículo do morador selecionado
        botao_novo_veiculo = QPushButton("+ Novo veículo")
        botao_novo_veiculo.setStyleSheet("background-color: #1d4ed8;")
        botao_novo_veiculo.clicked.connect(self.novo_veiculo)

        linha_busca = QHBoxLayout()
        linha_busca.addWidget(self.campo_busca)
        linha_busca.addWidget(botao_atualizar)
        linha_busca.addWidget(botao_novo_morador)
        linha_busca.addWidget(botao_editar_morador)
        linha_busca.addWidget(botao_excluir_morador)
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

    def excluir_morador(self):
        """Abre a confirmação de exclusão para o morador selecionado."""
        selecionado = self.morador_selecionado()

        # sem linha selecionada: avisa e não abre a confirmação
        if selecionado is None:
            self.total_moradores.setText("Selecione um morador na tabela antes de excluir.")
            return

        codigo, nome = selecionado
        dialogo = DialogoExcluirMorador(codigo, self)

        if dialogo.exec() == QDialog.Accepted:
            self.carregar_moradores()
            self.total_moradores.setText(
                self.total_moradores.text() + f"  —  morador {nome} excluído."
            )

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
        """Desliga câmera e relógio, fecha o painel e volta para a tela de login."""
        self.timer_alerta.stop()
        self.aba_rosto.cancelar()
        self.close()
        self.ao_sair()

    def closeEvent(self, evento):
        """Chamado quando a janela fecha (inclusive pelo X): desliga câmera e relógio."""
        self.timer_alerta.stop()
        self.aba_rosto.cancelar()
        evento.accept()


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
