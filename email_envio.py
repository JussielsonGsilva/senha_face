# importa o os para ler as variáveis do .env e criar pastas
import os

# importa o json para montar o corpo do pedido à API
import json

# importa o datetime para dar nome aos arquivos do modo de desenvolvimento
from datetime import datetime

# importa as ferramentas do Python para fazer pedidos HTTPS (já vêm com o Python)
import urllib.request
import urllib.error

# importa a função que carrega o arquivo .env
from dotenv import load_dotenv

# lê o .env e coloca os valores nas variáveis de ambiente
load_dotenv()

# endereço da API da Brevo para envio de e-mail
BREVO_URL = "https://api.brevo.com/v3/smtp/email"

# tempo máximo de espera pela resposta da API, em segundos
TIMEOUT_SEGUNDOS = 10

# pasta onde os e-mails são gravados no modo de desenvolvimento
PASTA_EMAILS_DEV = "logs/emails"


def enviar_email(destino, assunto, texto):
    """Envia um e-mail de texto. Devolve True se deu certo, False se falhou.
    Sem chave no .env, grava o e-mail em arquivo (modo de desenvolvimento)."""
    # lê a chave e o remetente do .env
    chave = os.getenv("EMAIL_API_CHAVE", "").strip()
    remetente = os.getenv("EMAIL_REMETENTE", "").strip()
    nome_remetente = os.getenv("EMAIL_REMETENTE_NOME", "Portaria").strip()

    # ---------- modo de desenvolvimento: sem chave, grava em arquivo ----------
    if not chave:
        # cria a pasta logs/emails se ainda não existir
        os.makedirs(PASTA_EMAILS_DEV, exist_ok=True)

        # nome do arquivo com data e hora (ex.: logs/emails/20261110-153000.txt)
        nome_arquivo = datetime.now().strftime("%Y%m%d-%H%M%S") + ".txt"
        caminho = os.path.join(PASTA_EMAILS_DEV, nome_arquivo)

        # grava destinatário, assunto e texto no arquivo
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(f"Para: {destino}\nAssunto: {assunto}\n\n{texto}\n")

        print(f"[modo desenvolvimento] e-mail gravado em {caminho}")
        return True

    # ---------- modo real: envia pela API da Brevo ----------

    # monta o corpo do pedido no formato que a Brevo espera
    corpo = {
        "sender": {"name": nome_remetente, "email": remetente},   # quem envia
        "to": [{"email": destino}],                               # quem recebe
        "subject": assunto,                                       # assunto
        "textContent": texto,                                     # texto do e-mail
    }

    # cria o pedido HTTPS do tipo POST, com o corpo em JSON
    pedido = urllib.request.Request(
        BREVO_URL,
        data=json.dumps(corpo).encode("utf-8"),   # transforma o dicionário em bytes JSON
        method="POST",
        headers={
            "api-key": chave,                     # autenticação na Brevo
            "Content-Type": "application/json",   # o corpo está em JSON
            "Accept": "application/json",         # queremos a resposta em JSON
        },
    )

    try:
        # envia o pedido e espera a resposta
        with urllib.request.urlopen(pedido, timeout=TIMEOUT_SEGUNDOS) as resposta:
            # a Brevo responde 201 (criado) quando aceita o e-mail
            return resposta.status in (200, 201, 202)

    except urllib.error.HTTPError as erro:
        # a Brevo recusou: mostra o código e a mensagem (a chave nunca é exibida)
        print(f"Erro da Brevo ({erro.code}): {erro.read().decode('utf-8', 'ignore')}")
        return False

    except urllib.error.URLError as erro:
        # sem internet, DNS ou tempo esgotado
        print(f"Falha de conexão com a Brevo: {erro.reason}")
        return False


# este bloco só roda com "python email_envio.py" (teste de envio)
if __name__ == "__main__":
    # pede o e-mail de destino do teste
    destino = input("Enviar e-mail de teste para: ").strip()

    # envia uma mensagem simples
    ok = enviar_email(
        destino,
        "Teste - Sistema de Portaria",
        "Se você recebeu esta mensagem, o envio de e-mail do sistema de portaria está funcionando.",
    )

    # mostra o resultado
    print("Envio OK!" if ok else "Falha no envio.")
