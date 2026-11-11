# importa o re (expressões regulares) para validar a placa
import re

# importa o erro que o MySQL gera quando um valor UNIQUE se repete
from mysql.connector.errors import IntegrityError

# importa a conexão com o banco
from banco import conectar

# formato de placa brasileira, sem hífen:
# 3 letras + 1 número + (letra OU número) + 2 números
# cobre o padrão antigo (ABC1234) e o Mercosul (ABC1D23)
FORMATO_PLACA = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")


def normalizar_placa(placa):
    """Deixa a placa no formato gravado no banco: sem hífen, sem espaços, maiúsculas."""
    return placa.replace("-", "").replace(" ", "").upper()


def placa_valida(placa):
    """Devolve True se a placa (já normalizada) segue o padrão antigo ou Mercosul."""
    return bool(FORMATO_PLACA.match(placa))


def placa_existe(placa):
    """Devolve True se a placa já estiver cadastrada."""
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT 1 FROM veiculos WHERE placa = %s LIMIT 1", (placa,))
    existe = cursor.fetchone() is not None
    cursor.close()
    conexao.close()
    return existe


def cadastrar_veiculo(codigo_morador, modelo, cor, placa):
    """Grava um veículo para o morador do código informado.
    Devolve o id criado, ou None se a placa já existir ou o morador não for encontrado."""
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        # INSERT ... SELECT: pega o id do morador pelo código e grava o veículo numa só instrução
        cursor.execute(
            """
            INSERT INTO veiculos (morador_id, modelo, cor, placa)
            SELECT id, %s, %s, %s FROM moradores WHERE codigo = %s
            """,
            (modelo, cor, placa, codigo_morador),
        )
        conexao.commit()

        # rowcount = quantas linhas foram inseridas (0 se o morador não existe)
        novo_id = cursor.lastrowid if cursor.rowcount == 1 else None

    except IntegrityError:
        # o banco recusou: placa repetida (segunda barreira)
        novo_id = None

    finally:
        cursor.close()
        conexao.close()

    return novo_id
