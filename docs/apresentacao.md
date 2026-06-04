# Monitor RU — Apresentação do Projeto

**Sistema Colaborativo de Monitoramento de Filas dos Restaurantes Universitários**

---

## O que é o Monitor RU?

O Monitor RU é um sistema web que permite aos estudantes acompanhar, em tempo real, a situação da fila nos Restaurantes Universitários — antes mesmo de sair de casa ou da sala de aula.

Qualquer estudante que esteja próximo ao RU pode informar como está a fila naquele momento. Essas informações são agregadas automaticamente pelo sistema, que calcula e exibe um status atual para cada restaurante.

---

## O problema que resolve

Quem frequenta o RU conhece bem a situação: às vezes a fila está enorme e você só descobre ao chegar lá. Outras vezes o restaurante está quase vazio e você nem foi porque achou que estaria cheio.

O Monitor RU resolve isso dando visibilidade à situação da fila em tempo real, de forma colaborativa — os próprios estudantes alimentam o sistema com informações que beneficiam a todos.

---

## Como funciona para o estudante

1. **Acessa o sistema pelo navegador** (computador ou celular) e vê o status atual de cada RU disponível.

2. **Se estiver próximo ao restaurante**, pode contribuir informando como está a fila no momento. As opções são:
   - Sem fila
   - Fila pequena
   - Fila média
   - Fila grande
   - Comida acabou

3. **O sistema valida** que o estudante está fisicamente próximo ao restaurante antes de aceitar o relato — isso garante que só quem está lá pode informar.

4. **O status é atualizado automaticamente** com base nos relatos recentes, dando mais peso às informações mais recentes.

---

## Funcionalidades principais

### Para os estudantes

| Funcionalidade | Descrição |
|---|---|
| **Dashboard de RUs** | Página inicial com todos os restaurantes e o status atual de cada um |
| **Status em tempo real** | Indicador visual do estado da fila: sem fila, pequena, média, grande ou comida acabou |
| **Indicador de frescor** | Exibe há quantos minutos os dados foram atualizados pela última vez |
| **Envio de relato** | Estudante informa a situação da fila com um clique |
| **Feed de relatos** | Histórico dos últimos relatos enviados para aquele restaurante |
| **Horários de funcionamento** | Página com a grade de horários de almoço e jantar de todos os RUs |
| **Exceções de horário** | Exibe avisos quando o RU estiver fechado por feriado ou funcionando em horário diferente |

### Para os administradores

| Funcionalidade | Descrição |
|---|---|
| **Painel admin protegido** | Área de gestão acessível apenas com chave de administrador |
| **Cadastro de restaurantes** | Adicionar ou editar informações dos RUs (nome, localização, raio de alcance) |
| **Gestão de horários** | Configurar os horários de almoço e jantar de cada restaurante, por dia da semana |
| **Exceções de horário** | Registrar feriados, fechamentos temporários ou horários especiais |

---

## Como o sistema garante a qualidade das informações

Para que o status exibido seja confiável, o sistema aplica algumas verificações automáticas:

**Verificação de proximidade**
O relato só é aceito se o estudante estiver fisicamente próximo ao restaurante. Isso impede que alguém informe a situação de um lugar onde não está.

**Limitação por tempo**
Um mesmo estudante não pode enviar vários relatos seguidos. Há um intervalo mínimo entre envios, evitando que uma única pessoa influencie o sistema de forma desproporcional.

**Peso por recência**
Relatos mais recentes têm mais influência no cálculo do status do que relatos antigos. Se ninguém informar nada por um tempo, o sistema passa a indicar que não há dados atualizados.

**Score de confiança**
Cada relato recebe automaticamente uma nota de confiança com base na qualidade do sinal de GPS informado. Relatos com GPS mais preciso têm mais peso no cálculo final.

**Horário de funcionamento**
O sistema só aceita relatos durante o horário em que o restaurante está funcionando. Fora do horário, o envio é bloqueado automaticamente.

---

## Fluxo resumido

```
Estudante abre o sistema
        ↓
Vê o status atual do RU (sem fila / fila pequena / fila grande…)
        ↓
Se estiver próximo, informa a situação atual
        ↓
Sistema valida a localização e o horário
        ↓
Relato é aceito e o status é recalculado
        ↓
Todos os outros estudantes veem o status atualizado
```

---

## O que está planejado

O sistema está em desenvolvimento ativo. As próximas funcionalidades planejadas incluem:

- **Atualização automática em tempo real** — o status muda na tela sem precisar recarregar a página (WebSocket)
- **Métricas de uso** — painel com dados agregados como total de relatos, horários de maior movimento e distribuição dos status ao longo do dia
- **Histórico por hora** — gráfico mostrando como a fila evoluiu ao longo do dia em cada restaurante
- **Previsão de fila** — com base no histórico dos dias anteriores, o sistema poderá indicar os horários com maior e menor probabilidade de fila

---

## Sobre o desenvolvimento

O projeto faz parte do **SIIS — Sistema Integrado de Informações do Estudante**, desenvolvido por alunos do campus como ferramenta de apoio à comunidade acadêmica.

O sistema é composto por duas partes:
- **Interface web** (front-end) — o que o estudante vê e usa no navegador
- **Servidor** (back-end) — responsável por receber os relatos, validar as informações e calcular os status

Ambas as partes foram desenvolvidas do zero para este projeto.

---

**Autor:** Kauan Rodrigues Lima
GitHub: [Kauanrodrigues01](https://github.com/Kauanrodrigues01) · LinkedIn: [Kauan Rodrigues](https://www.linkedin.com/in/kauan-rodrigues-lima/)
