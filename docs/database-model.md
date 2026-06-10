# Modelagem do Banco de Dados

A modelagem completa do banco pode ser visualizada em:

https://dbdiagram.io/d/Monitoramento-RU-6a10ba3edfb20dafcdd2b86a

## Principais Entidades

- restaurants
- restaurant_schedules
- restaurant_schedule_exceptions
- queue_reports
- queue_snapshots
- queue_aggregates_10m

## Observações

- Cada campus possui um único RU.
- QueueReport é a fonte da verdade dos relatos.
- QueueSnapshot representa o estado consolidado atual.
- QueueAggregates10m é utilizada para analytics e histórico.