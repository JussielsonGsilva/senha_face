-- =====================================================================
-- MORADORES
-- =====================================================================
CREATE TABLE IF NOT EXISTS moradores (
    -- número interno do morador, gerado automaticamente pelo MySQL
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- código curto que o morador digita no teclado (4 dígitos, regra em regras.py); não pode repetir
    codigo VARCHAR(10) NOT NULL UNIQUE,

    -- nome completo do morador
    nome VARCHAR(100) NOT NULL,

    -- bloco do prédio (pode ficar vazio se o condomínio não tiver blocos)
    bloco VARCHAR(10) NULL,

    -- número do apartamento
    apartamento VARCHAR(10) NOT NULL,

    -- senha guardada com hash bcrypt (nunca a senha pura)
    senha_hash VARCHAR(255) NOT NULL,

    -- "assinatura" numérica do rosto; fica vazia até o cadastro do rosto
    rosto_embedding BLOB NULL,

    -- 1 = morador ativo, 0 = desativado (mudou-se, por exemplo)
    ativo TINYINT(1) NOT NULL DEFAULT 1,

    -- data e hora do cadastro, preenchida automaticamente
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =====================================================================
-- REGISTRO DE ACESSOS
-- =====================================================================
CREATE TABLE IF NOT EXISTS acessos (
    -- número interno do registro
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- morador identificado; fica NULL quando o código digitado não existe
    morador_id INT NULL,

    -- código exatamente como foi digitado (mesmo que não exista)
    codigo_digitado VARCHAR(10) NOT NULL,

    -- resultado final da tentativa: só aceita esses dois valores
    resultado ENUM('LIBERADO', 'NEGADO') NOT NULL,

    -- motivo do resultado (ex.: "código ou senha inválidos", "tempo esgotado")
    motivo VARCHAR(100) NOT NULL,

    -- melhor nota facial obtida (NULL quando a câmera nem chegou a abrir)
    nota_facial DECIMAL(4,3) NULL,

    -- data e hora da tentativa, preenchida automaticamente
    data_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- índice para buscar rápido por período (também acelera a limpeza e o bloqueio)
    INDEX idx_data_hora (data_hora),

    -- liga ao morador; se o morador for apagado, o histórico fica e o campo vira NULL
    CONSTRAINT fk_acessos_morador FOREIGN KEY (morador_id)
        REFERENCES moradores (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =====================================================================
-- VEÍCULOS DOS MORADORES (um morador pode ter vários)
-- =====================================================================
CREATE TABLE IF NOT EXISTS veiculos (
    -- número interno do veículo
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- dono do veículo
    morador_id INT NOT NULL,

    -- modelo (ex.: "Onix", "CG 160")
    modelo VARCHAR(50) NOT NULL,

    -- cor (ex.: "Prata")
    cor VARCHAR(30) NOT NULL,

    -- placa sem hífen, em maiúsculas (ex.: ABC1D23); não pode repetir
    placa VARCHAR(8) NOT NULL UNIQUE,

    -- data e hora do cadastro
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- se o morador for apagado, os veículos dele são apagados junto
    CONSTRAINT fk_veiculos_morador FOREIGN KEY (morador_id)
        REFERENCES moradores (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =====================================================================
-- FUNCIONÁRIOS (quem usa o painel do porteiro)
-- =====================================================================
CREATE TABLE IF NOT EXISTS funcionarios (
    -- número interno do funcionário
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- nome de usuário para o login (ex.: "joao.silva"); não pode repetir
    usuario VARCHAR(30) NOT NULL UNIQUE,

    -- nome completo
    nome VARCHAR(100) NOT NULL,

    -- e-mail que recebe o código 2FA
    email VARCHAR(120) NOT NULL,

    -- senha com hash bcrypt
    senha_hash VARCHAR(255) NOT NULL,

    -- 1 = pode entrar no painel, 0 = bloqueado
    ativo TINYINT(1) NOT NULL DEFAULT 1,

    -- data e hora do cadastro
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =====================================================================
-- CÓDIGOS 2FA ENVIADOS POR E-MAIL
-- =====================================================================
CREATE TABLE IF NOT EXISTS codigos_2fa (
    -- número interno do código
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- funcionário que pediu o código
    funcionario_id INT NOT NULL,

    -- código de 6 dígitos guardado com hash bcrypt (nunca o código puro)
    codigo_hash VARCHAR(255) NOT NULL,

    -- até quando o código vale (5 minutos depois de enviado)
    expira_em DATETIME NOT NULL,

    -- quantas vezes erraram este código (bloqueia após o limite)
    tentativas INT NOT NULL DEFAULT 0,

    -- 1 = já foi usado com sucesso e não vale mais
    usado TINYINT(1) NOT NULL DEFAULT 0,

    -- data e hora do envio
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- se o funcionário for apagado, os códigos dele saem junto
    CONSTRAINT fk_codigos_funcionario FOREIGN KEY (funcionario_id)
        REFERENCES funcionarios (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =====================================================================
-- DESBLOQUEIOS DA PORTARIA (feitos pelo funcionário no painel)
-- O bloqueio só conta os erros que aconteceram DEPOIS do último desbloqueio.
-- Os erros antigos continuam no histórico (nada é apagado).
-- =====================================================================
CREATE TABLE IF NOT EXISTS desbloqueios (
    -- número interno do desbloqueio
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- funcionário que desbloqueou; se o funcionário for apagado, o registro fica e o campo vira NULL
    funcionario_id INT NULL,

    -- data e hora do desbloqueio
    data_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- índice para achar rápido o último desbloqueio
    INDEX idx_desbloqueio_data (data_hora),

    CONSTRAINT fk_desbloqueios_funcionario FOREIGN KEY (funcionario_id)
        REFERENCES funcionarios (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =====================================================================
-- RETENÇÃO DE DADOS (LGPD): limpeza automática diária
-- Os EVENTs rodam dentro do próprio MySQL, mesmo com o sistema fechado.
-- Exigem o agendador ligado (event_scheduler = ON, padrão no MySQL 8).
-- =====================================================================

-- apaga tentativas de acesso com mais de 365 dias, todo dia às 03:00
CREATE EVENT IF NOT EXISTS limpar_acessos_antigos
    ON SCHEDULE EVERY 1 DAY
    STARTS (CURRENT_DATE + INTERVAL 1 DAY + INTERVAL 3 HOUR)
    COMMENT 'Retenção LGPD: mantém só os últimos 365 dias de histórico de acessos'
    DO DELETE FROM acessos WHERE data_hora < NOW() - INTERVAL 365 DAY;

-- apaga códigos 2FA criados há mais de 1 dia (já vencidos ou usados), todo dia às 03:00
CREATE EVENT IF NOT EXISTS limpar_codigos_2fa
    ON SCHEDULE EVERY 1 DAY
    STARTS (CURRENT_DATE + INTERVAL 1 DAY + INTERVAL 3 HOUR)
    COMMENT 'Remove códigos 2FA que não servem mais (validade de 5 minutos)'
    DO DELETE FROM codigos_2fa WHERE criado_em < NOW() - INTERVAL 1 DAY;

-- apaga registros de desbloqueio com mais de 365 dias, todo dia às 03:00
CREATE EVENT IF NOT EXISTS limpar_desbloqueios_antigos
    ON SCHEDULE EVERY 1 DAY
    STARTS (CURRENT_DATE + INTERVAL 1 DAY + INTERVAL 3 HOUR)
    COMMENT 'Retenção LGPD: mantém só os últimos 365 dias de desbloqueios'
    DO DELETE FROM desbloqueios WHERE data_hora < NOW() - INTERVAL 365 DAY;
