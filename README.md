# Complete Guide: Self-Hosted Supabase with Docker on Oracle ARM64 VPS

This guide details the process of installing and configuring self-hosted Supabase using Docker and Docker Compose on an Oracle Cloud Infrastructure (OCI) Virtual Private Server (VPS) with an ARM64 architecture (running Ubuntu 24.04 LTS). Our journey addressed and resolved common issues such as database authentication failures, `VAULT_ENC_KEY` encryption problems, and setting up HTTPS with Nginx and Let's Encrypt.

-----

## Table of Contents

1.  Introduction and Prerequisites
2.  Server Preparation
3.  Docker and Docker Compose Installation
4.  Supabase Core Installation
5.  Generating Supabase Keys
6.  Security Configuration (Firewall)
7.  Nginx Reverse Proxy & HTTPS (Let's Encrypt)
8.  Modified Configuration Files (Examples)

-----

### 1\. Introduction and Prerequisites

This tutorial will guide you step-by-step through setting up Supabase on your own server, ensuring it's accessible and secure.

**Prerequisites:**

  * **Oracle Cloud VPS:** A Virtual Machine (VM) instance on Oracle Cloud, running Ubuntu 24.04 LTS with an ARM64 architecture.
  * **SSH Access:** Ability to connect to your VPS via SSH with a user who has `sudo` permissions.
  * **Domain Name:** A custom domain (e.g., `yourdomain.com`) configured to point to your VPS's public IP address.
  * **Basic Linux Knowledge:** Familiarity with command-line operations.

-----

### 2\. Server Preparation

First, let's ensure your server is ready for the installation.

1.  Connect to your VPS via SSH.

2.  Gather system information (for reference):

    ```bash
    cat /etc/os-release
    uname -m
    lscpu | grep "Model name"
    free -h
    df -h
    ```

    *This confirms your environment (ARM64 Ubuntu 24.04), and shows CPU, memory, and disk info.*

3.  Update system packages:

    ```bash
    sudo apt update && sudo apt upgrade -y
    ```

    *Keep your system updated for security and compatibility.*

-----

### 3\. Docker and Docker Compose Installation

Supabase relies on Docker and Docker Compose to orchestrate its various services.

1.  Uninstall old Docker versions (if any):

    ```bash
    sudo apt remove docker docker-engine docker.io containerd runc
    ```

2.  Install prerequisites for the Docker repository:

    ```bash
    sudo apt install ca-certificates curl apt-transport-https software-properties-common -y
    ```

3.  Add the official Docker GPG key:

    ```bash
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    ```

4.  Add the Docker repository to APT sources:

    ```bash
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    ```

5.  Update the APT package index:

    ```bash
    sudo apt update
    ```

6.  Install Docker Engine, containerd, and the Docker Compose Plugin:

    ```bash
    sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
    ```

7.  Verify the Docker installation:

    ```bash
    sudo docker run hello-world
    ```

    *You should see the "Hello from Docker\!" message.*

8.  Add your user to the `docker` group:

    ```bash
    sudo usermod -aG docker ${USER}
    ```

    **IMPORTANT:** You must log out of your SSH session and log back in for this change to take effect. After reconnecting, test with `docker run hello-world` (now without `sudo`).

-----

### 4\. Supabase Core Installation

With Docker configured, let's prepare and start your Supabase instance.

1.  Clone the Supabase repository:

    ```bash
    git clone --depth 1 https://github.com/supabase/supabase
    ```

2.  Navigate to the Supabase Docker directory:

    ```bash
    cd supabase/docker
    ```

    *It's crucial to be in this directory as it contains `docker-compose.yml` and `.env.example`.*

3.  Create and edit the environment variables file (`.env`):

    ```bash
    cp .env.example .env
    nano .env
    ```

    **CRITICAL CONFIGURATION POINTS in `.env`:**

      * `VAULT_ENC_KEY` (Essential Fix for Supavisor):

          * This is a common point of failure, especially on ARM64 environments. The Supavisor (pooler) expects a binary encryption key of exactly 32 bytes.
          * Generate a compatible key (exactly 32 alphanumeric characters):
            ```bash
            openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c32; echo
            ```
          * Copy the output and update the `VAULT_ENC_KEY` line in the `.env` file.

      * `POSTGRES_PASSWORD`:

          * Initially, use a simple password (alphanumeric characters only). Special characters like `$` or `@` can cause parsing issues.

      * `JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY`:

          * For security, generate long, random keys for these variables. We'll detail how to do this in the next section.

4.  Clear old database data (CRITICAL for password reset):
    *PostgreSQL persists its data in a local directory. You must clear this directory to force re-initialization with the new passwords.*

    ```bash
    sudo rm -rf ./volumes/db/data/*
    mkdir -p ./volumes/db/data/
    ```

5.  Stop and remove old containers and volumes:
    *This command ensures a clean slate with the new configurations.*

    ```bash
    docker compose down --volumes --remove-orphans
    ```

6.  Start Supabase services:

    ```bash
    docker compose up -d
    ```

7.  Verify the status of all containers:

    ```bash
    docker compose ps
    ```

    *All services should show the status `Up (healthy)` or `Up`.*

-----

### 5\. Generating Supabase Keys

You'll need three primary keys: `JWT_SECRET`, `ANON_KEY`, and `SERVICE_ROLE_KEY`.

#### 5.1. Generate JWT\_SECRET (Command Line)

Use `openssl` to generate a strong, random string:

```bash
openssl rand -hex 32
```

Copy this output. This will be your `JWT_SECRET`.

#### 5.2. Generate ANON\_KEY and SERVICE\_ROLE\_KEY (Python Script)

The `ANON_KEY` and `SERVICE_ROLE_KEY` are JWTs signed with your `JWT_SECRET`.

##### 5.2.1. Create a Python Virtual Environment

1.  Install `python3-venv`:
    ```bash
    sudo apt update
    sudo apt install python3-venv -y
    ```
2.  Create and activate the virtual environment:
    ```bash
    python3 -m venv supabase_keys_env
    source supabase_keys_env/bin/activate
    ```

##### 5.2.2. Install pyjwt

Install the `pyjwt` library in the activated virtual environment:

```bash
pip install pyjwt
```

##### 5.2.3. Create and Run the Python Script

1.  Create the `generate_keys.py` file:

    ```bash
    nano generate_keys.py
    ```

2.  Paste the following code, replacing `'YOUR_JWT_SECRET_..._HERE'` with the actual `JWT_SECRET` you generated:

    ```python
    import jwt

    # --- PASTE YOUR JWT_SECRET HERE ---
    # Keep the single quotes around it.
    jwt_secret = 'YOUR_JWT_SECRET_FROM_STEP_5.1_HERE'

    # --- Payloads (no need to change) ---
    anon_payload = {'role': 'anon'}
    service_role_payload = {'role': 'service_role'}

    # --- Generate the tokens ---
    anon_key = jwt.encode(anon_payload, jwt_secret, algorithm='HS256')
    service_role_key = jwt.encode(service_role_payload, jwt_secret, algorithm='HS256')

    # --- Print the results ---
    print("\n--- YOUR GENERATED KEYS ---")
    print("\n[ANON_KEY]")
    print(anon_key)
    print("\n[SERVICE_ROLE_KEY]")
    print(service_role_key)
    print("\nCopy and paste these values into your .env file\n")
    ```

3.  Run the script:

    ```bash
    python3 generate_keys.py
    ```

4.  Copy the generated `ANON_KEY` and `SERVICE_ROLE_KEY`.

5.  Deactivate the virtual environment:

    ```bash
    deactivate
    ```

#### 5.3. Update Your Supabase .env File

Navigate back to the `~/supabase/docker/` directory, open the `.env` file, and paste the three keys (`JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY`) into their respective fields. After saving, restart the containers:

```bash
cd ~/supabase/docker/
docker compose down
docker compose up -d
```

-----

### 6\. Security Configuration (Firewall)

#### 6.1. Oracle Cloud Firewall (Security Lists)

In the OCI dashboard, navigate to your instance's *Security List* and add the following Ingress Rules:

  * **Port 22 (SSH):** `Source CIDR: 0.0.0.0/0`, `Protocol: TCP`, `Port: 22`
  * **Port 80 (HTTP):** `Source CIDR: 0.0.0.0/0`, `Protocol: TCP`, `Port: 80`
  * **Port 443 (HTTPS):** `Source CIDR: 0.0.0.0/0`, `Protocol: TCP`, `Port: 443`

#### 6.2. Local Firewall (UFW on Ubuntu)

1.  Check UFW status and enable it if necessary:

    ```bash
    sudo ufw status
    sudo ufw enable
    ```

2.  Allow the necessary ports:

    ```bash
    sudo ufw allow ssh
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    ```

3.  Reload UFW:

    ```bash
    sudo ufw reload
    ```

-----

### 7\. Nginx Reverse Proxy & HTTPS (Let's Encrypt)

Nginx will act as the entry point, routing traffic to Docker services and providing HTTPS.

1.  **DNS:** Ensure your domain points to your VPS's public IP.

2.  Install Nginx:

    ```bash
    sudo apt install nginx -y
    ```

3.  Create the Nginx configuration file for Supabase:

    ```bash
    sudo nano /etc/nginx/sites-available/supabase
    ```

    Paste the configuration below, replacing `yourdomain.com` with your actual domain.

4.  Enable and test the configuration:

    ```bash
    sudo ln -s /etc/nginx/sites-available/supabase /etc/nginx/sites-enabled/
    sudo nginx -t
    ```

    If everything is OK, restart Nginx: `sudo systemctl restart nginx`.

5.  Install Certbot and the Nginx plugin:

    ```bash
    sudo apt install certbot python3-certbot-nginx -y
    ```

6.  Obtain SSL certificates with Certbot:

    ```bash
    sudo certbot --nginx -d yourdomain.com
    ```

    *Follow the prompts, entering your email and choosing the option to redirect HTTP traffic to HTTPS.*

7.  **Final Nginx Configuration Adjustment:**
    Certbot will modify your file. Verify that the file at `/etc/nginx/sites-available/supabase` matches the example in section 8.2 below and restart Nginx.

8.  **Update Supabase `.env`:**
    In the `~/supabase/docker/.env` file, set `SUPABASE_PUBLIC_URL` to your domain with HTTPS:

    ```
    SUPABASE_PUBLIC_URL=https://yourdomain.com
    ```

    Save and restart the Supabase containers:

    ```bash
    docker compose down
    docker compose up -d
    ```

    You should now be able to access Supabase Studio at `https://yourdomain.com`.

-----

### 8\. Modified Configuration Files (Examples)

Here are the final contents of the modified files.

#### 8.1. `~/supabase/docker/.env` (Final Version - Example)

```dotenv
# Replace with your own values
POSTGRES_PASSWORD=yoursecurepassword123
JWT_SECRET=YOUR_LONG_AND_RANDOM_JWT_SECRET_HERE
ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiJ9.YOUR_ANON_KEY_HERE
SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.YOUR_SERVICE_KEY_HERE
DASHBOARD_USERNAME=supabase
DASHBOARD_PASSWORD=yourstudiosimplepassword
VAULT_ENC_KEY=Your32AlphanumericKeyGoesHere

# Supabase public URL
SUPABASE_PUBLIC_URL=https://yourdomain.com

# ... (other settings remain)
```

#### 8.2. `/etc/nginx/sites-available/supabase` (Final Version)

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com;

    # Redirect all HTTP traffic to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com;

    # SSL certificate settings generated by Certbot
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Reverse proxy to Supabase Kong (API Gateway)
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
        # Essential for WebSockets
        proxy_set_header Connection "Upgrade";
    }
}
```

