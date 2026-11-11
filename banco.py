# importa o módulo 'os' para ler variáveis de ambiente
import os

# importa a função que carrega o arquivo .env
from dotenv import load_dotenv

# importa o conector do MySQL
import mysql.connector

# lê o arquivo .env e coloca os valores nas variáveis de ambiente
load_dotenv()


def conectar():
    """Abre e devolve uma conexão com o banco portaria_facial."""
    # cria a conexão usando os dados do .env
    conexao = mysql.connector.connect(
        host=os.getenv("DB_HOST"),           # endereço do servidor (localhost)
        port=int(os.getenv("DB_PORT")),      # porta, convertida de texto para número
        user=os.getenv("DB_USER"),           # usuário portaria_app
        password=os.getenv("DB_PASSWORD"),   # senha do usuário
        database=os.getenv("DB_NAME"),       # banco portaria_facial
    )
    # devolve a conexão para quem chamou a função
    return conexao


# este bloco só roda quando você executa "python banco.py" diretamente
# (não roda quando outro arquivo fizer "import banco")
if __name__ == "__main__":
    # abre a conexão
    conexao = conectar()

    # cria um cursor, o objeto que envia comandos SQL ao banco
    cursor = conexao.cursor()

    # conta quantos moradores existem na tabela
    cursor.execute("SELECT COUNT(*) FROM moradores")

    # pega o resultado (uma linha com um número)
    total = cursor.fetchone()[0]

    # mostra o resultado no terminal
    print(f"Conexão OK! Moradores cadastrados: {total}")

    # fecha o cursor e a conexão para liberar recursos
    cursor.close()
    conexao.close()
