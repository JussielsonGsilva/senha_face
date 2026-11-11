# importa o re (expressões regulares) para validar usuário e e-mail
import re

# importa o unicodedata para tirar acentos (ex.: "joão" -> "joao")
import unicodedata

# importa o bcrypt para gerar o hash da senha
import bcrypt

# importa o getpass para ler a senha sem mostrar na tela
from getpass import getpass

# importa o erro que o MySQL gera quando um valor UNIQUE se repete
from mysql.connector.errors import IntegrityError

# importa a função de conexão com o banco
from banco import conectar

# tamanho mínimo da senha do funcionário (o painel tem dados pessoais)
TAMANHO_MIN_SENHA = 8

# regra do usuário: 3 a 30 caracteres; letras minúsculas sem acento, números, ponto, hífen e sublinhado
FORMATO_USUARIO = re.compile(r"^[a-z0-9._-]{3,30}$")

# formato básico de e-mail: algo@algo.algo, sem espaços
FORMATO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def sugerir_usuario(texto):
    """Transforma um texto qualquer numa sugestão de usuário válida.
    Ex.: 'Marcos Silva' -> 'marcos.silva' / 'João  Paulo' -> 'joao.paulo'"""
    # separa letras e acentos (ex.: "ã" vira "a" + "~")
    sem_acento = unicodedata.normalize("NFKD", texto)

    # descarta os acentos soltos, ficando só os caracteres básicos
    sem_acento = sem_acento.encode("ascii", "ignore").decode("ascii")

    # minúsculas e sem espaços nas pontas
    sem_acento = sem_acento.lower().strip()

    # troca um ou mais espaços seguidos por um ponto
    sugestao = re.sub(r"\s+", ".", sem_acento)

    # remove qualquer caractere fora da regra
    sugestao = re.sub(r"[^a-z0-9._-]", "", sugestao)

    # corta no tamanho máximo
    return sugestao[:30]


def usuario_existe(usuario):
    """Devolve True se o nome de usuário já estiver cadastrado."""
    conexao = conectar()
    cursor = conexao.cursor()

    # procura algum funcionário com esse usuário
    cursor.execute("SELECT 1 FROM funcionarios WHERE usuario = %s LIMIT 1", (usuario,))
    existe = cursor.fetchone() is not None

    cursor.close()
    conexao.close()
    return existe


def cadastrar_funcionario(usuario, nome, email, senha):
    """Grava um novo funcionário com a senha em hash.
    Devolve o id criado, ou None se o usuário já existir."""
    # gera o hash da senha com bcrypt
    senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        # insere o funcionário (parâmetros %s evitam SQL injection)
        cursor.execute(
            """
            INSERT INTO funcionarios (usuario, nome, email, senha_hash)
            VALUES (%s, %s, %s, %s)
            """,
            (usuario, nome, email, senha_hash.decode("utf-8")),
        )
        conexao.commit()
        novo_id = cursor.lastrowid
    except IntegrityError:
        # o banco recusou: usuário repetido (segunda barreira)
        novo_id = None
    finally:
        # fecha cursor e conexão com erro ou sem erro
        cursor.close()
        conexao.close()

    return novo_id


def pedir_usuario():
    """Pede o usuário até ser válido e livre. Sugere uma correção quando possível."""
    while True:
        digitado = input("Usuário (ex.: joao.silva): ").strip().lower()

        # se não segue a regra, oferece uma sugestão corrigida
        if not FORMATO_USUARIO.match(digitado):
            sugestao = sugerir_usuario(digitado)

            # só oferece a sugestão se ela for válida
            if FORMATO_USUARIO.match(sugestao):
                resposta = input(f"Usuário inválido. Usar '{sugestao}'? [Enter = sim / N = digitar outro]: ")

                # Enter (resposta vazia) aceita a sugestão
                if resposta.strip().lower() in ("", "s", "sim"):
                    digitado = sugestao
                else:
                    continue
            else:
                print("Use de 3 a 30 caracteres: letras sem acento, números, ponto, hífen ou sublinhado.")
                continue

        # confere se já existe no banco
        if usuario_existe(digitado):
            print(f"O usuário {digitado} já existe. Escolha outro.")
            continue

        # válido e livre: devolve
        return digitado


def pedir_nome():
    """Pede o nome completo até não estar vazio."""
    while True:
        nome = input("Nome completo: ").strip()
        if nome:
            return nome
        print("O nome não pode ficar vazio.")


def pedir_email():
    """Pede o e-mail até ter um formato válido."""
    while True:
        email = input("E-mail (recebe o código 2FA): ").strip().lower()
        if FORMATO_EMAIL.match(email):
            return email
        print("E-mail com formato inválido. Exemplo: nome@dominio.com")


def pedir_senha():
    """Pede a senha duas vezes até cumprir o tamanho mínimo e as duas conferirem."""
    while True:
        senha = getpass(f"Senha (mínimo {TAMANHO_MIN_SENHA} caracteres): ")

        # confere o tamanho mínimo
        if len(senha) < TAMANHO_MIN_SENHA:
            print(f"Senha muito curta. Use pelo menos {TAMANHO_MIN_SENHA} caracteres.")
            continue

        # confere a digitação repetida
        if senha != getpass("Confirme a senha: "):
            print("As senhas não conferem. Digite novamente.")
            continue

        return senha


# este bloco só roda com "python funcionarios.py"
if __name__ == "__main__":
    print("=== Cadastro de funcionário ===")
    print("(Ctrl+C cancela a qualquer momento)")

    try:
        # cada função só devolve quando o valor estiver válido
        usuario = pedir_usuario()
        nome = pedir_nome()
        email = pedir_email()
        senha = pedir_senha()
    except KeyboardInterrupt:
        # Ctrl+C: encerra sem a mensagem de erro do Python
        print("\nCadastro cancelado.")
        exit()

    # grava no banco
    novo_id = cadastrar_funcionario(usuario, nome, email, senha)

    if novo_id is None:
        print(f"O usuário {usuario} acabou de ser usado por outro cadastro. Rode de novo.")
    else:
        print(f"Funcionário '{usuario}' cadastrado com sucesso! ID: {novo_id}")
