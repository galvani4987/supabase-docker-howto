# Definitive Guide: Self-Hosted Supabase with Docker, Nginx, and HTTPS

This guide provides a complete, optimized, step-by-step process for installing and configuring a self-hosted Supabase instance using Docker. The process covers everything from server preparation to setting up a reverse proxy with Nginx and securing it with a Let's Encrypt SSL/HTTPS certificate, resulting in a production-ready instance.

This method has been validated on an **Oracle Cloud ARM64 server running Ubuntu 24.04 LTS**.

## Table of Contents

1.  [Prerequisites](#1-prerequisites)
2.  [Step 1: Server Preparation](#2-step-1-server-preparation)
3.  [Step 2: Docker and Docker Compose Installation](#3-step-2-docker-and-docker-compose-installation)
4.  [Step 3: Supabase Setup and Key Generation](#4-step-3-supabase-setup-and-key-generation)
5.  [Step 4: Initial Supabase Launch](#5-step-4-initial-supabase-launch)
6.  [Step 5: Firewall Configuration](#6-step-5-firewall-configuration)
7.  [Step 6: Nginx Reverse Proxy and HTTPS Setup](#7-step-6-nginx-reverse-proxy-and-https-setup)
8.  [Conclusion and Access](#8-conclusion-and-access)

---

### 1. Prerequisites

* **Cloud Server:** A VM instance, such as from Oracle Cloud, with Ubuntu 24.04 LTS.
* **SSH Access:** The ability to connect to your server via SSH with a user that has `sudo` privileges.
* **Domain Name:** A domain (e.g., `supabase.your-domain.com`) with a DNS `A` record pointing to your server's public IP address.

> **Note:** Throughout this guide, remember to replace `supabase.your-domain.com` with your actual domain.

---

### 2. Step 1: Server Preparation

Connect to your server and ensure all packages are up-to-date.

```bash
sudo apt update && sudo apt upgrade -y
```

---

### 3. Step 2: Docker and Docker Compose Installation

Supabase uses Docker to orchestrate its microservices.

1.  **Install Docker dependencies:**
    ```bash
    sudo apt install ca-certificates curl apt-transport-https software-properties-common -y
    ```

2.  **Add Docker's official GPG key:**
    ```bash
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    ```

3.  **Set up the Docker repository:**
    ```bash
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    ```

4.  **Install Docker Engine and Docker Compose:**
    ```bash
    sudo apt update
    sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
    ```

5.  **Add your user to the `docker` group to run Docker commands without `sudo`:**
    ```bash
    sudo usermod -aG docker ${USER}
    ```
    > **IMPORTANT:** You must log out and log back into your SSH session for this change to take effect. Afterwards, verify by running `docker ps`.

---

### 4. Step 3: Supabase Setup and Key Generation

In this step, we will prepare all secrets and configurations *before* launching Supabase for the first time.

1.  **Clone the official Supabase repository:**
    ```bash
    git clone --depth 1 https://github.com/supabase/supabase
    ```

2.  **Navigate into the `docker` directory:**
    ```bash
    cd supabase/docker
    ```

3.  **Copy the example environment file:**
    ```bash
    cp .env.example .env
    ```

4.  **Generate all required keys and secrets:**
    Execute the commands below and save each output.

    * **Generate `POSTGRES_PASSWORD`:**
        ```bash
        openssl rand -base64 32
        ```
    * **Generate `JWT_SECRET`:**
        ```bash
        openssl rand -hex 32
        ```
    * **Generate `VAULT_ENC_KEY` (CRITICAL for ARM64):**
        ```
        # The Supavisor requires a key of exactly 32 alphanumeric bytes.
        ```
        ```bash
        openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c32; echo
        ```

5.  **Update the `.env` file with the generated keys:**
    ```
    # Open the .env file for editing.
    ```
    ```bash
    nano .env
    ```
    Locate and replace the values for the following variables with the keys you just generated. Also, set a password for the dashboard and define your final public URL.
    * `POSTGRES_PASSWORD=`
    * `JWT_SECRET=`
    * `VAULT_ENC_KEY=`
    * `DASHBOARD_PASSWORD=YourStudioPassword`
    * `SITE_URL=https://supabase.your-domain.com`
    * `API_EXTERNAL_URL=https://supabase.your-domain.com`
    * `SUPABASE_PUBLIC_URL=https://supabase.your-domain.com`

6.  **Generate `ANON_KEY` and `SERVICE_ROLE_KEY`:**
    These keys are JWTs signed with your JWT_SECRET. First, edit the provided Python script to include your secret. (Adjust the path if you cloned your 'supabase-docker-howto' repo elsewhere).
    ```bash
    nano ../../generate_keys.py
    ```
    Paste your `JWT_SECRET` inside the quotes for the `jwt_secret` variable in the script. Then, install the dependency and run the script.
    ```bash
    sudo apt install python3-pip -y
    pip install pyjwt
    python3 ../../generate_keys.py
    ```
    The script will print the ANON_KEY and SERVICE_ROLE_KEY.

7.  **Add the final keys to the `.env` file:**
    Open the .env file one last time (`nano .env`). Paste the generated values for `ANON_KEY` and `SERVICE_ROLE_KEY`. Save the file.

Your `.env` file is now complete.

---

### 5. Step 4: Initial Supabase Launch

With all configurations in place, we can now start the services.

1.  **Launch the containers:**
    ```
    # Ensure you are in the `~/supabase/docker` directory.
    ```
    ```bash
    docker compose up -d
    ```
2.  **Check the status:**
    ```bash
    docker compose ps
    ```
    Wait a few minutes. All services should eventually show the status `Up (healthy)` or `Up`.

---

### 6. Step 5: Firewall Configuration

Secure your server by allowing only necessary traffic.

1.  **Oracle Cloud Firewall (Security List):**
    In the OCI dashboard, add Ingress Rules for ports TCP/80 (HTTP) and TCP/443 (HTTPS). The source should be `0.0.0.0/0`. Port TCP/22 (SSH) should already be allowed.

2.  **Local Firewall (UFW):**
    ```bash
    sudo ufw allow ssh
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw enable
    sudo ufw status
    ```

---

### 7. Step 6: Nginx Reverse Proxy and HTTPS Setup

Nginx will manage external traffic and SSL.

1.  **Install Nginx:**
    ```bash
    sudo apt install nginx -y
    ```

2.  **Create the Nginx config file for Supabase:**
    ```bash
    sudo nano /etc/nginx/sites-available/supabase.your-domain.com
    ```

3.  **Paste the initial HTTP configuration below.** This is required for Certbot to perform its validation.
    ```nginx
    server {
        listen 80;
        listen [::]:80;
        server_name supabase.your-domain.com;

        location / {
            proxy_pass http://localhost:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "Upgrade"; 
        }
    }
    ```

4.  **Enable the site and test the configuration:**
    ```bash
    sudo ln -s /etc/nginx/sites-available/supabase.your-domain.com /etc/nginx/sites-enabled/
    sudo nginx -t
    ```
    If the test is successful (`syntax is ok`), reload Nginx.
    ```bash
    sudo systemctl reload nginx
    ```

5.  **Install Certbot and its Nginx plugin:**
    ```bash
    sudo apt install certbot python3-certbot-nginx -y
    ```

6.  **Obtain the SSL certificate:**
    ```bash
    sudo certbot --nginx -d supabase.your-domain.com
    ```
    Follow the on-screen prompts. Provide your email and choose the `Redirect` option to enforce HTTPS. Certbot will automatically update your Nginx configuration.

7.  **Reload Nginx one last time:**
    ```bash
    sudo systemctl reload nginx
    ```

---

### 8. Conclusion and Access

The installation is complete! Your Supabase instance is running securely with HTTPS.

You can now access the Supabase Studio dashboard at:
**`https://supabase.your-domain.com`**

Log in using the `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` you defined in the `.env` file.
