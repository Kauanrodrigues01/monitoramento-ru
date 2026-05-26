# Rate limit para endpoints de leitura
READ_RATE_LIMIT = "60/minute"

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
