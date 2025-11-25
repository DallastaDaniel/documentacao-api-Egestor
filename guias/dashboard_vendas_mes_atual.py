"""
Exemplo em Python para montar um dashboard de vendas do mês atual
usando a API do eGestor. O personal_token é pedido em tempo de
execução e nunca deve ser salvo no código ou em repositórios.
"""
from __future__ import annotations

import calendar
from datetime import date
from typing import Dict, List

import requests

API_BASE = "https://api.egestor.com.br/api"


def obter_access_token(personal_token: str) -> str:
    """
    Troca o personal_token por um access_token temporário.
    O personal_token deve ser coletado em tempo de execução.
    """

    resposta = requests.post(
        f"{API_BASE}/oauth/access_token",
        data={
            "grant_type": "personal",
            "personal_token": personal_token,
        },
        timeout=15,
    )
    resposta.raise_for_status()
    payload = resposta.json()
    return payload["access_token"]


def intervalo_mes_atual() -> Dict[str, str]:
    hoje = date.today()
    primeiro_dia = hoje.replace(day=1)
    ultimo_dia = primeiro_dia.replace(
        day=calendar.monthrange(hoje.year, hoje.month)[1]
    )
    return {
        "dtIni": primeiro_dia.isoformat(),
        "dtFim": ultimo_dia.isoformat(),
    }


def buscar_vendas_mes(access_token: str) -> List[Dict]:
    datas = intervalo_mes_atual()
    params = {
        "dtTipo": "dtVenda",
        "dtIni": datas["dtIni"],
        "dtFim": datas["dtFim"],
        "tipo": "50",  # apenas vendas, exclui orçamentos
        "orderBy": "dtVenda,asc",
    }

    resposta = requests.get(
        f"{API_BASE}/v1/vendas",
        headers={"Authorization": f"Bearer {access_token}"},
        params=params,
        timeout=30,
    )
    resposta.raise_for_status()
    payload = resposta.json()
    return payload.get("data", [])


def calcular_metricas(vendas: List[Dict]):
    faturamento = sum(float(v.get("valorTotal", 0) or 0) for v in vendas)
    quantidade = len(vendas)
    ticket_medio = faturamento / quantidade if quantidade else 0.0

    por_dia: Dict[str, float] = {}
    for venda in vendas:
        data = venda.get("dtVenda")
        valor = float(venda.get("valorTotal", 0) or 0)
        if data:
            por_dia[data] = por_dia.get(data, 0.0) + valor

    return faturamento, quantidade, ticket_medio, por_dia


def imprimir_metricas(faturamento: float, quantidade: int, ticket_medio: float, por_dia: Dict[str, float]):
    print("\nIndicadores do mês atual:\n")
    print(f"Faturamento: R$ {faturamento:,.2f}")
    print(f"Quantidade de vendas: {quantidade}")
    print(f"Ticket médio: R$ {ticket_medio:,.2f}")

    print("\nFaturamento diário:")
    for dia in sorted(por_dia):
        print(f"  {dia}: R$ {por_dia[dia]:,.2f}")


def main():
    print("Dashboard de Vendas - eGestor")
    print("O personal_token será solicitado apenas para esta execução.\n")
    personal_token = input("Informe seu personal_token: ").strip()
    if not personal_token:
        raise SystemExit("personal_token não informado.")

    access_token = obter_access_token(personal_token)
    vendas = buscar_vendas_mes(access_token)
    faturamento, quantidade, ticket_medio, por_dia = calcular_metricas(vendas)
    imprimir_metricas(faturamento, quantidade, ticket_medio, por_dia)


if __name__ == "__main__":
    main()
