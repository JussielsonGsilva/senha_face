# importa o bcrypt para gerar o hash da senha
import bcrypt

# importa o getpass, que lê a senha sem mostrar o que é digitado
from getpass import getpass

# importa o tipo de erro que o MySQL gera quando um valor UNIQUE se repete
from mysql.connector.errors import IntegrityError

# importa a função de conexão criada no banco.py
from banco import conectar

# importa as regras centralizadas (4 dígitos no código, senha com 8 ou mais)
from regras import DIGITOS_CODIGO_MORADOR, TAMANHO_MIN_SENHA_MORADOR, codigo_morador_valido


def codigo_existe(codigo):
    """Devolve True se o código de acesso já estiver cadastrado."""
    conexao = conectar()
    cursor = conexao.cursor()

    # procura algum morador com esse código (LIMIT 1: basta achar um)
    cursor.execute("SELECT 1 FROM moradores WHERE codigo = %s LIMIT 1", (codigo,))

    # fetchone() devolve uma linha se achou, ou None se não achou
    existe = cursor.fetchone() is not None

    cursor.close()
    conexao.close()
    return existe


def cadastrar_morador(codigo, nome, bloco, apartamento, senha):
    """Grava um novo morador no banco, com a senha em hash bcrypt.
    Devolve o id criado, ou None se o código já existir."""
    # gera o hash da senha (o sal aleatório faz senhas iguais terem hashes diferentes)
    senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())

    conexao = conectar()
    cursor = conexao.cursor()

    # comando de inserção; os %s são preenchidos com segurança pelo conector (evita SQL injection)
    sql = """
        INSERT INTO moradores (codigo, nome, bloco, apartamento, senha_hash)
        VALUES (%s, %s, %s, %s, %s)
    """

    try:
        # executa o INSERT; bloco vazio vira NULL; o hash vira texto
        cursor.execute(sql, (codigo, nome, bloco or None, apartamento, senha_hash.decode("utf-8")))
        conexao.commit()
        novo_id = cursor.lastrowid
    except IntegrityError:
        # o banco recusou porque o código já existe (segunda barreira)
        novo_id = None
    finally:
        # fecha cursor e conexão com erro ou sem erro
        cursor.close()
        conexao.close()

    return novo_id


def pedir_codigo():
    """Pede o código até ter o formato certo e estar livre."""
    while True:
        codigo = input(f"Código de acesso ({DIGITOS_CODIGO_MORADOR} dígitos): ").strip()
        if not codigo_morador_valido(codigo):
            print(f"O código precisa ter exatamente {DIGITOS_CODIGO_MORADOR} dígitos.")
            continue
        if codigo_existe(codigo):
            print(f"O código {codigo} já está em uso. Escolha outro.")
            continue
        return codigo


def pedir_obrigatorio(rotulo):
    """Pede um texto até não estar vazio."""
    while True:
        texto = input(rotulo).strip()
        if texto:
            return texto
        print("Este campo é obrigatório.")


def pedir_senha():
    """Pede a senha duas vezes até cumprir o mínimo e as duas conferirem."""
    while True:
        senha = getpass(f"Senha (mínimo {TAMANHO_MIN_SENHA_MORADOR} caracteres): ")
        if len(senha) < TAMANHO_MIN_SENHA_MORADOR:
            print(f"Senha muito curta. Use pelo menos {TAMANHO_MIN_SENHA_MORADOR} caracteres.")
            continue
        if senha != getpass("Confirme a senha: "):
            print("As senhas não conferem. Digite novamente.")
            continue
        return senha


# este bloco só roda quando você executa "python moradores.py" diretamente
if __name__ == "__main__":
    print("=== Cadastro de morador ===")
    print("(Ctrl+C cancela a qualquer momento)")

    try:
        # cada função só devolve quando o valor estiver válido
        codigo = pedir_codigo()
        nome = pedir_obrigatorio("Nome completo: ")
        bloco = input("Bloco (Enter se não houver): ").strip()
        apartamento = pedir_obrigatorio("Apartamento: ")
        senha = pedir_senha()
    except KeyboardInterrupt:
        # Ctrl+C: encerra sem a mensagem de erro do Python
        print("\nCadastro cancelado.")
        exit()

    novo_id = cadastrar_morador(codigo, nome, bloco, apartamento, senha)

    if novo_id is None:
        print(f"O código {codigo} acabou de ser usado por outro cadastro. Rode de novo.")
    else:
        print(f"Morador cadastrado com sucesso! ID: {novo_id}")
