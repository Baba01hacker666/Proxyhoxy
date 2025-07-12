# Proxyhoxy - An Intercepting MITM HTTP/HTTPS Proxy

Proxyhoxy is a powerful intercepting Man-in-the-Middle (MITM) proxy for HTTP and HTTPS traffic. It is designed for security researchers and developers to capture, inspect, modify, and log network traffic in real-time.

It can automatically download specific file types, decrypt and modify HTTPS content on the fly, and replace keywords in web pages, all managed through a simple configuration file and a web-based admin panel.

![Admin Panel Screenshot](https://user-images.githubusercontent.com/your-username/your-repo/your-image.png)  <!-- Optional: Add a screenshot of your admin panel later -->

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
