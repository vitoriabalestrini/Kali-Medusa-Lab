# Laboratório de Segurança Ofensiva — Kali Linux, Medusa e Metasploitable 2

> Projeto educacional de simulação controlada de tentativas de autenticação em FTP, DVWA (web) e SMB. **Não execute contra sistemas de terceiros ou redes públicas.** Resultados reais dependem da execução das VMs.

## Objetivos

- Construir duas VMs isoladas no VirtualBox (Kali Linux e Metasploitable 2).
- Demonstrar diferenças entre força bruta de senhas, tentativas automatizadas no formulário e *password spraying*.
- Validar, com evidências, comportamentos de autenticação e medidas de mitigação.
- Produzir relatório reprodutível, com limite rigoroso de tentativas.

## Arquitetura

```text
                   REDE HOST-ONLY ISOLADA (ex.: 192.168.56.0/24)
      +--------------------+                 +-----------------------+
      | Kali Linux         | --------------> | Metasploitable 2       |
      | 192.168.56.10      | 21 FTP           | 192.168.56.20         |
      | Medusa / curl      | 80 DVWA          | vsftpd / Apache / SMB  |
      | smbclient / Python | 139/445 SMB      | serviços vulneráveis   |
      +--------------------+                 +-----------------------+
```

IPs ilustrativos: substitua pelos endereços observados nas VMs. `Host-only` **não é** a modalidade `Internal Network`: ambas podem isolar VMs, mas host-only também permite comunicação com o host. **Não habilite bridge nem encaminhamento de portas.** Para máximo isolamento, desative acesso do host à rede e prefira `Internal Network`; se a atividade exigir host-only, mantenha apenas essa interface nas VMs durante os testes.

## Requisitos

- VirtualBox e imagens legais/oficiais de Kali Linux e Metasploitable 2.
- RAM e armazenamento suficientes para duas VMs.
- Ferramentas no Kali: `medusa`, `nmap`, `smbclient`, `rpcclient`, `curl`, `python3` e biblioteca Python `requests`.
- Rede estritamente privada, com snapshots e sem dados pessoais.

### 1. Preparação das VMs

1. Importe ou instale as duas VMs e crie um snapshot limpo de cada uma.
2. VirtualBox → Configurações → Rede → Adaptador 1 → **Adaptador somente-anfitrião (Host-only)**, mesmo adaptador nas duas VMs. Desabilite adaptadores NAT/bridge durante a execução. A atribuição IP pode ser feita por DHCP host-only ou IP fixo.
3. Em cada VM, execute `ip -4 addr`. Ajuste a rede, se necessário, e registre os IPs encontrados. O exemplo abaixo usa **192.168.56.10** (Kali) e **192.168.56.20** (alvo).
4. No Kali, instale dependências usando repositórios confiáveis, quando houver conectividade temporária para atualização **antes** do laboratório:

   ```bash
   sudo apt update
   sudo apt install -y medusa nmap smbclient python3-requests curl
   ```

5. Retorne a VM ao modo isolado (somente host-only). Confirme o alvo com:

   ```bash
   ping -c 2 192.168.56.20
   nmap -sT -sV -p 21,80,139,445 192.168.56.20
   ```

**Observação:** o Metasploitable 2 costuma oferecer serviços FTP, HTTP e SMB, mas portas, contas, versões e DVWA devem ser confirmados na imagem efetivamente utilizada. A execução de `nmap` aqui está limitada a um IP autorizado.

## Cenário A — Força bruta controlada em FTP (Medusa)

**Hipótese:** senhas simples para um usuário conhecido podem permitir autenticação.

1. Identifique o serviço na porta 21 e confirme uma conta **do laboratório**. Em instalações padrão de Metasploitable 2, a conta `msfadmin` costuma existir, com senha `msfadmin`; verifique localmente.
2. Inspecione `wordlists/ftp-demo.txt` (apenas quatro possibilidades).
3. Execute um teste deliberadamente limitado:

```bash
medusa -h 192.168.56.20 -u msfadmin -P wordlists/ftp-demo.txt -M ftp -t 1 -f
```

`-h` alvo único; `-u` conta de laboratório; `-P` arquivo pequeno de senhas; `-M ftp` módulo; `-t 1` concorrência mínima; `-f` para ao encontrar senha válida. Valide o resultado por login manual no serviço ou pelo log local. Nunca publique credenciais reais.

## Cenário B — Formulário web DVWA (nível Low)

**Importante:** o Medusa não possui um módulo genérico e universal que resolva qualquer formulário HTTP com cookies, redirects e tokens CSRF. Para o DVWA, usamos um **script Python pequeno** voltado exclusivamente ao endpoint local da aplicação e à configuração **Low**. O Medusa permanece como ferramenta principal nos cenários de FTP e SMB.

1. Abra `http://192.168.56.20/dvwa/` no Kali e configure/reset o banco DVWA, se necessário (geralmente em `/dvwa/setup.php`).
2. Faça login **manualmente** na aplicação de laboratório. Em imagens tradicionais do DVWA, as credenciais padrão costumam ser `admin` / `password`; confirme no ambiente.
3. Configure `DVWA Security` para **Low**. Crie/identifique o cookie `PHPSESSID` da **sua própria sessão de laboratório** pelo navegador (Ferramentas de desenvolvedor → Armazenamento/Cookies). Não divulgue o valor do cookie.
4. Execute o script, que impõe limites de IP, caminho e número de tentativas:

```bash
export DVWA_SESSION='COLE_SOMENTE_O_PHPSESSID_DA_SUA_VM'
python3 scripts/dvwa_low_demo.py --target 192.168.56.20 --user admin --wordlist wordlists/web-demo.txt
unset DVWA_SESSION
```

O script usa requisições GET para `/dvwa/vulnerabilities/brute/` como no modo Low clássico, um atraso entre tentativas e só aceita destino `192.168.56.0/24` (ou localhost). **Não funciona automaticamente nos níveis Medium/High/Impossible**, que exigem tratamento distinto e podem ter proteção CSRF, bloqueio ou lógica de aplicação alterada. Se o DVWA estiver instalado em outro path, ajuste o laboratório e o script conscientemente.

## Cenário C — SMB: enumeração e *password spraying* de laboratório

**Diferença:** força bruta normalmente testa várias senhas contra uma conta; *spraying* tenta **uma única senha** contra poucas contas previamente identificadas, reduzindo a concentração de erros por usuário. Pode ainda gerar alertas, bloqueios ou risco operacional.

1. Verifique SMB no alvo:

```bash
smbclient -L //192.168.56.20 -N
rpcclient -U '' -N 192.168.56.20 -c 'enumdomusers'
```

Uma instalação de laboratório pode bloquear enumeração anônima: nesse caso, registre a falha e use **apenas contas de teste confirmadas localmente**. `wordlists/smb-users-demo.txt` contém exemplos e deve ser ajustado aos usuários existentes na VM.

2. Realize **uma senha por usuário**, de forma serial, com Medusa:

```bash
medusa -h 192.168.56.20 -U wordlists/smb-users-demo.txt -p lab123 -M smbnt -t 1
```

`-U` contém usuários do laboratório; `-p` define a única senha candidata para o ciclo; `-M smbnt` módulo SMB/NT; `-t 1` reduz paralelismo. Alguns builds/servidores têm diferenças de compatibilidade SMB; consulte `medusa -d` e `medusa -M smbnt -q` e registre eventuais erros sem alegar sucesso. `lab123` é uma senha fictícia: só há resultado positivo se você tiver configurado uma conta de teste correspondente. **Não use listas vazadas nem tente contas fora da VM**.

3. Não repita ciclos continuamente. Documente quantidade de contas, tentativas, resposta, tempo e eventuais bloqueios.

## Checklist de evidências

- [ ] Screenshots das duas VMs com a rede host-only configurada (sem dados sensíveis)
- [ ] Endereços IP conferidos em `ip -4 addr`
- [ ] Portas efetivamente observadas por `nmap`
- [ ] Logs de FTP com segredo ocultado
- [ ] Tela ou log de tentativa DVWA, com cookie removido
- [ ] Resultado de enumeração SMB (inclusive acesso negado, se houver)
- [ ] Saída Medusa SMB, com usuários anonimizados, quando aplicável
- [ ] Tabela de resultados e comparação de controles defensivos

Preencha `docs/RELATORIO.md`; guarde imagens censuradas em `evidencias/` (não disponibilize identificadores de rede real, tokens ou segredos).

## Mitigações e aprendizagem

| Superfície | Risco testado | Proteções sugeridas |
|---|---|---|
| FTP | Senha fraca e autenticação repetida | Desativar FTP legado; preferir SFTP; senhas fortes; limites de tentativa; logs; segmentação |
| DVWA/Web | Adivinhação automatizada no login | Rate limiting por conta/IP, MFA quando aplicável, delays adaptativos, logs e alertas, monitoramento de padrões anômalos |
| SMB | Senha comum em várias contas | Desabilitar SMBv1 e acesso guest, senhas únicas, MFA onde suportado, políticas de bloqueio calibradas, monitoramento e segmentação |

**Cuidado:** limitação apenas por IP é insuficiente quando há proxies/NAT; bloqueios rígidos também podem causar negação de serviço. Use uma estratégia de camadas e analise falsos positivos.

## Estrutura

```text
kali-medusa-lab/
├── README.md
├── .gitignore
├── LICENSE
├── wordlists/
│   ├── ftp-demo.txt
│   ├── web-demo.txt
│   └── smb-users-demo.txt
├── scripts/
│   └── dvwa_low_demo.py
├── docs/
│   └── RELATORIO.md
└── evidencias/
    └── .gitkeep
```

## Referências

- Kali Linux Documentation: https://www.kali.org/docs/
- Medusa (Kali Tools): https://www.kali.org/tools/medusa/
- Metasploitable 2: https://docs.rapid7.com/metasploit/metasploitable-2/
- DVWA (projeto oficial): https://github.com/digininja/DVWA
- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html

## Escopo ético

Uso exclusivo em sistemas próprios, máquinas intencionalmente vulneráveis ou instalações com autorização explícita. Não use infraestrutura pública, terceiros ou credenciais reais. A palavra “sucesso” no relatório deve corresponder a teste verificado; exemplos não equivalem a resultados.
