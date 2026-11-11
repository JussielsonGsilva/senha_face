# importa o os para mexer nas variáveis de ambiente
import os

# importa o sys para passar argumentos ao Qt
import sys

# importa o OpenCV para ler a câmera
import cv2

# o OpenCV configura uma variável que aponta para o Qt interno dele;
# removemos para o PySide6 usar o próprio Qt e não dar conflito
os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)

# importa as classes de interface
from PySide6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout

# QTimer = relógio que dispara de tempos em tempos; Qt = constantes de alinhamento
from PySide6.QtCore import QTimer, Qt

# QImage e QPixmap = formatos de imagem que o Qt sabe exibir
from PySide6.QtGui import QImage, QPixmap


class PainelCamera(QLabel):
    """Área da janela que mostra o vídeo da webcam."""

    def __init__(self, indice_camera=0):
        # inicializa o QLabel (a classe "mãe")
        super().__init__()

        # guarda qual câmera usar (0 = primeira webcam)
        self.indice_camera = indice_camera

        # a câmera começa desligada
        self.camera = None

        # guarda o último frame lido, para outras partes do sistema usarem
        self.ultimo_frame = None

        # centraliza a imagem dentro da área
        self.setAlignment(Qt.AlignCenter)

        # tamanho mínimo da área do vídeo
        self.setMinimumSize(640, 480)

        # fundo preto e texto branco enquanto a câmera está desligada
        self.setStyleSheet("background-color: black; color: white; font-size: 18px;")

        # texto mostrado antes de ligar a câmera
        self.setText("Câmera desligada")

        # cria o relógio que vai pedir um frame novo de tempos em tempos
        self.timer = QTimer(self)

        # cada vez que o relógio disparar, chama o método _atualizar
        self.timer.timeout.connect(self._atualizar)

    def ligar(self):
        """Abre a câmera e começa a mostrar o vídeo. Devolve True se deu certo."""
        # abre a webcam
        self.camera = cv2.VideoCapture(self.indice_camera)

        # se não abriu, avisa na própria área do vídeo
        if not self.camera.isOpened():
            self.setText("Erro: câmera não encontrada")
            self.camera = None
            return False

        # liga o relógio: dispara a cada 30 ms (cerca de 33 frames por segundo)
        self.timer.start(30)
        return True

    def desligar(self):
        """Para o vídeo e libera a câmera."""
        # para o relógio
        self.timer.stop()

        # libera a câmera, se estiver aberta
        if self.camera is not None:
            self.camera.release()
            self.camera = None

        # limpa a imagem e volta o texto inicial
        self.ultimo_frame = None
        self.clear()
        self.setText("Câmera desligada")

    def _atualizar(self):
        """Chamado pelo relógio: lê um frame e mostra na tela."""
        # se a câmera não estiver aberta, não faz nada
        if self.camera is None:
            return

        # lê um frame; se falhar, só espera o próximo disparo
        ok, frame = self.camera.read()
        if not ok:
            return

        # guarda o frame original (sem desenhos)
        self.ultimo_frame = frame

        # exibe o frame na tela
        self.mostrar(frame)

    def mostrar(self, frame):
        """Converte um frame do OpenCV e exibe na área do vídeo."""
        # o OpenCV usa as cores na ordem BGR; o Qt usa RGB, então invertemos
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # pega altura, largura e quantidade de canais de cor (3)
        altura, largura, canais = rgb.shape

        # cria a QImage apontando para os dados da imagem;
        # canais * largura = quantos bytes tem cada linha da imagem
        imagem = QImage(rgb.data, largura, altura, canais * largura, QImage.Format_RGB888)

        # converte para QPixmap e ajusta ao tamanho da área, mantendo a proporção
        pixmap = QPixmap.fromImage(imagem).scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        # coloca a imagem no QLabel
        self.setPixmap(pixmap)


# este bloco só roda com "python painel_camera.py" (demonstração)
if __name__ == "__main__":
    # cria a aplicação Qt
    app = QApplication(sys.argv)

    # cria a janela e define o título
    janela = QWidget()
    janela.setWindowTitle("Portaria - Teste da câmera no Qt")

    # cria o painel da câmera
    painel = PainelCamera()

    # coloca o painel dentro da janela com um layout vertical
    layout = QVBoxLayout(janela)
    layout.addWidget(painel)

    # quando a aplicação for fechar, desliga a câmera antes
    app.aboutToQuit.connect(painel.desligar)

    # mostra a janela e liga a câmera
    janela.show()
    painel.ligar()

    # inicia o loop da interface
    sys.exit(app.exec())
