# HTTP Security Headers

Adicionar security headers nas respostas da API protege contra ataques comuns sem custo de dependências.

Exemplo de resposta com headers configurados:

```http
HTTP/1.1 200 OK
Content-Type: application/json
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
```

---

## Headers relevantes

### `Strict-Transport-Security` (HSTS)

Protege contra downgrade de HTTPS para HTTP. Sem ele, um atacante pode interceptar um request inicial feito por `http://`.

Com o header, o navegador aprende que aquele domínio só aceita HTTPS e nunca mais tenta HTTP:

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

- `max-age=31536000` — aprende por 1 ano
- `includeSubDomains` — aplica a subdomínios também

> Só faz sentido quando a API já está atrás de HTTPS (Nginx/Cloudflare). Em HTTP puro o header é ignorado.

---

### `X-Frame-Options`

Protege contra **clickjacking**: impede que a página seja carregada dentro de um `<iframe>` por outro domínio.

```http
X-Frame-Options: DENY
```

Para APIs REST isso sempre deve ser `DENY`.

---

### `X-Content-Type-Options`

Protege contra **MIME sniffing**: impede que o browser interprete o `Content-Type` de forma diferente do declarado (ex: tratar um `.txt` como JavaScript).

```http
X-Content-Type-Options: nosniff
```

---

## Implementação no FastAPI

### Opção recomendada — middleware manual

Sem dependência extra, controle total:

```python
# app/main.py
from fastapi import Request

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
```

### Alternativa — lib `secure`

Adiciona automaticamente HSTS, X-Frame, CSP, Referrer-Policy e outros:

```bash
pip install secure
```

```python
from secure import Secure

secure_headers = Secure()

@app.middleware("http")
async def set_secure_headers(request: Request, call_next):
    response = await call_next(request)
    secure_headers.framework.fastapi(response)
    return response
```

Para este projeto o **middleware manual é suficiente** — menos dependência, mais clareza.
