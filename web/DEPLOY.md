# AnonShield Deployment Guide (Production Sandbox)

Este guia descreve como enviar e rodar o AnonShield no servidor compartilhado (`ppges-a9`) usando as configurações de segurança e sandbox preparadas.

## 1. Transferência de Arquivos

No seu computador local (na pasta raiz do projeto `tool`), execute o comando abaixo para sincronizar apenas a pasta de infraestrutura web para o servidor:

```bash
# Sincroniza a pasta web e o código fonte necessário (src e anon.py)
rsync -avz --progress --exclude 'node_modules' --exclude '.venv' . a9:~/anonshield_deploy/
```

## 2. Configuração no Servidor (SSH)

Acesse o servidor:
```bash
ssh a9
cd ~/anonshield_deploy/web
```

### Configurar Variáveis Sensíveis
Crie um arquivo `.env` na pasta `web` para manter seus dados privados:
```bash
echo "PUBLIC_API_URL=https://anonshield.org/api" > .env
# Opcional: E-mail para notificações de certificados SSL (Let's Encrypt)
# echo "CADDY_EMAIL=seu-email@exemplo.com" >> .env
```
*Atenção: Use o seu domínio real aqui.*

## 3. Inicialização (Sandbox Mode)

Como o servidor é compartilhado, vamos usar o arquivo de produção que contém os limites de hardware (32GB RAM / 8 CPUs) e travas de segurança:

```bash
sudo docker compose -f docker-compose.prod.yml up -d --build
```

O comando `--build` garante que as imagens sejam geradas com o código fonte atualizado (embutido no container).

## 4. Monitoramento e Manutenção

### Verificar logs
```bash
sudo docker compose -f docker-compose.prod.yml logs -f
```

### Verificar uso de recursos (Sandbox)
```bash
sudo docker stats
```
Isso mostrará quanto de RAM e CPU cada parte do AnonShield está consumindo no servidor compartilhado.

### Encerrar o serviço
```bash
sudo docker compose -f docker-compose.prod.yml down
```

## Resumo da Segurança do Sandbox
- **Rede**: Isolada internamente; apenas o Caddy (Reverse Proxy) expõe portas 80/443.
- **Usuários**: Nenhum container roda como `root`.
- **Escrita Local**: O sistema de arquivos do container é `read-only` em áreas críticas.
- **HTTPS**: Gerenciado automaticamente pelo Caddy via Let's Encrypt (ou ZeroSSL).
