# importa a conexão com o banco
from banco import conectar

# quantidade máxima de linhas que o histórico devolve (as mais recentes)
LIMITE_HISTORICO = 500


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

    # o % antes e depois faz o LIKE achar o texto em qualquer parte
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


def listar_acessos(dias=None, resultado=None, busca=""):
    """Lista as tentativas de acesso, da mais recente para a mais antiga.
    dias      -> None = tudo; 1 = só hoje; 7 = últimos 7 dias; etc.
    resultado -> None = todos; 'LIBERADO' ou 'NEGADO'
    busca     -> procura no código digitado e no nome do morador"""
    # cada filtro escolhido vira uma condição do WHERE e um valor para o %s
    condicoes = []
    valores = []

    if dias is not None:
        # CURDATE() = hoje à meia-noite; "hoje" = a partir de hoje 00:00,
        # "7 dias" = a partir de 6 dias atrás 00:00 (hoje + 6 dias anteriores)
        condicoes.append("a.data_hora >= CURDATE() - INTERVAL %s DAY")
        valores.append(dias - 1)

    if resultado is not None:
        condicoes.append("a.resultado = %s")
        valores.append(resultado)

    if busca.strip():
        condicoes.append("(a.codigo_digitado LIKE %s OR m.nome LIKE %s)")
        valores.extend([f"%{busca.strip()}%", f"%{busca.strip()}%"])

    # junta as condições com AND; sem filtros, o WHERE fica sempre verdadeiro (1 = 1)
    where = " AND ".join(condicoes) if condicoes else "1 = 1"

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    # LEFT JOIN: traz a tentativa mesmo sem morador (código inexistente ou morador excluído)
    cursor.execute(
        f"""
        SELECT a.data_hora, a.codigo_digitado, a.resultado, a.motivo, a.nota_facial,
               m.nome, m.bloco, m.apartamento
        FROM acessos a
        LEFT JOIN moradores m ON m.id = a.morador_id
        WHERE {where}
        ORDER BY a.data_hora DESC, a.id DESC
        LIMIT {LIMITE_HISTORICO}
        """,
        tuple(valores),
    )

    linhas = cursor.fetchall()
    cursor.close()
    conexao.close()
    return linhas
