# importa a conexão com o banco
from banco import conectar


def formatar_placa(placa):
    """Mostra a placa com hífen para leitura: ABC1D23 -> ABC-1D23."""
    if not placa:
        return ""
    return f"{placa[:3]}-{placa[3:]}"


def listar_moradores_veiculos(filtro=""):
    """Lista moradores com seus veículos (uma linha por veículo).
    Morador sem veículo aparece uma vez, com os campos do veículo vazios.
    O filtro procura no nome, bloco, apartamento, código, modelo, cor e placa."""
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    # o % antes e depois faz o LIKE achar o texto em qualquer parte (ex.: "silva" acha "Jussielson Silva")
    busca = f"%{filtro.strip()}%"

    # a placa é gravada sem hífen e em maiúsculas, então ajustamos o texto digitado
    busca_placa = f"%{filtro.strip().replace('-', '').upper()}%"

    # LEFT JOIN: traz o morador mesmo que ele não tenha veículo
    cursor.execute(
        """
        SELECT m.codigo, m.nome, m.bloco, m.apartamento,
               (m.rosto_embedding IS NOT NULL) AS tem_rosto,
               m.ativo,
               v.modelo, v.cor, v.placa
        FROM moradores m
        LEFT JOIN veiculos v ON v.morador_id = m.id
        WHERE m.nome LIKE %s
           OR m.apartamento LIKE %s
           OR m.bloco LIKE %s
           OR m.codigo LIKE %s
           OR v.modelo LIKE %s
           OR v.cor LIKE %s
           OR v.placa LIKE %s
        ORDER BY m.bloco, m.apartamento, m.nome
        """,
        # um valor para cada %s, na mesma ordem do WHERE
        (busca, busca, busca, busca, busca, busca, busca_placa),
    )

    linhas = cursor.fetchall()
    cursor.close()
    conexao.close()
    return linhas
