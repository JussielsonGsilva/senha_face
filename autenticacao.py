# importa o secrets: gera números aleatórios seguros (próprios para códigos de acesso)
import secrets

# importa o bcrypt para conferir senhas e gerar o hash do código
import bcrypt

# importa o getpass para ler a senha sem mostrar na tela (usado no teste)
from getpass import getpass

# importa a conexão com o banco
from banco import conectar

# importa a função de envio de e-mail criada na etapa 6.8
from email_envio import enviar_email

# quantos dígitos tem o código 2FA
DIGITOS_CODIGO = 6

# por quantos minutos o código vale
VALIDADE_MINUTOS = 5

# quantas tentativas erradas são permitidas por código
MAX_TENTATIVAS = 5

# hash "de mentira", usado quando o usuário não existe
# (faz a resposta demorar o mesmo tempo, sem revelar quais usuários existem)
HASH_FALSO = bcrypt.hashpw(b"senha-que-nao-existe", bcrypt.gensalt()).decode("utf-8")


def mascarar_email(email):
    """Esconde parte do e-mail para mostrar na tela. Ex.: jussielson@gmail.com -> ju********@gmail.com"""
    # separa o que vem antes e depois do @
    nome, dominio = email.split("@", 1)

    # mostra só as 2 primeiras letras do nome e troca o resto por asteriscos
    return nome[:2] + "*" * max(len(nome) - 2, 1) + "@" + dominio


def verificar_login(usuario, senha):
    """Confere usuário e senha do funcionário.
    Devolve um dicionário com id, nome e email se estiver certo, ou None."""
    conexao = conectar()

    # dictionary=True faz o cursor devolver cada linha como dicionário (acesso por nome da coluna)
    cursor = conexao.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, nome, email, senha_hash FROM funcionarios WHERE usuario = %s AND ativo = 1",
        (usuario,),
    )
    funcionario = cursor.fetchone()
    cursor.close()
    conexao.close()

    # usuário não existe: compara com o hash falso só para gastar o mesmo tempo
    if funcionario is None:
        bcrypt.checkpw(senha.encode("utf-8"), HASH_FALSO.encode("utf-8"))
        return None

    # senha errada
    if not bcrypt.checkpw(senha.encode("utf-8"), funcionario["senha_hash"].encode("utf-8")):
        return None

    # tudo certo: devolve os dados, sem o hash da senha
    return {"id": funcionario["id"], "nome": funcionario["nome"], "email": funcionario["email"]}


def gerar_e_enviar_codigo(funcionario):
    """Gera um código de 6 dígitos, guarda o hash no banco e envia por e-mail.
    Devolve True se o e-mail foi enviado."""
    # gera um número aleatório seguro de 0 a 999999 e completa com zeros à esquerda (ex.: 004213)
    codigo = f"{secrets.randbelow(10 ** DIGITOS_CODIGO):0{DIGITOS_CODIGO}d}"

    # hash do código: nem quem tem acesso ao banco consegue ver o código
    codigo_hash = bcrypt.hashpw(codigo.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    conexao = conectar()
    cursor = conexao.cursor()

    # invalida códigos anteriores ainda não usados deste funcionário
    cursor.execute(
        "UPDATE codigos_2fa SET usado = 1 WHERE funcionario_id = %s AND usado = 0",
        (funcionario["id"],),
    )

    # grava o novo código; a validade usa o relógio do próprio MySQL (NOW())
    cursor.execute(
        """
        INSERT INTO codigos_2fa (funcionario_id, codigo_hash, expira_em)
        VALUES (%s, %s, NOW() + INTERVAL %s MINUTE)
        """,
        (funcionario["id"], codigo_hash, VALIDADE_MINUTOS),
    )

    conexao.commit()
    cursor.close()
    conexao.close()

    # monta o texto do e-mail
    texto = (
        f"Olá, {funcionario['nome']}.\n\n"
        f"Seu código de acesso ao painel da portaria é: {codigo}\n\n"
        f"Ele vale por {VALIDADE_MINUTOS} minutos e só pode ser usado uma vez.\n"
        f"Se não foi você que tentou entrar, avise a administração."
    )

    # envia e devolve se deu certo
    return enviar_email(funcionario["email"], "Código de acesso - Portaria", texto)


def verificar_codigo(funcionario_id, codigo_digitado):
    """Confere o código 2FA. Devolve uma destas situações:
    'ok'        -> código certo (e agora queimado)
    'incorreto' -> código errado, ainda há tentativas
    'bloqueado' -> errou demais, precisa pedir outro código
    'expirado'  -> não há código válido (venceu ou já foi usado)"""
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    # busca o código mais recente, ainda não usado e dentro da validade
    cursor.execute(
        """
        SELECT id, codigo_hash, tentativas FROM codigos_2fa
        WHERE funcionario_id = %s AND usado = 0 AND expira_em > NOW()
        ORDER BY id DESC LIMIT 1
        """,
        (funcionario_id,),
    )
    registro = cursor.fetchone()

    # nenhum código válido
    if registro is None:
        cursor.close()
        conexao.close()
        return "expirado"

    # código certo: queima o código (não pode ser usado de novo)
    if bcrypt.checkpw(codigo_digitado.encode("utf-8"), registro["codigo_hash"].encode("utf-8")):
        cursor.execute("UPDATE codigos_2fa SET usado = 1 WHERE id = %s", (registro["id"],))
        situacao = "ok"
    else:
        # código errado: soma uma tentativa
        tentativas = registro["tentativas"] + 1

        # chegou no limite: queima o código
        if tentativas >= MAX_TENTATIVAS:
            cursor.execute(
                "UPDATE codigos_2fa SET tentativas = %s, usado = 1 WHERE id = %s",
                (tentativas, registro["id"]),
            )
            situacao = "bloqueado"
        else:
            cursor.execute(
                "UPDATE codigos_2fa SET tentativas = %s WHERE id = %s",
                (tentativas, registro["id"]),
            )
            situacao = "incorreto"

    conexao.commit()
    cursor.close()
    conexao.close()
    return situacao


# este bloco só roda com "python autenticacao.py" (teste pelo terminal)
if __name__ == "__main__":
    print("=== Login do funcionário (teste) ===")

    # passo 1: usuário e senha
    usuario = input("Usuário: ").strip().lower()
    senha = getpass("Senha: ")

    funcionario = verificar_login(usuario, senha)
    if funcionario is None:
        print("Usuário ou senha inválidos.")
        exit()

    # passo 2: gera e envia o código
    if not gerar_e_enviar_codigo(funcionario):
        print("Não foi possível enviar o código por e-mail. Tente novamente.")
        exit()

    print(f"Código enviado para {mascarar_email(funcionario['email'])}")

    # passo 3: confere o código até acertar ou bloquear
    while True:
        codigo = input("Código recebido: ").strip()
        situacao = verificar_codigo(funcionario["id"], codigo)

        if situacao == "ok":
            print(f"Login liberado. Bem-vindo(a), {funcionario['nome']}!")
            break
        if situacao == "incorreto":
            print("Código incorreto. Tente novamente.")
            continue
        if situacao == "bloqueado":
            print("Muitas tentativas. Faça o login de novo para receber outro código.")
            break
        if situacao == "expirado":
            print("Código expirado ou já usado. Faça o login de novo.")
            break
