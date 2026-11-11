# importa a conexão com o banco
from banco import conectar

# importa as regras de bloqueio
from regras import (
    MAX_ERROS_POR_CODIGO,
    MAX_ERROS_PORTARIA,
    MINUTOS_BLOQUEIO,
    MOTIVO_CREDENCIAIS_INVALIDAS,
)

# trecho de SQL reaproveitado: data e hora do último desbloqueio
# (COALESCE devolve 1970-01-01 quando ainda não houve nenhum desbloqueio)
ULTIMO_DESBLOQUEIO = "(SELECT COALESCE(MAX(data_hora), '1970-01-01') FROM desbloqueios)"


def segundos_de_bloqueio(limite, codigo=None):
    """Devolve quantos segundos faltam para liberar (0 = não está bloqueado).
    codigo=None   -> conta erros de QUALQUER código (trava da portaria)
    codigo='1234' -> conta só os erros desse código (trava por código)

    Como funciona: pega o erro de número 'limite' (ex.: o 5º mais recente) dentro da janela,
    contando só erros DEPOIS do último desbloqueio. Se ele existe, há erros suficientes
    para bloquear, e a liberação acontece MINUTOS_BLOQUEIO depois dele."""
    # valores na MESMA ORDEM em que os %s aparecem no SQL
    valores = [MINUTOS_BLOQUEIO, MOTIVO_CREDENCIAIS_INVALIDAS, MINUTOS_BLOQUEIO]

    # filtro opcional pelo código
    filtro_codigo = ""
    if codigo is not None:
        filtro_codigo = "AND codigo_digitado = %s"
        valores.append(codigo)

    # OFFSET (limite - 1) pula os mais recentes e cai exatamente no erro de número 'limite'
    valores.append(limite - 1)

    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        f"""
        SELECT TIMESTAMPDIFF(SECOND, NOW(), data_hora + INTERVAL %s MINUTE)
        FROM acessos
        WHERE motivo = %s
          AND data_hora >= NOW() - INTERVAL %s MINUTE
          AND data_hora > {ULTIMO_DESBLOQUEIO}
          {filtro_codigo}
        ORDER BY data_hora DESC, id DESC
        LIMIT 1 OFFSET %s
        """,
        tuple(valores),
    )
    linha = cursor.fetchone()
    cursor.close()
    conexao.close()

    # sem o erro de número 'limite' na janela: não está bloqueado
    if linha is None:
        return 0

    # segundos que faltam (nunca negativo)
    return max(int(linha[0]), 0)


def verificar_bloqueio(codigo):
    """Confere as duas travas e devolve os segundos de bloqueio (0 = pode tentar).
    Vale também para códigos que não existem, para não revelar quais existem."""
    trava_codigo = segundos_de_bloqueio(MAX_ERROS_POR_CODIGO, codigo)
    trava_portaria = segundos_de_bloqueio(MAX_ERROS_PORTARIA)

    # se as duas estiverem ativas, vale a que demora mais para liberar
    return max(trava_codigo, trava_portaria)


def listar_codigos_bloqueados():
    """Devolve a lista de (codigo, segundos) dos códigos bloqueados agora."""
    conexao = conectar()
    cursor = conexao.cursor()

    # códigos com erros suficientes na janela (depois do último desbloqueio)
    cursor.execute(
        f"""
        SELECT codigo_digitado
        FROM acessos
        WHERE motivo = %s
          AND data_hora >= NOW() - INTERVAL %s MINUTE
          AND data_hora > {ULTIMO_DESBLOQUEIO}
        GROUP BY codigo_digitado
        HAVING COUNT(*) >= %s
        """,
        (MOTIVO_CREDENCIAIS_INVALIDAS, MINUTOS_BLOQUEIO, MAX_ERROS_POR_CODIGO),
    )
    codigos = [linha[0] for linha in cursor.fetchall()]
    cursor.close()
    conexao.close()

    # para cada código, calcula quanto falta; mantém só os que ainda estão bloqueados
    bloqueados = []
    for codigo in codigos:
        segundos = segundos_de_bloqueio(MAX_ERROS_POR_CODIGO, codigo)
        if segundos > 0:
            bloqueados.append((codigo, segundos))
    return bloqueados


def situacao_bloqueio():
    """Resumo para o painel: segundos da trava da portaria e lista de códigos bloqueados."""
    return {
        "portaria": segundos_de_bloqueio(MAX_ERROS_PORTARIA),
        "codigos": listar_codigos_bloqueados(),
    }


def desbloquear(funcionario_id):
    """Registra um desbloqueio feito pelo funcionário.
    Não apaga nada: a partir de agora, só contam os erros que acontecerem depois deste momento."""
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("INSERT INTO desbloqueios (funcionario_id) VALUES (%s)", (funcionario_id,))
    conexao.commit()
    cursor.close()
    conexao.close()
