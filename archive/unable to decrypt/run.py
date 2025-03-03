import uvicorn
import os
import ssl
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set default SECRET_KEY if not provided
if not os.getenv("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "mirage_development_secret_key"
    print("WARNING: Using default SECRET_KEY. For production, set a secure SECRET_KEY in .env file.")

def generate_self_signed_cert():
    """Generate a self-signed certificate for development HTTPS"""
    from OpenSSL import crypto
    
    # Create certificates directory if it doesn't exist
    cert_dir = Path("./certificates")
    cert_dir.mkdir(exist_ok=True)
    
    key_file = cert_dir / "key.pem"
    cert_file = cert_dir / "cert.pem"
    
    # Check if certificates already exist
    if key_file.exists() and cert_file.exists():
        print("Using existing SSL certificates")
        return str(key_file), str(cert_file)
    
    # Create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)
    
    # Create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().ST = "State"
    cert.get_subject().L = "City"
    cert.get_subject().O = "Organization"
    cert.get_subject().OU = "Organizational Unit"
    cert.get_subject().CN = "localhost"
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10*365*24*60*60)  # 10 years
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')
    
    # Write the certificate and key to files
    with open(str(key_file), "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
    
    with open(str(cert_file), "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    print("Generated self-signed SSL certificates")
    return str(key_file), str(cert_file)

if __name__ == "__main__":
    print("Starting Mirage application...")
    
    # Check if we should use HTTPS
    use_https = os.getenv("USE_HTTPS", "false").lower() == "true"
    
    if use_https:
        # Generate or use existing self-signed certificates
        ssl_keyfile, ssl_certfile = generate_self_signed_cert()
        
        # Create SSL context
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(ssl_certfile, ssl_keyfile)
        
        print(f"HTTPS enabled on https://localhost:8443")
        uvicorn.run(
            "mirage.main:app", 
            host="0.0.0.0", 
            port=8443, 
            reload=True,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile
        )
    else:
        print(f"HTTP enabled on http://localhost:8000")
        uvicorn.run("mirage.main:app", host="0.0.0.0", port=8000, reload=True) 