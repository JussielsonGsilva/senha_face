# =====================================================================
# Regras de cadastro do sistema, em um só lugar.
# Para mudar uma regra, altere aqui: todos os arquivos usam estes valores.
# =====================================================================

# quantidade EXATA de dígitos do código de acesso do morador
DIGITOS_CODIGO_MORADOR = 4

# tamanho mínimo da senha do morador
TAMANHO_MIN_SENHA_MORADOR = 8


def codigo_morador_valido(codigo):
    """Devolve True se o código tiver exatamente a quantidade de dígitos, só números."""
    return codigo.isdigit() and len(codigo) == DIGITOS_CODIGO_MORADOR
