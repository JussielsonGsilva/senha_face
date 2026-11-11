# =====================================================================
# Prova de vida (anti-spoofing) por desafio de movimento da cabeça.
# Uma foto ou tela é plana: mesmo inclinada, o nariz não "foge" do meio
# dos olhos. Um rosto real, ao virar, desloca o nariz para o lado.
# =====================================================================

# importa o random; o SystemRandom usa o gerador seguro do sistema (imprevisível)
import random

# quanto o índice de giro precisa passar (calibrado: foto ~0,06; pessoa 0,48 a 0,67)
LIMITE_GIRO = 0.30

# quantos frames seguidos o giro precisa ficar além do limite
FRAMES_GIRO = 3

# índice máximo para considerar o rosto "de frente" na confirmação final
LIMITE_FRENTE = 0.15

# frames seguidos na confirmação final (de frente + reconhecido)
FRAMES_CONFIRMACAO = 3

# tempo total, em segundos, para o desafio e a confirmação final
TEMPO_DESAFIO = 12

# quantos frames seguidos o rosto pode sumir (ou aparecer mais de um) antes de falhar
# (com análise a cada 100 ms, 5 frames = meio segundo)
MAX_FRAMES_SEM_ROSTO = 5

# sinal do índice para cada lado (calibrado: sua esquerda = +, sua direita = -)
SINAL_DO_LADO = {
    "esquerda": +1,
    "direita": -1,
}

# texto mostrado na tela para cada lado
TEXTO_DO_LADO = {
    "esquerda": "ESQUERDA",
    "direita": "DIREITA",
}


def indice_de_giro(rosto):
    """Calcula o quanto o rosto está virado para um lado.
    ~0 = de frente; positivo = virado para a esquerda da pessoa; negativo = para a direita."""
    # posições 4 e 6: x dos dois olhos; posição 8: x da ponta do nariz (pontos do YuNet)
    olho1_x, olho2_x = rosto[4], rosto[6]
    nariz_x = rosto[8]

    # ponto do meio entre os olhos e distância entre eles
    meio_olhos = (olho1_x + olho2_x) / 2
    distancia_olhos = abs(olho2_x - olho1_x)

    # evita divisão por zero se os olhos não forem detectados direito
    if distancia_olhos < 1:
        return 0.0

    # deslocamento do nariz, proporcional à distância dos olhos (não depende de perto/longe)
    return float((nariz_x - meio_olhos) / distancia_olhos)


def sortear_desafio():
    """Devolve a ordem dos movimentos, sorteada de forma imprevisível.
    Ex.: ['direita', 'esquerda'] ou ['esquerda', 'direita']."""
    passos = ["esquerda", "direita"]
    random.SystemRandom().shuffle(passos)
    return passos


def girou_para(rosto, lado):
    """Devolve True se o rosto está virado o suficiente para o lado pedido."""
    return indice_de_giro(rosto) * SINAL_DO_LADO[lado] >= LIMITE_GIRO


def esta_de_frente(rosto):
    """Devolve True se o rosto está praticamente de frente."""
    return abs(indice_de_giro(rosto)) <= LIMITE_FRENTE
