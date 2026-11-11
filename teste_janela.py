# importa o sys, usado para passar argumentos ao Qt e encerrar o programa
import sys

# importa as classes de interface: aplicação, janela, texto e layout
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout

# importa o Qt, que tem as constantes de alinhamento
from PySide6.QtCore import Qt

# cria a aplicação Qt (toda interface PySide6 precisa de exatamente uma)
app = QApplication(sys.argv)

# cria a janela principal
janela = QWidget()

# define o título que aparece na barra da janela
janela.setWindowTitle("Portaria - Teste")

# define o tamanho inicial da janela: 400 de largura x 200 de altura
janela.resize(400, 200)

# cria um texto para mostrar dentro da janela
texto = QLabel("PySide6 funcionando!")

# centraliza o texto na horizontal e na vertical
texto.setAlignment(Qt.AlignCenter)

# aumenta a fonte do texto
texto.setStyleSheet("font-size: 22px;")

# cria um layout vertical (organiza os elementos de cima para baixo)
layout = QVBoxLayout()

# coloca o texto dentro do layout
layout.addWidget(texto)

# aplica o layout na janela
janela.setLayout(layout)

# mostra a janela na tela
janela.show()

# inicia o "loop" da interface: o programa fica rodando até a janela ser fechada
sys.exit(app.exec())
