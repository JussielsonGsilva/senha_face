# importa o datetime para mostrar a hora da última atualização
from datetime import datetime

# importa a consulta do histórico e o limite de linhas
from consultas import listar_acessos, LIMITE_HISTORICO

# importa as classes de interface
from PySide6.QtWidgets import (
    QWidget,            # área genérica
    QLabel,             # texto
    QLineEdit,          # campo de digitação
    QComboBox,          # lista de opções
    QPushButton,        # botão
    QVBoxLayout,        # layout vertical
    QHBoxLayout,        # layout horizontal
    QTableWidget,       # tabela
    QTableWidgetItem,   # célula
    QHeaderView,        # cabeçalho da tabela
)

# Qt = constantes de alinhamento; QTimer = relógio da atualização automática
from PySide6.QtCore import Qt, QTimer

# QColor = cor do texto (verde/vermelho)
from PySide6.QtGui import QColor

# de quanto em quanto tempo a tabela recarrega sozinha (10 segundos)
INTERVALO_ATUALIZACAO_MS = 10_000

# títulos das colunas
COLUNAS_HISTORICO = ["Data e hora", "Código", "Morador", "Bloco / Apto", "Resultado", "Motivo", "Nota"]

# opções do filtro de período: texto mostrado -> quantidade de dias (None = tudo)
PERIODOS = {
    "Hoje": 1,
    "Últimos 7 dias": 7,
    "Últimos 30 dias": 30,
    "Tudo": None,
}

# opções do filtro de resultado: texto mostrado -> valor no banco (None = todos)
RESULTADOS = {
    "Todos": None,
    "Liberado": "LIBERADO",
    "Negado": "NEGADO",
}

# cores do resultado
COR_LIBERADO = QColor("#4ade80")
COR_NEGADO = QColor("#f87171")


class AbaHistorico(QWidget):
    """Aba do painel com o histórico de tentativas de acesso (atualiza sozinha a cada 10 s)."""

    def __init__(self):
        super().__init__()

        # ---------- relógio da atualização automática ----------
        self.timer_atualizacao = QTimer(self)
        self.timer_atualizacao.timeout.connect(self.carregar)

        # ---------- filtros ----------

        # período (começa em "Hoje")
        self.filtro_periodo = QComboBox()
        self.filtro_periodo.addItems(PERIODOS.keys())
        self.filtro_periodo.currentIndexChanged.connect(self.carregar)

        # resultado (começa em "Todos")
        self.filtro_resultado = QComboBox()
        self.filtro_resultado.addItems(RESULTADOS.keys())
        self.filtro_resultado.currentIndexChanged.connect(self.carregar)

        # busca por código ou nome: filtra enquanto digita
        self.campo_busca = QLineEdit()
        self.campo_busca.setPlaceholderText("Buscar por código ou nome do morador...")
        self.campo_busca.textChanged.connect(self.carregar)

        # botão para recarregar na hora, sem esperar os 10 s
        botao_atualizar = QPushButton("Atualizar")
        botao_atualizar.clicked.connect(self.carregar)

        linha_filtros = QHBoxLayout()
        linha_filtros.addWidget(QLabel("Período:"))
        linha_filtros.addWidget(self.filtro_periodo)
        linha_filtros.addWidget(QLabel("Resultado:"))
        linha_filtros.addWidget(self.filtro_resultado)
        linha_filtros.addWidget(self.campo_busca)
        linha_filtros.addWidget(botao_atualizar)

        # ---------- tabela ----------
        self.tabela = QTableWidget(0, len(COLUNAS_HISTORICO))
        self.tabela.setHorizontalHeaderLabels(COLUNAS_HISTORICO)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)        # só leitura
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)       # seleciona a linha toda
        self.tabela.verticalHeader().setVisible(False)                  # sem numeração à esquerda

        # colunas ajustadas ao conteúdo; "Motivo" ocupa o espaço que sobrar
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeToContents)
        cabecalho.setSectionResizeMode(5, QHeaderView.Stretch)

        # ---------- resumo ----------
        self.resumo = QLabel("")

        # ---------- layout ----------
        layout = QVBoxLayout(self)
        layout.addLayout(linha_filtros)
        layout.addWidget(self.tabela)
        layout.addWidget(self.resumo)

    # ================= liga/desliga automático =================

    def showEvent(self, evento):
        """O Qt chama quando a aba APARECE: recarrega e liga a atualização automática."""
        super().showEvent(evento)
        self.carregar()
        self.timer_atualizacao.start(INTERVALO_ATUALIZACAO_MS)

    def hideEvent(self, evento):
        """O Qt chama quando a aba SOME (troca de aba, Sair ou fechar): desliga o relógio."""
        super().hideEvent(evento)
        self.timer_atualizacao.stop()

    # ================= carga da tabela =================

    def carregar(self):
        """Busca no banco conforme os filtros e preenche a tabela."""
        # guarda a posição da rolagem para a tabela não pular para o topo a cada recarga
        rolagem = self.tabela.verticalScrollBar().value()

        # converte o texto escolhido nos combos para o valor usado na consulta
        dias = PERIODOS[self.filtro_periodo.currentText()]
        resultado = RESULTADOS[self.filtro_resultado.currentText()]

        linhas = listar_acessos(dias, resultado, self.campo_busca.text())
        self.tabela.setRowCount(len(linhas))

        # contadores para o resumo
        liberados = 0
        negados = 0

        for i, linha in enumerate(linhas):
            # morador: nome, ou aviso quando não há morador ligado à tentativa
            morador = linha["nome"] or "— (sem morador)"

            # bloco/apto: monta só se houver morador
            if linha["nome"]:
                local = f"{linha['bloco']} / {linha['apartamento']}" if linha["bloco"] else linha["apartamento"]
            else:
                local = "—"

            # nota com 2 casas, ou traço quando a câmera nem abriu
            nota = f"{float(linha['nota_facial']):.2f}" if linha["nota_facial"] is not None else "—"

            # valores na mesma ordem de COLUNAS_HISTORICO
            valores = [
                linha["data_hora"].strftime("%d/%m/%Y %H:%M:%S"),
                linha["codigo_digitado"],
                morador,
                local,
                linha["resultado"],
                linha["motivo"],
                nota,
            ]

            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))

                # centraliza tudo, menos morador e motivo
                if coluna not in (2, 5):
                    item.setTextAlignment(Qt.AlignCenter)

                # pinta a coluna Resultado de verde ou vermelho
                if coluna == 4:
                    item.setForeground(COR_LIBERADO if valor == "LIBERADO" else COR_NEGADO)

                self.tabela.setItem(i, coluna, item)

            # soma no resumo
            if linha["resultado"] == "LIBERADO":
                liberados += 1
            else:
                negados += 1

        # devolve a rolagem para onde estava
        self.tabela.verticalScrollBar().setValue(rolagem)

        # monta o texto do resumo, com a hora da última atualização
        agora = datetime.now().strftime("%H:%M:%S")
        texto = f"{len(linhas)} tentativa(s): {liberados} liberada(s), {negados} negada(s)"
        if len(linhas) == LIMITE_HISTORICO:
            texto += f"  —  mostrando as {LIMITE_HISTORICO} mais recentes; use os filtros para refinar"
        texto += f"  —  atualizado às {agora} (automático a cada 10 s)"
        self.resumo.setText(texto)
