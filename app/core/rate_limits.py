# Rate limit para endpoints de leitura simples (1 query)
READ_RATE_LIMIT = "60/minute"

# Rate limit para endpoints de leitura em lote (N queries por request)
BULK_READ_RATE_LIMIT = "20/minute"

# Rate limit para create/update de Restaurant
CREATE_RESTAURANT_RATE_LIMIT = "10/minute"
UPDATE_RESTAURANT_RATE_LIMIT = "10/minute"

# Rate limit para create/update de Restaurant Schedule
CREATE_SCHEDULE_RATE_LIMIT = "20/minute"
UPDATE_SCHEDULE_RATE_LIMIT = "20/minute"

# Rate limit para create/update de Restaurant Schedule Exception
CREATE_SCHEDULE_EXCEPTION_RATE_LIMIT = "5/minute"
UPDATE_SCHEDULE_EXCEPTION_RATE_LIMIT = "10/minute"

# Rate limit para criação de Queue Report — proteção contra DoS bruto; cooldown real é feito no service
QUEUE_REPORT_RATE_LIMIT = "20/minute"

# Rate limit para conexões WebSocket — previne brute force de abertura de conexões
WS_CONNECT_RATE_LIMIT = "20/minute"
