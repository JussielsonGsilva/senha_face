# Sistema de Portaria com Senha + Reconhecimento Facial

Sistema desktop em Python para controle de acesso em portarias de prédios e condomínios.
O morador digita o **código de acesso** e a **senha**, e a câmera confirma a identidade
por **reconhecimento facial**. O acesso só é liberado quando os três fatores conferem.

O sistema também tem um **painel do funcionário da portaria**, protegido por login com
**2FA por e-mail**, para consultar e cadastrar moradores e veículos.

> Projeto de portfólio desenvolvido em etapas.

---

## Como funciona

### Acesso do morador (tela da portaria)

1. O morador digita o **código** de 4 dígitos, que localiza o cadastro no banco.
2. Digita a **senha**, comparada com o hash bcrypt salvo no banco.
3. A câmera captura o rosto e gera uma assinatura facial (embedding).
4. A assinatura é comparada **apenas** com a do morador daquele código (verificação 1:1).
5. Se tudo confere, o acesso é liberado e registrado.

Na verificação 1:1, o sistema não procura o rosto entre todos os moradores: ele compara
só com uma pessoa. Isso deixa o processo mais rápido e reduz o risco de confundir alguém.

### Regras da verificação facial

| Parâmetro | Valor | Motivo |
|---|---|---|
| Nota mínima de semelhança | **0,50** | Nos testes, o morador ficou em ~0,93 e outra pessoa em ~0,20 |
| Frames seguidos aprovados | **5** | Evita liberar por um acerto isolado |
| Tempo limite | **10 s** | Sem confirmação nesse tempo, o acesso é negado |

Esses valores ficam no início do arquivo `acesso.py` e podem ser ajustados.

### Painel do funcionário

1. O funcionário informa **usuário e senha**.
2. Recebe por e-mail um **código de 6 dígitos**, válido por **5 minutos**.
3. Com o código confirmado, o painel abre com as abas:
   - **Moradores e veículos:** busca, cadastro, edição e exclusão de morador, e cadastro de veículo;
   - **Rosto:** cadastro (ou troca) do rosto do morador pela câmera;
   - **Histórico:** em construção.

### Regras de cadastro

| Regra | Valor |
|---|---|
| Código de acesso do morador | exatamente **4 dígitos** |
| Senha do morador | mínimo **8 caracteres** |
| Senha do funcionário | mínimo **8 caracteres** |
| Placa do veículo | padrão antigo (`ABC1234`) ou Mercosul (`ABC1D23`), única no sistema |

As regras do morador ficam centralizadas no arquivo `regras.py`.

---

## Tecnologias

| Item | Uso |
|---|---|
| Python 3.13 | Linguagem principal |
| OpenCV 5 | Acesso à webcam e processamento de imagem |
| YuNet (ONNX) | Detecção de rosto |
| SFace (ONNX) | Geração da assinatura facial (128 valores) |
| MySQL 8 | Banco de dados |
| bcrypt | Hash seguro das senhas e dos códigos 2FA |
| python-dotenv | Leitura das configurações do arquivo `.env` |
| PySide6 (Qt) | Interface desktop |
| Brevo (API) | Envio do código 2FA por e-mail |

---

## Requisitos

- Linux (testado no Ubuntu 22.04)
- Python 3.10 ou superior (desenvolvido no 3.13)
- MySQL 8 instalado e em execução
- Webcam
- Conta na [Brevo](https://www.brevo.com) com uma **chave de API** (opcional em desenvolvimento)

---

## Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/JussielsonGsilva/senha_face.git
cd senha_face
```

### 2. Criar e ativar o ambiente virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Se aparecer erro de `ensurepip`, instale o suporte a venv:

```bash
sudo apt install python3-venv
```

### 3. Instalar as bibliotecas

```bash
pip install -r requirements.txt
```

Se o PySide6 reclamar de `xcb-cursor0` ao abrir uma janela:

```bash
sudo apt install libxcb-cursor0
```

### 4. Baixar os modelos de reconhecimento facial

```bash
mkdir -p modelos
wget -O modelos/face_detection_yunet_2023mar.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
wget -O modelos/face_recognition_sface_2021dec.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx
```

Tamanhos esperados: cerca de **228 KB** (YuNet) e **37 MB** (SFace).

### 5. Criar o banco e o usuário no MySQL

```bash
sudo mysql
```

No prompt `mysql>`, troque a senha de exemplo por uma sua:

```sql
CREATE DATABASE portaria_facial CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'portaria_app'@'localhost' IDENTIFIED BY 'SuaSenhaForte123!';
GRANT ALL PRIVILEGES ON portaria_facial.* TO 'portaria_app'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 6. Criar as tabelas

```bash
mysql -u portaria_app -p portaria_facial < schema.sql
```

Tabelas criadas: `moradores`, `acessos`, `veiculos`, `funcionarios` e `codigos_2fa`.

### 7. Configurar o arquivo `.env`

Crie um arquivo `.env` na raiz do projeto com o conteúdo abaixo, usando a senha do passo 5:

```ini
# ===== BANCO DE DADOS =====
DB_HOST=localhost
DB_PORT=3306
DB_USER=portaria_app
DB_PASSWORD=SuaSenhaForte123!
DB_NAME=portaria_facial

# ===== E-MAIL (código 2FA pela API da Brevo) =====
# deixe vazia em desenvolvimento: o e-mail é gravado em logs/emails/
EMAIL_API_CHAVE=
EMAIL_REMETENTE=seu_email@exemplo.com
EMAIL_REMETENTE_NOME=Portaria
```

O `.env` está no `.gitignore` e **nunca** deve ser enviado ao GitHub.

**Sobre a chave da Brevo:**

- Use uma chave do tipo **API** (começa com `xkeysib-`), criada em
  **SMTP & API → Chaves API**. A chave do tipo SMTP (`xsmtpsib-`) não funciona.
- O e-mail remetente precisa estar **verificado** na Brevo.
- Se aparecer o erro *"unrecognised IP address"*, autorize o IP em
  **Configurações → Segurança → IPs autorizados**. Em internet residencial com IPv6
  o endereço muda sozinho; autorize a faixa (ex.: `2804:xxxx:xxxx:xxxx::/64`) ou
  desative o bloqueio para API durante o desenvolvimento.
- Em produção, com IP fixo na portaria, mantenha o bloqueio ativo e autorize só esse IP.

### 8. Cadastrar o primeiro funcionário

O primeiro acesso ao painel exige um funcionário cadastrado pelo terminal:

```bash
python funcionarios.py
```

Use um e-mail real: é nele que chega o código 2FA.

---

## Como usar

Todos os comandos rodam na pasta do projeto, com o `.venv` ativo.

### Tela da portaria (morador)

```bash
python tela_portaria.py
```

O morador digita **código** e **senha** (pelo teclado da tela ou do computador) e aperta
**ENTRAR**. Se estiverem corretos, a câmera liga e confirma o rosto. A faixa de status fica
**verde** (liberado) ou **vermelha** (negado) e a tela reinicia sozinha após 4 segundos.
Toda tentativa é gravada no histórico.

### Painel do funcionário

```bash
python painel_porteiro.py
```

Login com usuário, senha e código 2FA. No painel:

- **Buscar:** por nome, bloco, apartamento, código, modelo, cor ou placa;
- **+ Novo morador:** cadastra código, nome, bloco, apartamento e senha;
- **Editar morador** (ou dois cliques na linha): altera nome, bloco, apartamento, situação
  (Ativo/Inativo) e, opcionalmente, a senha. O código não pode ser alterado. Morador
  **inativo** não consegue entrar pela portaria;
- **Excluir morador:** mostra o que será apagado e exige digitar o código do morador para
  confirmar. Apaga cadastro, senha, rosto e veículos; o histórico de acessos é mantido
  sem identificação (`morador_id` vazio);
- **+ Novo veículo:** selecione o morador na tabela e informe modelo, cor e placa;
- **Aba Rosto:** digite o código, clique em **Buscar** (a câmera liga) e em
  **Iniciar captura**. O morador mexe a cabeça devagar enquanto o sistema tira 5 amostras;
  a média é salva e a câmera desliga. A câmera também desliga ao trocar de aba ou sair;
- **Sair:** volta para a tela de login.

### Outros comandos

| Comando | O que faz |
|---|---|
| `python funcionarios.py` | Cadastra um funcionário do painel (terminal) |
| `python moradores.py` | Cadastra um morador (terminal) |
| `python rosto.py` | Cadastra o rosto de um morador (**ESPAÇO** inicia a captura de 5 amostras, **Q** cancela) |
| `python acesso.py` | Fluxo da portaria pelo terminal (mesma lógica da tela) |
| `python autenticacao.py` | Testa o login com 2FA pelo terminal |
| `python email_envio.py` | Envia um e-mail de teste |
| `python banco.py` | Testa a conexão com o MySQL |
| `python painel_camera.py` | Mostra a câmera dentro de uma janela Qt (componente das telas) |
| `python teste_camera.py` | Testa se a webcam abre (tecla **Q** para sair) |
| `python teste_deteccao.py` | Mostra a detecção de rosto em tempo real |
| `python teste_comparacao.py` | Mostra ao vivo a nota de semelhança com o rosto salvo |
| `python teste_janela.py` | Testa se o PySide6 abre uma janela |

### Cadastro do rosto pelo terminal (alternativa)

O caminho principal é a aba **Rosto** do painel. Pelo terminal, rode `python rosto.py`, informe o código e aperte
**ESPAÇO** com a janela da câmera selecionada. Mexa a cabeça levemente: o sistema tira
**5 amostras** e salva a **média** delas, o que torna o reconhecimento mais estável com
mudanças de luz e de ângulo.

### Consultar o histórico de acessos

```bash
mysql -u portaria_app -p portaria_facial -e "SELECT id, morador_id, codigo_digitado, resultado, motivo, nota_facial, data_hora FROM acessos ORDER BY id DESC;"
```

| Coluna | Conteúdo |
|---|---|
| `morador_id` | Morador alvo da tentativa (`NULL` se o código não existe) |
| `codigo_digitado` | Código exatamente como foi digitado |
| `resultado` | `LIBERADO` ou `NEGADO` |
| `motivo` | Ex.: código ou senha inválidos, tempo esgotado, rosto confirmado |
| `nota_facial` | Melhor nota de semelhança (`NULL` se a câmera não abriu) |
| `data_hora` | Momento da tentativa |

---

## Estrutura do projeto

```
senha_face/
├── modelos/                 # modelos ONNX do YuNet e do SFace (baixados no passo 4, não versionados)
├── logs/                    # e-mails do modo de desenvolvimento (não versionado)
├── .env                     # credenciais e configurações (não versionado)
├── .gitignore               # arquivos que não vão para o GitHub
├── aba_rosto.py             # aba do painel para cadastrar o rosto pela câmera
├── acesso.py                # lógica do acesso: código + senha + rosto + registro
├── autenticacao.py          # login do funcionário e código 2FA
├── banco.py                 # conexão com o MySQL
├── consultas.py             # consultas usadas no painel
├── dialogo_editar_morador.py # formulário de edição de morador
├── dialogos.py              # formulários de novo morador e novo veículo
├── email_envio.py           # envio de e-mail pela API da Brevo
├── exclusao_morador.py      # exclusão de morador com confirmação
├── funcionarios.py          # cadastro de funcionários (terminal)
├── moradores.py             # cadastro de moradores com senha em hash
├── painel_camera.py         # componente Qt que exibe o vídeo da câmera
├── painel_porteiro.py       # painel do funcionário (abre após o login 2FA)
├── regras.py                # regras de cadastro (código e senha do morador)
├── requirements.txt         # bibliotecas e versões do projeto
├── rosto.py                 # detecção, assinatura facial e cadastro do rosto
├── schema.sql               # criação das tabelas
├── tela_login.py            # tela de login do funcionário com 2FA
├── tela_portaria.py         # interface da portaria para o morador
├── teste_camera.py          # teste da webcam
├── teste_comparacao.py      # teste da nota de semelhança facial
├── teste_deteccao.py        # teste de detecção de rosto
├── teste_janela.py          # teste de janela do PySide6
├── veiculos.py              # validação e cadastro de veículos
└── README.md
```

---

## Segurança e privacidade

**Senhas e dados**

- Senhas de moradores e funcionários guardadas com **bcrypt** (hash com sal, custo 12).
- Consultas SQL com parâmetros (`%s`), o que protege contra SQL injection.
- O usuário do banco tem acesso somente ao banco do projeto e somente a partir de `localhost`.
- Credenciais e chaves ficam fora do código, no arquivo `.env`.
- **Nenhuma foto é armazenada:** o banco guarda apenas a assinatura facial (128 números,
  512 bytes), e não é possível reconstruir o rosto a partir dela.

**Acesso do morador**

- **Mensagem genérica:** código inexistente e senha errada recebem a mesma resposta.
- A câmera **só abre depois** que código e senha estão corretos.
- O rosto precisa ser confirmado em **5 frames seguidos**, com **uma única pessoa** na câmera.
- **Auditoria:** toda tentativa é registrada, inclusive com código inexistente. A senha
  digitada **nunca** é gravada. O histórico é preservado mesmo se o morador for removido.

**Exclusão de morador**

- A exclusão exige digitar o código do morador para liberar o botão.
- Dados pessoais (cadastro, senha, rosto e veículos) são apagados; os registros de acesso
  ficam **anônimos**. Assim o condomínio mantém a trilha de segurança e um funcionário não
  consegue apagar um morador para sumir com as provas de um acesso.

**Login do funcionário (2FA)**

- Código de 6 dígitos gerado com `secrets` (gerador seguro) e guardado **em hash**.
- Validade de **5 minutos**, **uso único** e limite de **5 tentativas** por código.
- Pedir um novo código **invalida o anterior**; reenvio liberado só após 30 segundos.
- Usuário inexistente e senha errada levam **o mesmo tempo** para responder, o que impede
  descobrir usuários válidos medindo o tempo de resposta.
- O e-mail aparece **mascarado** na tela (ex.: `ju********@gmail.com`).

---

## Etapas do desenvolvimento

- [x] **Etapa 1:** ambiente virtual, OpenCV e teste da webcam
- [x] **Etapa 2:** banco MySQL, conexão e cadastro de moradores com bcrypt
- [x] **Etapa 3:** detecção de rosto (YuNet) e cadastro da assinatura facial (SFace)
- [x] **Etapa 4:** verificação de acesso (código + senha + rosto)
- [x] **Etapa 5:** registro de acessos (log) e cadastro facial com 5 amostras
- [ ] **Etapa 6:** interface desktop
  - [x] tela da portaria para o morador
  - [x] login do funcionário com 2FA por e-mail
  - [x] painel: moradores e veículos (busca, cadastro, edição e exclusão)
  - [x] painel: cadastro de rosto
  - [ ] painel: histórico de acessos
- [ ] **Etapa 7:** bloqueio por tentativas e detecção de foto (anti-spoofing)

---

## Autor

**Jussielson Gonçalves Silva**, Analista e Desenvolvedor de Sistemas
GitHub: [JussielsonGsilva](https://github.com/JussielsonGsilva)
