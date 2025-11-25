"""
Exemplo em Python para montar um dashboard de vendas do mês atual
usando a API do eGestor. O personal_token é pedido em tempo de
execução e nunca deve ser salvo no código ou em repositórios.
"""
from __future__ import annotations

import argparse
import calendar
import json
from datetime import date
from typing import Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://api.egestor.com.br/api"


class APIRequestError(RuntimeError):
    """Erro genérico para chamadas HTTP."""


def _post_form(url: str, data: Dict[str, str], timeout: int = 15) -> Dict:
    payload = urlencode(data).encode()
    requisicao = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urlopen(requisicao, timeout=timeout) as resposta:
            return json.loads(resposta.read().decode())
    except HTTPError as exc:  # erro HTTP com código
        raise APIRequestError(f"HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:  # erro de rede
        raise APIRequestError(str(exc)) from exc


def _get_json(url: str, headers: Dict[str, str] | None = None, timeout: int = 30) -> Dict:
    requisicao = Request(url, headers=headers or {}, method="GET")
    try:
        with urlopen(requisicao, timeout=timeout) as resposta:
            return json.loads(resposta.read().decode())
    except HTTPError as exc:
        raise APIRequestError(f"HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise APIRequestError(str(exc)) from exc


def obter_access_token(personal_token: str, api_base: str = API_BASE) -> str:
    """
    Troca o personal_token por um access_token temporário.
    O personal_token deve ser coletado em tempo de execução.
    """

    payload = _post_form(
        f"{api_base}/oauth/access_token",
        data={
            "grant_type": "personal",
            "personal_token": personal_token,
        },
    )
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


def buscar_vendas_mes(access_token: str, api_base: str = API_BASE) -> List[Dict]:
    datas = intervalo_mes_atual()
    query = urlencode(
        {
            "dtTipo": "dtVenda",
            "dtIni": datas["dtIni"],
            "dtFim": datas["dtFim"],
            "tipo": "50",  # apenas vendas, exclui orçamentos
            "orderBy": "dtVenda,asc",
        }
    )

    url = f"{api_base}/v1/vendas?{query}"
    payload = _get_json(url, headers={"Authorization": f"Bearer {access_token}"})
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


def mock_vendas_mes_atual() -> List[Dict]:
    return [
        {"dtVenda": "2024-08-01", "valorTotal": 1520.75},
        {"dtVenda": "2024-08-01", "valorTotal": 300.25},
        {"dtVenda": "2024-08-02", "valorTotal": 820.40},
        {"dtVenda": "2024-08-03", "valorTotal": 2100.00},
    ]


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Dashboard de vendas do mês atual usando a API do eGestor. "
            "Informe o personal_token somente em tempo de execução."
        )
    )
    parser.add_argument(
        "--base-url",
        default=API_BASE,
        help="URL base da API (padrão: https://api.egestor.com.br/api)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Usa dados simulados em vez de chamar a API (não precisa de token).",
    )
    args = parser.parse_args()

    print("Dashboard de Vendas - eGestor")

    if args.mock:
        vendas = mock_vendas_mes_atual()
    else:
        print("O personal_token será solicitado apenas para esta execução.\n")
        personal_token = input("Informe seu personal_token: ").strip()
        if not personal_token:
            raise SystemExit("personal_token não informado.")

        try:
            access_token = obter_access_token(personal_token, api_base=args.base_url)
            vendas = buscar_vendas_mes(access_token, api_base=args.base_url)
        except APIRequestError as exc:
            raise SystemExit(f"Erro ao consultar a API: {exc}") from exc

    faturamento, quantidade, ticket_medio, por_dia = calcular_metricas(vendas)
    imprimir_metricas(faturamento, quantidade, ticket_medio, por_dia)


if __name__ == "__main__":
    main()
