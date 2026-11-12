# importa o os para ler as variáveis do .env
import os

# importa as ferramentas do Python para fazer pedidos HTTP (já vêm com o Python)
import urllib.request
import urllib.error
import urllib.parse

# importa a função que carrega o arquivo .env
from dotenv import load_dotenv

# lê o .env e coloca os valores nas variáveis de ambiente
load_dotenv()

# tempo máximo, em segundos, esperando a resposta da ESP32
TIMEOUT_SEGUNDOS = 3


def fechadura_configurada():
    """Devolve True se o .env tem o endereço e o token da ESP32."""
    return bool(os.getenv("ESP32_URL", "").strip()) and bool(os.getenv("ESP32_TOKEN", "").strip())


def abrir_porta():
    """Manda a ESP32 acionar a fechadura.
    Devolve (situacao, mensagem), onde situacao é:
    True  -> a ESP32 confirmou a abertura
    False -> a ESP32 recusou ou não respondeu
    None  -> fechadura não configurada no .env (sistema funciona sem abrir porta)"""
    if not fechadura_configurada():
        return (None, "fechadura não configurada")

    # monta o endereço: http://IP/abrir?token=...  (quote protege caracteres especiais)
    base = os.getenv("ESP32_URL").strip().rstrip("/")
    token = urllib.parse.quote(os.getenv("ESP32_TOKEN").strip())
    url = f"{base}/abrir?token={token}"

    try:
        # faz o pedido e espera no máximo TIMEOUT_SEGUNDOS
        with urllib.request.urlopen(url, timeout=TIMEOUT_SEGUNDOS) as resposta:
            corpo = resposta.read().decode("utf-8")
            return (resposta.status == 200, corpo)

    except urllib.error.HTTPError as erro:
        # a ESP32 respondeu, mas recusou (ex.: 403 = token errado)
        return (False, f"ESP32 recusou o comando (código {erro.code})")

    except urllib.error.URLError as erro:
        # não achou a ESP32 na rede (desligada, IP errado, Wi-Fi caiu)
        return (False, f"ESP32 não respondeu: {erro.reason}")

    except TimeoutError:
        # a ESP32 demorou mais que o tempo limite
        return (False, "ESP32 não respondeu a tempo")


# este bloco só roda com "python fechadura.py" (teste pelo terminal)
if __name__ == "__main__":
    situacao, mensagem = abrir_porta()
    print("Resultado:", situacao, "-", mensagem)
