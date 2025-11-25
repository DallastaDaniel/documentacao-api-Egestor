# Dashboard de vendas do mês atual

Este guia mostra como montar um painel com os principais indicadores de vendas do mês atual consumindo a API do eGestor. Os exemplos usam JavaScript, mas a mesma lógica se aplica a outras linguagens que consigam fazer requisições HTTP autenticadas.

## Endpoints utilizados
- `POST /oauth/access_token` para trocar o **personal_token** por um `access_token` temporário.
- `GET /vendas` para recuperar as vendas filtradas pelo período desejado.

## Passo 1: obter um access_token
> 🔒 Segurança: o `personal_token` deve ser informado apenas em tempo de execução (por exemplo, via prompt ou campo de formulário) e nunca salvo no código-fonte ou commitado no repositório.

Envie o `personal_token` obtido no menu **Configurações > API** do eGestor para gerar um token de acesso de curta duração.
Use `grant_type=personal` obrigatoriamente:

```bash
curl --request POST \
  --url https://api.egestor.com.br/api/oauth/access_token \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data grant_type=personal \
  --data personal_token=SEU_PERSONAL_TOKEN
```

A resposta retorna o campo `access_token`, que deve ser enviado em todas as chamadas seguintes.

## Passo 2: buscar as vendas do mês corrente
Use o endpoint de listagem de vendas informando o intervalo de datas do mês atual. O filtro `tipo=50` limita o resultado apenas a vendas (excluindo orçamentos), e `dtTipo=dtVenda` utiliza a data de venda como referência.

```bash
FIRST_DAY=$(date +%Y-%m-01)
LAST_DAY=$(date -d "$(date +%Y-%m-01) +1 month -1 day" +%Y-%m-%d)

curl --request GET \
  --url "https://api.egestor.com.br/api/v1/vendas?dtTipo=dtVenda&dtIni=${FIRST_DAY}&dtFim=${LAST_DAY}&tipo=50&orderBy=dtVenda,asc" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

O retorno incluirá a lista de vendas com campos como `dtVenda`, `valorTotal` e `codVendedor`, que já servem para as agregações do painel.

## Passo 3: calcular indicadores do painel
A partir da coleção de vendas, calcule métricas como:

- **Faturamento do mês:** soma de `valorTotal`.
- **Quantidade de vendas:** tamanho da lista retornada.
- **Ticket médio:** `faturamento / quantidade` (quando quantidade > 0).
- **Faturamento diário:** agrupe por `dtVenda` e some `valorTotal` para alimentar gráficos de linha ou barras.

## Exemplo rápido com fetch e Chart.js
O snippet abaixo monta as métricas e preenche um gráfico diário com Chart.js.

```javascript
import Chart from 'chart.js/auto';

async function gerarAccessToken() {
  // Pergunta o personal_token em tempo de execução (não salve no código)
  const personalToken = prompt('Informe seu personal_token do eGestor:');

  const resposta = await fetch('https://api.egestor.com.br/api/oauth/access_token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'personal',
      personal_token: personalToken,
    }),
  });

  if (!resposta.ok) {
    throw new Error(`Erro ao obter access_token: ${resposta.status}`);
  }

  const { access_token: accessToken } = await resposta.json();
  return accessToken;
}

async function carregarVendasMesAtual(accessToken) {
  const hoje = new Date();
  const primeiroDia = new Date(hoje.getFullYear(), hoje.getMonth(), 1)
    .toISOString()
    .slice(0, 10);
  const ultimoDia = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0)
    .toISOString()
    .slice(0, 10);

  const url = new URL('https://api.egestor.com.br/api/v1/vendas');
  url.searchParams.set('dtTipo', 'dtVenda');
  url.searchParams.set('dtIni', primeiroDia);
  url.searchParams.set('dtFim', ultimoDia);
  url.searchParams.set('tipo', '50');
  url.searchParams.set('orderBy', 'dtVenda,asc');

  const resposta = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!resposta.ok) {
    throw new Error(`Erro ao buscar vendas: ${resposta.status}`);
  }

  const payload = await resposta.json();
  const vendas = payload.data ?? [];

  const faturamento = vendas.reduce((total, venda) => total + Number(venda.valorTotal || 0), 0);
  const quantidade = vendas.length;
  const ticketMedio = quantidade ? faturamento / quantidade : 0;

  const porDia = vendas.reduce((acumulado, venda) => {
    const data = venda.dtVenda;
    const valor = Number(venda.valorTotal || 0);
    acumulado[data] = (acumulado[data] || 0) + valor;
    return acumulado;
  }, {});

  const dias = Object.keys(porDia).sort();
  const valores = dias.map((dia) => porDia[dia]);

  document.querySelector('#faturamento').textContent = faturamento.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
  document.querySelector('#ticket-medio').textContent = ticketMedio.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
  document.querySelector('#quantidade-vendas').textContent = quantidade;

  const ctx = document.getElementById('grafico-diario');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: dias,
      datasets: [
        {
          label: 'Faturamento diário (R$)',
          data: valores,
          backgroundColor: '#2E86DE',
        },
      ],
    },
  });
}

// Exemplo de uso sem armazenar tokens de forma persistente
document.querySelector('#btn-carregar').addEventListener('click', async () => {
  const accessToken = await gerarAccessToken();
  await carregarVendasMesAtual(accessToken);
});
```

Inclua três elementos no HTML para os indicadores (`#faturamento`, `#ticket-medio`, `#quantidade-vendas`) e um `<canvas id="grafico-diario">` para o gráfico. Depois de obter o `access_token`, invoque `carregarVendasMesAtual(token)` para popular o dashboard.
