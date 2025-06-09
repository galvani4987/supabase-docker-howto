# Guia Completo: Supabase Self-Hosted com Docker em VPS Oracle ARM64

Este guia detalha o processo de instalação e configuração do Supabase em modo self-hosted, utilizando Docker e Docker Compose em um Servidor Privado Virtual (VPS) da Oracle Cloud Infrastructure (OCI) com arquitetura ARM64 (executando Ubuntu 24.04 LTS). Nossa jornada abordou e resolveu problemas comuns, como falhas de autenticação de banco de dados, problemas de criptografia com `VAULT_ENC_KEY`, e a configuração de HTTPS com Nginx e Let's Encrypt.

-----

## Tabela de Conteúdos

1.  [Introdução e Pré-requisitos](https://www.google.com/search?q=%231-introdu%C3%A7%C3%A3o-e-pr%C3%A9-requisitos)
2.  [Preparação do Servidor](https://www.google.com/search?q=%232-prepara%C3%A7%C3%A3o-do-servidor)
3.  [Instalação do Docker e Docker Compose](https://www.google.com/search?q=%233-instala%C3%A7%C3%A3o-do-docker-e-docker-compose)
4.  [Instalação do Core do Supabase](https://www.google.com/search?q=%234-instala%C3%A7%C3%A3o-do-core-do-supabase)
5.  [Geração das Chaves do Supabase](https://www.google.com/search?q=%235-gera%C3%A7%C3%A3o-das-chaves-do-supabase)
6.  [Configuração de Segurança (Firewall)](https://www.google.com/search?q=%236-configura%C3%A7%C3%A3o-de-seguran%C3%A7a-firewall)
7.  [Proxy Reverso Nginx & HTTPS (Let's Encrypt)](https://www.google.com/search?q=%237-proxy-reverso-nginx--https-lets-encrypt)
8.  [Arquivos de Configuração Modificados (Exemplos)](https://www.google.com/search?q=%238-arquivos-de-configura%C3%A7%C3%A3o-modificados-exemplos)

-----

### 1\. Introdução e Pré-requisitos

Este tutorial irá guiá-lo passo a passo na configuração do Supabase em seu próprio servidor, garantindo que ele esteja acessível e seguro.

**Pré-requisitos:**

  * **Oracle Cloud VPS:** Uma instância de Máquina Virtual (VM) na Oracle Cloud, executando Ubuntu 24.04 LTS com arquitetura ARM64.
  * **Acesso SSH:** Capacidade de se conectar à sua VPS via SSH com um usuário que tenha permissões `sudo`.
  * **Nome de Domínio:** Um domínio personalizado (ex: `seudominio.com`) configurado para apontar para o endereço IP público da sua VPS.
  * **Conhecimento Básico de Linux:** Familiaridade com operações de linha de comando.

-----

### 2\. Preparação do Servidor

Primeiro, vamos garantir que seu servidor esteja pronto para a instalação.

1.  Conecte-se à sua VPS via SSH.

2.  Colete informações do sistema (para referência):

    ```bash
    cat /etc/os-release
    uname -m
    lscpu | grep "Model name"
    free -h
    df -h
    ```

    *Isso confirma seu ambiente (ARM64 Ubuntu 24.04) e mostra informações de CPU, memória e disco.*

3.  Atualize os pacotes do sistema:

    ```bash
    sudo apt update && sudo apt upgrade -y
    ```

    *Mantenha seu sistema atualizado por segurança e compatibilidade.*

-----

### 3\. Instalação do Docker e Docker Compose

O Supabase depende do Docker e do Docker Compose para orquestrar seus vários serviços.

1.  Desinstale versões antigas do Docker (se houver):

    ```bash
    sudo apt remove docker docker-engine docker.io containerd runc
    ```

2.  Instale os pré-requisitos para o repositório Docker:

    ```bash
    sudo apt install ca-certificates curl apt-transport-https software-properties-common -y
    ```

3.  Adicione a chave GPG oficial do Docker:

    ```bash
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    ```

4.  Adicione o repositório Docker às fontes do APT:

    ```bash
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    ```

5.  Atualize o índice de pacotes do APT:

    ```bash
    sudo apt update
    ```

6.  Instale o Docker Engine, containerd e o plugin Docker Compose:

    ```bash
    sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
    ```

7.  Verifique a instalação do Docker:

    ```bash
    sudo docker run hello-world
    ```

    *Você deve ver a mensagem "Hello from Docker\!".*

8.  Adicione seu usuário ao grupo `docker`:

    ```bash
    sudo usermod -aG docker ${USER}
    ```

    **IMPORTANTE:** Você deve sair da sua sessão SSH e fazer login novamente para que essa alteração tenha efeito. Após reconectar, teste com `docker run hello-world` (agora sem `sudo`).

-----

### 4\. Instalação do Core do Supabase

Com o Docker configurado, vamos preparar e iniciar sua instância do Supabase.

1.  Clone o repositório do Supabase:

    ```bash
    git clone --depth 1 https://github.com/supabase/supabase
    ```

2.  Navegue até o diretório Docker do Supabase:

    ```bash
    cd supabase/docker
    ```

    *É crucial estar neste diretório, pois ele contém `docker-compose.yml` e `.env.example`.*

3.  Crie e edite o arquivo de variáveis de ambiente (`.env`):

    ```bash
    cp .env.example .env
    nano .env
    ```

    **PONTOS DE CONFIGURAÇÃO CRÍTICOS no `.env`:**

      * `VAULT_ENC_KEY` (Correção Essencial para o Supavisor):

          * Este é um ponto comum de falha, especialmente em ambientes ARM64. O Supavisor (pooler) espera uma chave de criptografia binária de exatamente 32 bytes.
          * Gere uma chave compatível (exatamente 32 caracteres alfanuméricos):
            ```bash
            openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c32; echo
            ```
          * Copie a saída e atualize a linha `VAULT_ENC_KEY` no arquivo `.env`.

      * `POSTGRES_PASSWORD`:

          * Inicialmente, use uma senha simples (apenas caracteres alfanuméricos). Caracteres especiais como `$` ou `@` podem causar problemas de interpretação.

      * `JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY`:

          * Por segurança, gere chaves longas e aleatórias para essas variáveis. Detalharemos como fazer isso na próxima seção.

4.  Limpe os dados antigos do banco de dados (CRÍTICO para redefinir a senha):
    *O PostgreSQL persiste seus dados em um diretório local. Você deve limpar este diretório para forçar a reinicialização com as novas senhas.*

    ```bash
    sudo rm -rf ./volumes/db/data/*
    mkdir -p ./volumes/db/data/
    ```

5.  Pare e remova contêineres e volumes antigos:
    *Este comando garante um início limpo com as novas configurações.*

    ```bash
    docker compose down --volumes --remove-orphans
    ```

6.  Inicie os serviços do Supabase:

    ```bash
    docker compose up -d
    ```

7.  Verifique o status de todos os contêineres:

    ```bash
    docker compose ps
    ```

    *Todos os serviços devem exibir o status `Up (healthy)` ou `Up`.*

-----

### 5\. Geração das Chaves do Supabase

Você precisará de três chaves principais: `JWT_SECRET`, `ANON_KEY` e `SERVICE_ROLE_KEY`.

#### 5.1. Gerar JWT\_SECRET (Linha de Comando)

Use o `openssl` para gerar uma string aleatória e forte:

```bash
openssl rand -hex 32
```

Copie esta saída. Este será o seu `JWT_SECRET`.

#### 5.2. Gerar ANON\_KEY e SERVICE\_ROLE\_KEY (Script Python)

As chaves `ANON_KEY` e `SERVICE_ROLE_KEY` são JWTs assinados com o seu `JWT_SECRET`.

##### 5.2.1. Criar um Ambiente Virtual Python

1.  Instale o `python3-venv`:
    ```bash
    sudo apt update
    sudo apt install python3-venv -y
    ```
2.  Crie e ative o ambiente virtual:
    ```bash
    python3 -m venv supabase_keys_env
    source supabase_keys_env/bin/activate
    ```

##### 5.2.2. Instalar pyjwt

Instale a biblioteca `pyjwt` no ambiente virtual ativado:

```bash
pip install pyjwt
```

##### 5.2.3. Criar e Executar o Script Python

1.  Crie o arquivo `generate_keys.py`:

    ```bash
    nano generate_keys.py
    ```

2.  Cole o seguinte código, substituindo `'YOUR_JWT_SECRET_..._HERE'` pelo `JWT_SECRET` real que você gerou:

    ```python
    import jwt

    # --- COLE SEU JWT_SECRET AQUI ---
    # Mantenha as aspas simples.
    jwt_secret = 'YOUR_JWT_SECRET_FROM_STEP_5.1_HERE'

    # --- Payloads (não precisa alterar) ---
    anon_payload = {'role': 'anon'}
    service_role_payload = {'role': 'service_role'}

    # --- Gerar os tokens ---
    anon_key = jwt.encode(anon_payload, jwt_secret, algorithm='HS256')
    service_role_key = jwt.encode(service_role_payload, jwt_secret, algorithm='HS256')

    # --- Imprimir os resultados ---
    print("\n--- SUAS CHAVES GERADAS ---")
    print("\n[ANON_KEY]")
    print(anon_key)
    print("\n[SERVICE_ROLE_KEY]")
    print(service_role_key)
    print("\nCopie e cole estes valores no seu arquivo .env\n")
    ```

3.  Execute o script:

    ```bash
    python3 generate_keys.py
    ```

4.  Copie as chaves `ANON_KEY` e `SERVICE_ROLE_KEY` geradas.

5.  Desative o ambiente virtual:

    ```bash
    deactivate
    ```

#### 5.3. Atualize seu arquivo .env do Supabase

Volte para o diretório `~/supabase/docker/`, abra o arquivo `.env` e cole as três chaves (`JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY`) em seus respectivos campos. Após salvar, reinicie os contêineres:

```bash
cd ~/supabase/docker/
docker compose down
docker compose up -d
```

-----

### 6\. Configuração de Segurança (Firewall)

#### 6.1. Oracle Cloud Firewall (Security Lists)

No painel da OCI, navegue até a *Security List* da sua instância e adicione as seguintes regras de entrada (Ingress Rules):

  * **Porta 22 (SSH):** `Source CIDR: 0.0.0.0/0`, `Protocol: TCP`, `Port: 22`
  * **Porta 80 (HTTP):** `Source CIDR: 0.0.0.0/0`, `Protocol: TCP`, `Port: 80`
  * **Porta 443 (HTTPS):** `Source CIDR: 0.0.0.0/0`, `Protocol: TCP`, `Port: 443`

#### 6.2. Firewall Local (UFW no Ubuntu)

1.  Verifique o status do UFW e ative-o se necessário:

    ```bash
    sudo ufw status
    sudo ufw enable
    ```

2.  Permita as portas necessárias:

    ```bash
    sudo ufw allow ssh
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    ```

3.  Recarregue o UFW:

    ```bash
    sudo ufw reload
    ```

-----

### 7\. Proxy Reverso Nginx & HTTPS (Let's Encrypt)

O Nginx atuará como ponto de entrada, roteando o tráfego para os serviços Docker e fornecendo HTTPS.

1.  **DNS:** Certifique-se de que seu domínio aponta para o IP público da sua VPS.

2.  Instale o Nginx:

    ```bash
    sudo apt install nginx -y
    ```

3.  Crie o arquivo de configuração do Nginx para o Supabase:

    ```bash
    sudo nano /etc/nginx/sites-available/supabase
    ```

    Cole a configuração abaixo, substituindo `seudominio.com` pelo seu domínio real.

4.  Ative a configuração e teste-a:

    ```bash
    sudo ln -s /etc/nginx/sites-available/supabase /etc/nginx/sites-enabled/
    sudo nginx -t
    ```

    Se tudo estiver OK, reinicie o Nginx: `sudo systemctl restart nginx`.

5.  Instale o Certbot e o plugin para Nginx:

    ```bash
    sudo apt install certbot python3-certbot-nginx -y
    ```

6.  Obtenha os certificados SSL com o Certbot:

    ```bash
    sudo certbot --nginx -d seudominio.com
    ```

    *Siga as instruções, inserindo seu e-mail e escolhendo a opção de redirecionar o tráfego HTTP para HTTPS.*

7.  **Ajuste Final da Configuração do Nginx:**
    O Certbot modificará seu arquivo. Verifique se o arquivo em `/etc/nginx/sites-available/supabase` corresponde ao exemplo na seção 8.2 abaixo e reinicie o Nginx.

8.  **Atualize o `.env` do Supabase:**
    No arquivo `~/supabase/docker/.env`, defina `SUPABASE_PUBLIC_URL` para o seu domínio com HTTPS:

    ```
    SUPABASE_PUBLIC_URL=https://seudominio.com
    ```

    Salve e reinicie os contêineres do Supabase:

    ```bash
    docker compose down
    docker compose up -d
    ```

    Agora você deve conseguir acessar o Supabase Studio em `https://seudominio.com`.

-----

### 8\. Arquivos de Configuração Modificados (Exemplos)

Aqui estão os conteúdos finais dos arquivos que foram modificados.

#### 8.1. `~/supabase/docker/.env` (Versão Final - Exemplo)

```dotenv
# Substitua com seus próprios valores
POSTGRES_PASSWORD=yoursecurepassword123
JWT_SECRET=YOUR_LONG_AND_RANDOM_JWT_SECRET_HERE
ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiJ9.YOUR_ANON_KEY_HERE
SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.YOUR_SERVICE_KEY_HERE
DASHBOARD_USERNAME=supabase
DASHBOARD_PASSWORD=yourstudiosimplepassword
VAULT_ENC_KEY=Your32AlphanumericKeyGoesHere

# URL pública do Supabase
SUPABASE_PUBLIC_URL=https://seudominio.com

# ... (outras configurações permanecem)
```

#### 8.2. `/etc/nginx/sites-available/supabase` (Versão Final)

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name seudominio.com;

    # Redireciona todo o tráfego HTTP para HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name seudominio.com;

    # Configurações de SSL geradas pelo Certbot
    ssl_certificate /etc/letsencrypt/live/seudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seudominio.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Proxy reverso para o Supabase Kong (API Gateway)
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        # Essencial para WebSockets
        proxy_set_header Connection "Upgrade";
    }
}
```
