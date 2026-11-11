# =====================================================================
# Regras do sistema, em um só lugar.
# Para mudar uma regra, altere aqui: todos os arquivos usam estes valores.
# =====================================================================

# ---------- cadastro do morador ----------

# quantidade EXATA de dígitos do código de acesso do morador
DIGITOS_CODIGO_MORADOR = 4

# tamanho mínimo da senha do morador
TAMANHO_MIN_SENHA_MORADOR = 8


def codigo_morador_valido(codigo):
    """Devolve True se o código tiver exatamente a quantidade de dígitos, só números."""
    return codigo.isdigit() and len(codigo) == DIGITOS_CODIGO_MORADOR


# ---------- bloqueio por tentativas na portaria ----------

# erros de código/senha com o MESMO código que bloqueiam esse código
MAX_ERROS_POR_CODIGO = 5

# erros de código/senha com QUALQUER código que bloqueiam a portaria inteira
MAX_ERROS_PORTARIA = 5

# janela de contagem e tempo de bloqueio, em minutos
MINUTOS_BLOQUEIO = 10

# textos gravados na coluna "motivo" do histórico
# (os erros são contados pelo motivo, então os textos precisam ser sempre os mesmos)
MOTIVO_CREDENCIAIS_INVALIDAS = "código ou senha inválidos"
MOTIVO_BLOQUEADO = "bloqueado por tentativas"
