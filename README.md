Complete Guide: Self-Hosted Supabase with Docker on Oracle ARM64 VPS

This guide details the process of installing and configuring self-hosted Supabase using Docker and Docker Compose on an Oracle Cloud Infrastructure (OCI) Virtual Private Server (VPS) with an ARM64 architecture (running Ubuntu 24.04 LTS). Our journey addressed and resolved common issues such as database authentication failures, VAULT_ENC_KEY encryption problems, and setting up HTTPS with Nginx and Let's Encrypt.

Table of Contents

1.  Introduction and Prerequisites
2.  Server Preparation
3.  Docker and Docker Compose Installation
4.  Supabase Core Installation
5.  Generating Supabase Keys
6.  Security Configuration (Firewall)
7.  Nginx Reverse Proxy & HTTPS (Let's Encrypt)
8.  Modified Configuration Files (Examples)

---

1. Introduction and Prerequisites

This tutorial will guide you step-by-step through setting up Supabase on your own server, ensuring it's accessible and secure.

Prerequisites:

* Oracle Cloud VPS: A Virtual Machine (VM) instance on Oracle Cloud, running Ubuntu 24.04 LTS with an ARM64 architecture.
* SSH Access: Ability to connect to your VPS via SSH with a user who has sudo permissions.
* Domain Name: A custom domain (e.g., yourdomain.com) configured to point to your VPS's public IP address.
* Basic Linux Knowledge: Familiarity with command-line operations.

---

2. Server Preparation

First things first, let's ensure your server is ready for the installation.

1.  Connect to your VPS via SSH.

2.  Gather system information (for reference):

    cat /etc/os-release
    uname -m
    lscpu | grep "Model name"
    free -h
    df -h

    *This confirms your environment (ARM64 Ubuntu 24.04), and shows CPU, memory, and disk info.*

3.  Update system packages:

    sudo apt update && sudo apt upgrade -y

    *Keep your system updated for security and compatibility.*

---

3. Docker and Docker Compose Installation

Supabase relies on Docker and Docker Compose to orchestrate its various services.

1.  Uninstall old Docker versions (if any):

    sudo apt remove docker docker-engine docker.io containerd runc

    *It's fine if some packages aren't found or installed.*

2.  Install prerequisites for the Docker repository:

    sudo apt install ca-certificates curl apt-transport-https software-properties-common -y

3.  Add the official Docker GPG key:

    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

4.  Add the Docker repository to APT sources:

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

5.  Update the APT package index:

    sudo apt update

    *Confirm that the Docker repository appears in the output.*

6.  Install Docker Engine, containerd, and Docker Compose Plugin:

    sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y

7.  Verify the Docker installation:

    sudo docker run hello-world

    *You should see the "Hello from Docker!" message.*

8.  Add your user to the docker group:

    sudo usermod -aG docker ${USER}

    IMPORTANT: You must log out of your SSH session and log back in (or restart the SSH session) for this change to take effect. After reconnecting, test: docker run hello-world (now without sudo).

---

4. Supabase Core Installation

With Docker configured, let's prepare and start your Supabase instance.

1.  Clone the Supabase repository:

    git clone --depth 1 https://github.com/supabase/supabase

2.  Navigate to the Supabase Docker directory:
    *It's crucial to be in this directory as it contains docker-compose.yml and .env.example.*

    cd supabase/docker

3.  Create and edit the environment variables file (.env):

    cp .env.example .env
    nano .env

    CRITICAL CONFIGURATION POINTS IN .env:

    * VAULT_ENC_KEY (Essential Fix for Supavisor):
        * This is a common point of failure, especially on ARM64 environments. The Supavisor (pooler) expects a binary encryption key of exactly 32 bytes, which translates to a specific string length after encoding.
        * Generate a compatible key (exactly 32 alphanumeric characters):

            openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c32; echo

            *Copy the output (e.g., Your32AlphanumericKeyGoesHere).*
        * Update the VAULT_ENC_KEY= line in .env with this copied key.

    * POSTGRES_PASSWORD:
        * Initially, use a simple password (alphanumeric characters only) for PostgreSQL. Special characters like $ or @ can cause unexpected parsing issues during database initialization.
        * Example:

            POSTGRES_PASSWORD=yoursecurepassword123

        * Also update STUDIO_PG_PASSWORD and DASHBOARD_PASSWORD to simple alphanumeric passwords if they contain special characters.

    * JWT_SECRET, ANON_KEY, SERVICE_ROLE_KEY:
        * For security, generate long, complex, random keys for these variables. We'll detail how to do this in the next section.

    * Example of the Secrets section in .env (USE YOUR OWN KEYS AND PASSWORDS):

        ############
        # Secrets
        ############

        POSTGRES_PASSWORD=yoursecurepassword123
        JWT_SECRET=YOUR_GENERATED_JWT_SECRET_HERE
        ANON_KEY=YOUR_GENERATED_ANON_KEY_HERE
        SERVICE_ROLE_KEY=YOUR_GENERATED_SERVICE_ROLE_KEY_HERE
        DASHBOARD_USERNAME=supabase
        DASHBOARD_PASSWORD=yourstudiosimplepassword
        SECRET_KEY_BASE=YOUR_OTHER_LONG_RANDOM_KEY_HERE
        VAULT_ENC_KEY=Your32AlphanumericKeyGoesHere

    Save the file (Ctrl+X, Y, Enter).

4.  Clear old database data (CRITICAL for password reset):
    *PostgreSQL persists its data in a local directory (./volumes/db/data). You must clear this directory to force the database to reinitialize with the new passwords from your .env.*

    sudo rm -rf ./volumes/db/data/*
    mkdir -p ./volumes/db/data/

5.  Stop and remove any old Docker Compose containers and orphaned volumes:
    *This command ensures a clean slate before starting with the new configurations.*

    docker compose down --volumes --remove-orphans

6.  Start Supabase services:

    docker compose up -d

    *This process will download Docker images and start all containers in detached mode. It might take a few minutes depending on your internet connection.*

7.  Verify the status of all containers:

    docker compose ps

    *All services (db, auth, kong, supavisor, studio, etc.) should show Up (healthy) or Up status.*

---

5. Generating Supabase Keys

You'll need three primary keys for your Supabase instance: JWT_SECRET, ANON_KEY, and SERVICE_ROLE_KEY.

5.1. Generate JWT_SECRET (Command Line)

The JWT_SECRET is the cryptographic key used to sign and verify JSON Web Tokens (JWTs). It's a foundational secret for your Supabase instance.

Use the openssl command to generate a strong, random string:

    openssl rand -hex 32

This command generates a 32-byte (64-character hexadecimal) string. Copy this output. This will be your JWT_SECRET.

Example Output:
a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2

5.2. Generate ANON_KEY and SERVICE_ROLE_KEY (Python Script)

Your ANON_KEY and SERVICE_ROLE_KEY are JWTs that define specific roles (anon and service_role) and are signed using your JWT_SECRET. Supabase uses these keys for client-side and backend API access, respectively.

5.2.1. Create a Python Virtual Environment

It's best practice to isolate Python dependencies in a virtual environment (venv). This prevents conflicts with system-wide Python packages.

1.  Install python3-venv (if not already installed):

    sudo apt update
    sudo apt install python3-venv -y

2.  Create a venv:
    *Navigate to a directory where you want to create your virtual environment (e.g., your home directory).*

    python3 -m venv supabase_keys_env

3.  Activate the venv:

    source supabase_keys_env/bin/activate

    *Your terminal prompt should now show (supabase_keys_env) indicating the venv is active.*

5.2.2. Install pyjwt

Now, install the pyjwt library within your activated virtual environment:

    pip install pyjwt

5.2.3. Create and Run the Python Script

1.  Create the Python script file:
    Create a new file named generate_keys.py in your current directory:

    nano generate_keys.py

2.  Paste the following code into generate_keys.py:
    IMPORTANT: Replace 'YOUR_JWT_SECRET_FROM_STEP_5.1_HERE' with the actual JWT_SECRET you generated in Step 5.1. Keep the single quotes around the secret.

    import jwt

    # --- PASTE YOUR JWT_SECRET HERE ---
    # Keep the single quotes around it.
    jwt_secret = 'YOUR_JWT_SECRET_FROM_STEP_5.1_HERE'

    # --- Payloads (no need to change) ---
    anon_payload = {'role': 'anon'}
    service_role_payload = {'role': 'service_role'}

    # --- Generate the tokens ---
    # The 'HS256' algorithm is Supabase's default.
    anon_key = jwt.encode(anon_payload, jwt_secret, algorithm='HS256')
    service_role_key = jwt.encode(service_role_payload, jwt_secret, algorithm='HS256')

    # --- Print the results ---
    print("\n--- YOUR GENERATED KEYS ---")
    print("\n[ANON_KEY]")
    print(anon_key)
    print("\n[SERVICE_ROLE_KEY]")
    print(service_role_key)
    print("\nCopy and paste these values into your .env file\n")

    Save the file (Ctrl+X, Y, Enter).

3.  Run the Python script:

    python3 generate_keys.py

Example Output:

--- YOUR GENERATED KEYS ---

[ANON_KEY]
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiJ9.SOME_GENERATED_ANON_KEY_STRING_HERE

[SERVICE_ROLE_KEY]
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.SOME_GENERATED_SERVICE_ROLE_KEY_STRING_HERE

Copy and paste these values into your .env file

Copy the full ANON_KEY and SERVICE_ROLE_KEY strings from the output.

4.  Deactivate the venv:
    Once you're done generating keys, you can deactivate the virtual environment.

    deactivate

    *Your terminal prompt should return to its normal state.*

5.3. Update Your Supabase .env File

Navigate back to your ~/supabase/docker/ directory and open your .env file:

    nano ~/supabase/docker/.env

Paste the JWT_SECRET (from Step 5.1), ANON_KEY, and SERVICE_ROLE_KEY (from Step 5.2) into the respective lines in your .env file.

After updating the .env file, remember to restart your Supabase containers for the changes to take effect:

    cd ~/supabase/docker/
    docker compose down
    docker compose up -d

Now you'll have securely generated and applied keys for your Supabase instance!

---

6. Security Configuration (Firewall)

It's essential to configure both your VPS's cloud firewall and your local firewall to allow necessary traffic.

6.1. Oracle Cloud Firewall (Security Lists)

Access your Oracle Cloud Infrastructure (OCI) dashboard.
1.  Navigate to Compute > Instances.
2.  Click on your VM instance (your Ubuntu server).
3.  In the Primary VNIC section, click on the Subnet name associated with your VM.
4.  On the Subnet details page, scroll down to Security Lists. Click on the Security List associated with your Subnet.
5.  Click on Add Ingress Rules and add the following rules:

    * SSH (Port 22):
        * Source CIDR: 0.0.0.0/0
        * IP Protocol: TCP
        * Destination Port Range: 22
        * Description: SSH Access
    * HTTP (Port 80):
        * Source CIDR: 0.0.0.0/0
        * IP Protocol: TCP
        * Destination Port Range: 80
        * Description: HTTP for Nginx
    * HTTPS (Port 443):
        * Source CIDR: 0.0.0.0/0
        * IP Protocol: TCP
        * Destination Port Range: 443
        * Description: HTTPS for Nginx
    * (Optional - Only if you plan to access Docker ports directly without Nginx, which is not recommended for production):
        * Port 3000 (Studio): TCP, 0.0.0.0/0, 3000
        * Port 8000 (Kong HTTP): TCP, 0.0.0.0/0, 8000
        * Port 8443 (Kong HTTPS): TCP, 0.0.0.0/0, 8443

6.  Click Add Ingress Rules to save the changes.

6.2. Local Firewall (UFW on Ubuntu)

UFW (Uncomplicated Firewall) is your operating system's firewall layer.

1.  Check UFW status:

    sudo ufw status

    *If it's inactive, activate it with sudo ufw enable.*

2.  Allow necessary ports:

    sudo ufw allow ssh comment 'SSH Access'
    sudo ufw allow 80/tcp comment 'HTTP for Nginx'
    sudo ufw allow 443/tcp comment 'HTTPS for Nginx'
    # Allow Nginx (running on the host) to communicate with Docker containers
    sudo ufw allow proto tcp from 127.0.0.1 to any port 8000 comment 'Allow Nginx to Kong HTTP'
    sudo ufw allow proto tcp from 127.0.0.1 to any port 8443 comment 'Allow Nginx to Kong HTTPS'
    sudo ufw allow proto tcp from 127.0.0.1 to any port 3000 comment 'Allow Nginx to Studio'

3.  Reload UFW to apply the rules:

    sudo ufw reload

4.  Verify the final UFW status:

    sudo ufw status verbose

    *Ports 80/443 should be open to Anywhere, and ports 3000/8000/8443 should be open only to 127.0.0.1.*

---

7. Nginx Reverse Proxy & HTTPS (Let's Encrypt)

Nginx will act as the entry point for your domain, routing traffic to Docker services and providing HTTPS.

1.  Configure your domain's DNS:
    *Ensure yourdomain.com (or your chosen domain) is pointing to your VPS's public IP address in your DNS provider's settings.*

2.  Install Nginx:

    sudo apt install nginx -y

3.  Verify Nginx status:

    sudo systemctl status nginx

    *It should show active (running).*

4.  Remove the default Nginx site:

    sudo rm /etc/nginx/sites-enabled/default

5.  Create the Nginx configuration file for Supabase (Temporary for Certbot):
    *This configuration is temporary. We need it so Certbot can validate your domain.*

    nano /etc/nginx/sites-available/supabase

    Paste the following content. Replace yourdomain.com with your actual domain.

    server {
        listen 80;
        listen [::]:80;
        server_name yourdomain.com;

        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443;
        listen [::]:443;
        server_name yourdomain.com;

        # The ssl_certificate, ssl_certificate_key, include, and ssl_dhparam lines should be COMMENTED OUT or REMOVED
        # ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
        # ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
        # include /etc/letsencrypt/options-ssl-nginx.conf;
        # ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

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
            proxy_set_header Connection "Upgrade";
        }
    }

    Save the file (Ctrl+X, Y, Enter).

6.  Enable the Nginx configuration and test:

    sudo ln -s /etc/nginx/sites-available/supabase /etc/nginx/sites-enabled/
    sudo nginx -t

    *It should return syntax is ok and test is successful.*

7.  Restart Nginx:

    sudo systemctl restart nginx

8.  Install Certbot and the Nginx plugin:

    sudo apt install certbot python3-certbot-nginx -y

9.  Obtain SSL certificates with Certbot:

    sudo certbot --nginx -d yourdomain.com

    *Follow Certbot's prompts: enter your email, agree to the terms of service, and choose option 2: Redirect to redirect HTTP traffic to HTTPS.*
    Expected result: Congratulations! You have successfully enabled HTTPS on https://yourdomain.com

10. Adjust Nginx Configuration (FINAL - Post-Certbot):
    *Certbot will have modified your configuration file. We need to ensure it contains the correct proxy directives.*
    Edit the file again:

    nano /etc/nginx/sites-available/supabase

    Verify and adjust the content to the following. Ensure the location / section in the HTTPS block is correct.

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

        # SSL certificate settings generated by Certbot/Let's Encrypt
        ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
        include /etc/letsencrypt/options-ssl-nginx.conf;
        ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

        # Proxy to Supabase Kong (API Gateway) at the root domain (https://yourdomain.com/)
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

    Save the file (Ctrl+X, Y, Enter).

11. Test and restart Nginx (final time for main configuration):

    sudo nginx -t
    sudo systemctl restart nginx

12. Update SUPABASE_PUBLIC_URL in your Supabase .env:
    In the ~/supabase/docker/ directory, edit the .env:

    nano .env

    Change the SUPABASE_PUBLIC_URL line to your full domain with HTTPS:

    SUPABASE_PUBLIC_URL=https://yourdomain.com

    Save the file.

13. Restart Supabase containers to apply the .env change:

    docker compose down
    docker compose up -d

    You should now be able to access Supabase Studio at https://yourdomain.com and log in with your DASHBOARD_USERNAME and DASHBOARD_PASSWORD from your .env.

---

8. Modified Configuration Files (Examples)

Here are the final contents of the files that were modified throughout this tutorial.

8.1. ~/supabase/docker/.env (Final Version)

############
# Secrets
############

# Example: Your simple password here
POSTGRES_PASSWORD=yoursecurepassword123
# Randomly generated
JWT_SECRET=YOUR_LONG_AND_RANDOM_JWT_SECRET_HERE
# Randomly generated
ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiJ9.YOUR_ANON_KEY_HERE
# Randomly generated
SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.YOUR_SERVICE_KEY_HERE
# Your dashboard username
DASHBOARD_USERNAME=supabase
# Your dashboard password
DASHBOARD_PASSWORD=yourstudiosimplepassword
# Randomly generated
SECRET_KEY_BASE=YOUR_OTHER_LONG_RANDOM_KEY_HERE
# Generated with openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c32
VAULT_ENC_KEY=Your32AlphanumericKeyGoesHere

############
# Database - You can change these to any PostgreSQL database that has logical replication enabled.
############

POSTGRES_HOST=db
POSTGRES_DB=postgres
POSTGRES_PORT=5432
# default user is postgres


############
# Supavisor -- Database pooler
############
POOLER_PROXY_PORT_TRANSACTION=6543
POOLER_DEFAULT_POOL_SIZE=20
POOLER_MAX_CLIENT_CONN=100
POOLER_TENANT_ID=local


############
# API Proxy - Configuration for the Kong Reverse proxy.
############

KONG_HTTP_PORT=8000
KONG_HTTPS_PORT=8443


############
# API - Configuration for PostgREST.
############

PGRST_DB_SCHEMAS=public,storage,graphql_public


############
# Auth - Configuration for the GoTrue authentication server.
############

## General
SITE_URL=http://localhost:3000
ADDITIONAL_REDIRECT_URLS=
JWT_EXPIRY=3600
DISABLE_SIGNUP=false
API_EXTERNAL_URL=http://localhost:8000

## Mailer Config
MAILER_URLPATHS_CONFIRMATION="/auth/v1/verify"
MAILER_URLPATHS_INVITE="/auth/v1/verify"
MAILER_URLPATHS_RECOVERY="/auth/v1/verify"
MAILER_URLPATHS_EMAIL_CHANGE="/auth/v1/verify"

## Email auth
ENABLE_EMAIL_SIGNUP=true
ENABLE_EMAIL_AUTOCONFIRM=false
# Your SMTP admin email
SMTP_ADMIN_EMAIL=admin@example.com
# Your SMTP host
SMTP_HOST=smtp-relay.brevo.com
# Your SMTP port
SMTP_PORT=587
# Your SMTP user
SMTP_USER=YOUR_SMTP_USER
# Your SMTP password
SMTP_PASS=YOUR_SMTP_PASS
# Your sender name
SMTP_SENDER_NAME=your_email@example.com
ENABLE_ANONYMOUS_USERS=false

## Phone auth
ENABLE_PHONE_SIGNUP=true
ENABLE_PHONE_AUTOCONFIRM=true


############
# Studio - Configuration for the Dashboard
############

STUDIO_DEFAULT_ORGANIZATION=Default Organization
STUDIO_DEFAULT_PROJECT=Default Project

STUDIO_PORT=3000
# Replace with your full public domain with HTTPS
SUPABASE_PUBLIC_URL=https://yourdomain.com

# Add or adjust this line if using a subdirectory for Studio
# Remove or comment this line if not using a subdirectory
# BASE_PATH=/supabase

# Enable webp support
IMGPROXY_ENABLE_WEBP_DETECTION=true

# Add your OpenAI API key to enable SQL Editor Assistant
OPENAI_API_KEY=


############
# Functions - Configuration for Functions
############
# NOTE: VERIFY_JWT applies to all functions. Per-function VERIFY_JWT is not supported yet.
FUNCTIONS_VERIFY_JWT=false


############
# Logs - Configuration for Analytics
# Please refer to https://supabase.com/docs/reference/self-hosting-analytics/introduction
############

# Change vector.toml sinks to reflect this change
# these cannot be the same value
LOGFLARE_PUBLIC_ACCESS_TOKEN=your-super-secret-and-long-logflare-key-public
LOGFLARE_PRIVATE_ACCESS_TOKEN=your-super-secret-and-long-logflare-key-private

# Docker socket location - this value will differ depending on your OS
DOCKER_SOCKET_LOCATION=/var/run/docker.sock

# Google Cloud Project details
GOOGLE_PROJECT_ID=GOOGLE_PROJECT_ID
GOOGLE_PROJECT_NUMBER=GOOGLE_PROJECT_NUMBER

8.2. /etc/nginx/sites-available/supabase (Final Version)

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

    # SSL certificate settings generated by Certbot/Let's Encrypt
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Proxy to Supabase Kong (API Gateway) at the root domain (https://yourdomain.com/)
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
