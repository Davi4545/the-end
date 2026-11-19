# Venqra — Release Candidate v1.0 (DESENVOLVIMENTO)

**Status:** versão candidata para demonstração e avaliação local. **Não é um ERP 100% homologado nem deve ser colocado em produção ou usado para registrar vendas reais.**

A interface premium é um painel web conectado a um backend Python (biblioteca padrão) e banco SQLite. Nenhum framework ou pacote precisa ser instalado com `pip`.

## Começar no Windows, sem digitar comandos

1. Instale Python 3.10+ com a opção **Add Python to PATH** (caso ainda não esteja instalado).
2. Extraia todo o ZIP em uma pasta.
3. Abra `CONFIGURAR-PRIMEIRO-ACESSO.bat`, informe dados da empresa, administrador e senha com no mínimo 12 caracteres.
4. Abra `INICIAR-WINDOWS.bat`. **Deixe a janela aberta** enquanto utiliza o aplicativo.
5. Abra **http://127.0.0.1:3000** no navegador e entre com o usuário criado.
6. Para fazer cópia íntegra do banco, use `FAZER-BACKUP-WINDOWS.bat`.

Para migrar dados de uma v0.4 existente, feche ambos os servidores, faça cópia de segurança e transfira o arquivo `the_end.db` para a raiz desta versão. O banco recebe automaticamente as tabelas novas ao iniciar. **Não sobrescreva bancos sem manter cópia.**

## Módulos incluídos

| Área | Entrega verificável | Limite atual |
|---|---|---|
| Login | Senha com PBKDF2, sessão expirada em 12h, perfis | Sem autenticação multifator/rate limiting |
| Organizações | Estrutura de organização/unidade e escopo na API | Sem SaaS de provisionamento automático |
| Vendas | Carrinho, preços recalculados no servidor, baixa de estoque, chave de idempotência | Pagamento apenas informado, não confirmado |
| Orçamentos | Orçamento com itens e valores persistidos | Não converte automaticamente em venda |
| Produtos | Código SKU, preço e custo | Sem variantes, lotes, fotos ou código de barras dedicado |
| Inventário | Saldos por loja, ajuste, movimentações e transferência transacional | Sem coleta com leitor nem integração logística |
| CRM | Cadastro, tarefas, oportunidades e histórico vinculado às vendas | Sem disparo de WhatsApp, e-mail ou consentimento gerenciado |
| Cashback | Acúmulo, resgate, extrato, política ajustável por empresa | Promocional demonstrativo; sem expiração e controles antifraude completos |
| Devoluções | Devolução parcial limitada à quantidade vendida, reentrada em estoque | Reembolso financeiro e documento fiscal NÃO realizados |
| Financeiro | Contas a pagar/receber, vencimentos e baixa manual | Sem bancos, conciliação ou cobrança real |
| Metas | Metas mensais por filial | Sem comissões ou metas por vendedor |
| Inteligência | Alertas de baixo estoque, inatividade, saldo financeiro aberto | Heurísticas básicas, não é previsão por IA |
| Relatórios | Vendas diárias, produtos e contas | Não calcula tributos nem confirma lucro realizado |
| Fiscal | Bloqueio explícito de emissão | Sem NF-e/NFC-e, certificado, Sefaz ou homologação |
| Auditoria | Registro de operações principais | Revisão de abrangência ainda necessária |
| Backups | Cópia consistente SQLite com `integrity_check` | Sem criptografia e política de retenção automáticas |

## Segurança e isolamento

- Servidor vinculado a **127.0.0.1**, sem exposição pública.
- APIs requerem token e estabelecem o escopo pelo usuário autenticado.
- Operações de movimentação/venda são executadas em transação SQLite.
- Valores monetários são armazenados em centavos inteiros.
- O navegador exibe alertas persistentes de ambiente de desenvolvimento.
- O cashback registra crédito demonstrativo mesmo que o pagamento não tenha sido confirmado. Não tratar como saldo resgatável real.
- Não armazenar dados financeiros reais, cartões, CPF ou outras informações pessoais sensíveis nesta versão.

## Executar testes

```bash
python -m unittest discover -s tests -v
node --check web/app.js
```

## Limitações para lançamento comercial

Antes de poder chamar o Venqra de **v1.0 homologada** é indispensável realizar: integração com provedor de pagamentos e webhooks idempotentes, integração fiscal NF-e/NFC-e conforme UF/regime, fluxo de devoluções e estornos fiscais/financeiros, permissões granulares, controles antifraude e de fidelização, LGPD (retenção/consentimentos/solicitações dos titulares), implantação com HTTPS, proteção de login, monitoramento, backup criptografado com restauração verificada, migração para infraestrutura apropriada, testes de ponta a ponta e piloto supervisionado com empresas.

**Esta entrega é `v1.0-rc`, não `v1.0` aprovada para produção.**

Destino do código: https://github.com/Davi4545/the-end. A integração do GitHub disponível anteriormente negou autorização para alterações. Este pacote é uma cópia local e não significa que foi publicado.

## Identidade e compatibilidade

- Nova identidade Venqra, com paleta preta/roxa, logotipo vetorial e favicon.
- A URL local, as rotas e os fluxos do backend permanecem iguais à versão anterior.
- Para não quebrar bancos existentes, o arquivo continua denominado `the_end.db` e a variável de ambiente `THE_END_DB` continua aceita. São nomes internos legados, **não** o nome público do produto.
- O token anterior `the_end_token` é lido apenas para continuidade da sessão e removido após login; novas sessões usam `venqra_token`.
- A marca Venqra ainda precisa de verificação jurídica de disponibilidade para uso comercial.
- O arquivo `PREVIA-VENQRA.html` é uma amostra estática de identidade, independente do servidor e sem dados reais.
