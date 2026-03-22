# Proxyhoxy - An Intercepting MITM HTTP/HTTPS Proxy

Proxyhoxy is a powerful intercepting Man-in-the-Middle (MITM) proxy for HTTP and HTTPS traffic. It is designed for security researchers and developers to capture, inspect, modify, and log network traffic in real-time.

It can automatically download specific file types, decrypt and modify HTTPS content on the fly, and replace keywords in web pages, all managed through a simple configuration file and a web-based admin panel.

## Features

*   **HTTP & HTTPS Interception:** Decrypts and inspects TLS/SSL traffic using a Man-in-the-Middle approach.
*   **On-the-Fly Content Modification:** Automatically replaces specified keywords in text-based web content (HTML, JavaScript, CSS, etc.).
*   **Easy Configuration:** All settings (ports, log files, keywords) are managed in a simple `config.ini` file.
*   **Traffic Logging:** Logs details of all requests, including client IP, requested URL, and method.
*   **Automatic File Downloading:** Intercepts and saves files with specific extensions (e.g., `.zip`, `.exe`, `.apk`) to a local directory.
*   **Web Admin Panel:** A clean web interface to view connection logs, browse/download captured files, and download the required CA certificate.
*   **Certificate Generation:** Includes a script to generate the necessary local Certificate Authority (CA) for HTTPS interception.

## How It Works

The proxy works by positioning itself between your client (e.g., a web browser) and the internet.

1.  **For HTTP traffic:** It directly reads the request, logs it, modifies content if configured, and then forwards it to the destination server.
2.  **For HTTPS traffic (MITM):**
    *   The client sends a `CONNECT` request to the proxy to open a tunnel to the destination server (e.g., `google.com`).
    *   Proxyhoxy intercepts this request. Instead of just tunneling, it generates a fake SSL certificate for `google.com` and signs it with its own root Certificate Authority (CA).
    *   It presents this fake certificate to the client. The client trusts it because you will have installed the Proxyhoxy Root CA in your browser/OS.
    *   A secure (TLS) connection is established between the client and Proxyhoxy.
    *   Proxyhoxy then establishes its own separate, legitimate secure connection to the real `google.com`.
    *   It decrypts data from the client, logs it, modifies it, re-encrypts it, and sends it to the server. The process is reversed for the response.

## Installation & Setup Guide

Follow these steps carefully to get Proxyhoxy running.

### Step 1: Clone the Repository

Open your terminal and clone the repository to your local machine.

```bash
git clone https://github.com/Baba01hacker666/Proxyhoxy.git
cd Proxyhoxy
```

### Step 2: Install Dependencies

The project requires `pyopenssl` to handle SSL/TLS certificate operations. Install it using pip.

```bash
pip install -r requirements.txt
```
*(On some systems, you may need to use `pip3`)*

### Step 3: Generate the Certificate Authority (CA)

This is a **one-time setup step**. You need to create your own local CA which will be used to sign certificates for the websites you visit.

```bash
python3 generate_ca.py
```
This creates a `certs` directory containing `ca.crt` (the public certificate) and `ca.key` (the private key).

### Step 4: Install and Trust the CA Certificate

This is the most critical step for intercepting HTTPS traffic. You must tell your browser or OS to trust your newly created CA.

**Instructions for Chrome/Edge:**
1.  Go to **Settings** → **Privacy and security** → **Security** → **Manage certificates**.
2.  Click the **Authorities** tab and then click **Import...**.
3.  Navigate to your `Proxyhoxy/certs` folder and select the `ca.crt` file.
4.  In the dialog box, **check the box "Trust this certificate for identifying websites."** and click **OK**.

**Instructions for Firefox:**
1.  Go to **Settings** and search for "certificates".
2.  Click **View Certificates...**.
3.  In the **Authorities** tab, click **Import...**.
4.  Select the `ca.crt` file.
5.  **Check the box "Trust this CA to identify websites."** and click **OK**.

### Step 5: Configure the Proxy

All settings are in the `config.ini` file. You can edit it to:
*   Change the `proxy_port` or `admin_port`.
*   Enable or disable `https_mitm` or `content_replacement`.
*   Add or change keywords for content modification.

```ini
[content_modification]
# ...
# Example: "Google" will be replaced with "Proxyhoxy"
Google = Proxyhoxy
```

### Step 6: Run Proxyhoxy

Start the proxy server with a single command. The admin panel will start automatically in the background.

```bash
python3 proxy_server.py
```
The terminal will confirm that both servers are running.

### Step 7: Configure Your System/Browser to Use the Proxy

1.  Go to your operating system's or browser's network proxy settings.
2.  Enable **manual proxy** configuration.
3.  Set the following:
    *   **Server/Address:** `127.0.0.1` (or `localhost`)
    *   **Port:** `8080` (or the `proxy_port` from `config.ini`)
4.  Apply these settings for both **HTTP** and **HTTPS** (Secure Web Proxy).

## Usage

*   **Browse the web:** Your traffic will now be routed through Proxyhoxy. Check the terminal window where it's running to see live request logs.
*   **Access the Admin Panel:** Open your browser and navigate to `http://127.0.0.1:5000` (or your configured admin port). Here you can view logs and download any captured files.
*   **Verify Interception:** Visit an HTTPS site and click the padlock icon in the address bar. The certificate details should show it was issued by **"Proxyhoxy Root CA"**, confirming that your MITM is active.

## Disclaimer

This tool is intended for educational and authorized security testing purposes only. The user is responsible for all their actions. Decrypting network traffic without explicit, authorized consent is illegal and unethical. The developer of this tool is not responsible for its misuse.
```
