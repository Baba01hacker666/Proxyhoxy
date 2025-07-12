# Proxyhoxy-main/generate_ca.py
import os
from OpenSSL import crypto

CERT_DIR = "certs"
CA_CERT_FILE = os.path.join(CERT_DIR, "ca.crt")
CA_KEY_FILE = os.path.join(CERT_DIR, "ca.key")

def generate_ca():
    """
    Generates a self-signed root Certificate Authority (CA) if it doesn't exist.
    """
    if os.path.exists(CA_CERT_FILE) and os.path.exists(CA_KEY_FILE):
        print("[*] CA certificate and key already exist. Skipping generation.")
        return

    print("[*] Generating new CA certificate and private key...")
    os.makedirs(CERT_DIR, exist_ok=True)

    # Create a new key pair
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)

    # Create a self-signed certificate
    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().ST = "California"
    cert.get_subject().L = "San Francisco"
    cert.get_subject().O = "Proxyhoxy"
    cert.get_subject().OU = "Proxyhoxy CA"
    cert.get_subject().CN = "Proxyhoxy Root CA"
    
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60) # Valid for 10 years
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.add_extensions([
        crypto.X509Extension(b"basicConstraints", True, b"CA:TRUE, pathlen:0"),
        crypto.X509Extension(b"keyUsage", True, b"keyCertSign, cRLSign"),
        crypto.X509Extension(b"subjectKeyIdentifier", False, b"hash", subject=cert),
    ])
    cert.sign(key, 'sha256')

    # Save the key and certificate
    with open(CA_KEY_FILE, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
    with open(CA_CERT_FILE, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        
    print(f"[+] CA certificate saved to {CA_CERT_FILE}")
    print(f"[+] CA private key saved to {CA_KEY_FILE}")
    print("\n[IMPORTANT] You must now install the 'ca.crt' file in your browser or OS.")

if __name__ == "__main__":
    generate_ca()