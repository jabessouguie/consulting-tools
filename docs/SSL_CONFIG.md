# 🔒 Configuration HTTPS / SSL

## Développement local

L'application détecte automatiquement la présence des certificats SSL et démarre en HTTPS si disponibles.

### Certificats auto-signés (déjà créés)

Les certificats auto-signés sont dans `/ssl/` :
- `ssl/cert.pem` - Certificat
- `ssl/key.pem` - Clé privée

**⚠️ Note :** Les navigateurs afficheront un avertissement de sécurité car le certificat est auto-signé. C'est normal en développement.

### Ports

- **HTTP** : [http://localhost:8000](http://localhost:8000)
- **HTTPS** : [https://localhost:8443](https://localhost:8443)

L'application démarre automatiquement en HTTPS si les certificats existent.

---

## Production

### Option 1 : Let's Encrypt (Recommandé)

Let's Encrypt fournit des certificats SSL gratuits et reconnus.

#### Installation avec Certbot

```bash
# Installer certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtenir un certificat (remplacer votre-domaine.com)
sudo certbot certonly --standalone -d votre-domaine.com
```

Les certificats seront dans `/etc/letsencrypt/live/votre-domaine.com/`

#### Configuration

Modifier `.env` :

```bash
SSL_CERT_PATH=/etc/letsencrypt/live/votre-domaine.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/votre-domaine.com/privkey.pem
```

Modifier `app.py` pour lire depuis `.env` :

```python
ssl_cert = Path(os.getenv("SSL_CERT_PATH", str(BASE_DIR / "ssl" / "cert.pem")))
ssl_key = Path(os.getenv("SSL_KEY_PATH", str(BASE_DIR / "ssl" / "key.pem")))
```

#### Renouvellement automatique

Let's Encrypt expire après 90 jours. Configurer le renouvellement auto :

```bash
# Test du renouvellement
sudo certbot renew --dry-run

# Ajouter au crontab (renouvelle tous les jours à 2h du matin)
0 2 * * * certbot renew --quiet && systemctl restart Consulting Tools-agents
```

---

### Option 2 : Reverse Proxy (Nginx/Caddy)

#### Avec Nginx

1. Installer Nginx :
```bash
sudo apt-get install nginx
```

2. Configuration Nginx (`/etc/nginx/sites-available/Consulting Tools`) :

```nginx
server {
    listen 80;
    server_name votre-domaine.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name votre-domaine.com;

    ssl_certificate /etc/letsencrypt/live/votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.com/privkey.pem;

    # SSL optimizations
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

3. Activer et redémarrer :
```bash
sudo ln -s /etc/nginx/sites-available/Consulting Tools /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Avec Caddy (plus simple)

Fichier `Caddyfile` :

```
votre-domaine.com {
    reverse_proxy localhost:8000
}
```

Caddy gère automatiquement SSL avec Let's Encrypt !

```bash
sudo caddy run --config Caddyfile
```

---

### Option 3 : Cloudflare

1. Créer un compte Cloudflare
2. Ajouter votre domaine
3. Activer "Full" SSL/TLS encryption mode
4. Configurer les DNS pour pointer vers votre serveur

Cloudflare gère automatiquement SSL et offre :
- CDN global
- Protection DDoS
- WAF (Web Application Firewall)
- Analytics

---

## Vérification SSL

### Test local

```bash
curl -k https://localhost:8443
```

### Test production

```bash
# Vérifier le certificat
openssl s_client -connect votre-domaine.com:443 -servername votre-domaine.com

# Test complet avec SSL Labs
# Aller sur https://www.ssllabs.com/ssltest/
```

---

## Sécurité supplémentaire

### 1. HSTS (HTTP Strict Transport Security)

Ajouter dans `app.py` :

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

### 2. Firewall

```bash
# UFW (Ubuntu)
sudo ufw allow 443/tcp
sudo ufw allow 80/tcp
sudo ufw enable
```

### 3. Fail2ban

Protection contre les attaques brute-force :

```bash
sudo apt-get install fail2ban
sudo systemctl enable fail2ban
```

---

## Troubleshooting

### Erreur "Address already in use"

Un autre processus utilise le port :

```bash
# Trouver le processus
lsof -i :8443

# Tuer le processus
kill -9 <PID>
```

### "Certificate verify failed"

En développement avec certificat auto-signé :
- Accepter l'exception de sécurité dans le navigateur
- OU utiliser `curl -k` pour ignorer la vérification

### Permissions SSL

```bash
# Les certificats doivent être lisibles
sudo chmod 644 /etc/letsencrypt/live/*/fullchain.pem
sudo chmod 600 /etc/letsencrypt/live/*/privkey.pem
```

---

## Recommandations production

✅ **Obligatoire :**
- Utiliser Let's Encrypt ou certificat valide
- Configurer HSTS
- Renouvellement automatique des certificats

✅ **Recommandé :**
- Utiliser un reverse proxy (Nginx/Caddy)
- Activer Cloudflare pour CDN + sécurité
- Configurer fail2ban
- Monitoring des certificats (expiration)

✅ **Optionnel :**
- Certificate pinning pour les apps mobiles
- OCSP stapling
- Perfect Forward Secrecy (PFS)
