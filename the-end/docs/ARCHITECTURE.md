# Arquitetura alvo do The End

## Norte do produto

Um sistema único para o varejista gerir seu negócio: venda + cliente + fidelidade + estoque + financeiro + fiscal + metas, com políticas padronizadas, rastreabilidade e visão integrada por canal e unidade.

## Decisão inicial

**Monólito modular com API transacional e PostgreSQL**, em vez de microserviços prematuros. O protótipo atual é uma SPA estática e usa `localStorage` **somente para demonstrar o produto**. A migração para uma API e base relacional é condição para uso comercial real.

Módulos de domínio propostos:

- `identity`: organizações, empresas, unidades, usuários, papéis e permissões.
- `catalog`: produtos, variantes, SKUs, tabelas de preço e tributação por item.
- `sales`: pedidos, itens, descontos, devoluções, pagamentos e sessões de caixa.
- `inventory`: saldos, reservas, transferências, inventários e ledger de movimentações.
- `crm`: cadastro 360°, jornadas, segmentação, consentimento e tarefas.
- `loyalty`: carteira, cashback, regras, expiração, estornos e antifraude.
- `finance`: recebíveis, liquidação, contas a pagar, taxas, conciliação e fluxo de caixa.
- `fiscal`: documentos fiscais, assinaturas/credenciais seguras, integradores, eventos e rejeições.
- `goals`: metas por unidade, vendedor e período, comissões e produtividade.
- `analytics`: agregações, relatórios e detecção de oportunidades.

## Requisitos não funcionais

1. Isolamento por organização (`organization_id`) validado no servidor e integrado a RBAC.
2. Senhas armazenadas apenas com função de hash robusta; autenticação MFA quando aplicável.
3. Validação de entradas no servidor, limites de taxa, logs de auditoria e política de backups com restauração testada.
4. Idempotência em fechamento de vendas, pagamentos, cashback e integrações externas.
5. Persistir valores monetários em centavos inteiros ou DECIMAL; evitar float para dinheiro.
6. Saldos de estoque e carteiras reconciliados a partir de eventos/lançamentos. Estorno não apaga histórico.
7. Saída assíncrona via outbox para sincronização fiscal, notificação, CRM, e-commerce e BI.
8. LGPD: minimização de dados, base legal, controles de acesso, retenção e direitos dos titulares.
9. Observabilidade: correlação de eventos, métricas, rastreamento, alertas e monitoramento de integrações.
10. Políticas de desconto e acesso a dados sensíveis são geridas por papéis, hierarquia e trilha de auditoria.

## Fluxo de venda em produção

1. Identificação de organização/unidade/operador.
2. Validação de tabela de preços, desconto autorizado, cliente e estoque reservado.
3. Registro do pedido com chave idempotente e estado `pending_payment`.
4. Processamento assíncrono ou síncrono de pagamento com provedor homologado.
5. Confirmação atômica de venda, movimento de estoque e contas a receber.
6. Solicitação fiscal ao provedor e registro de autorização/rejeição conforme documento/UF/tributação.
7. Crédito de cashback após condição elegível e tratamento de reversões.
8. Eventos para metas, CRM e analytics.

## Fiscal e privacidade

O Brasil possui regras fiscais complexas e sujeitas a mudanças. Emissão de NF-e e NFC-e requer implementação alinhada às especificações e notas técnicas oficiais, além de configuração por regime tributário, CNPJ, UF e tipo de operação. Homologar com contador e integrador especializado.

Referências institucionais:
- Portal Nacional NF-e — https://www.nfe.fazenda.gov.br/portal/
- Documentação NFC-e da SVRS — https://dfe-portal.svrs.rs.gov.br/NFCE/Documentos
- Segurança da informação ANPD — https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-orientativo-sobre-seguranca-da-informacao-para-agentes-de-tratamento-de-pequeno-porte

## Diferenciais que merecem investimento

- Motor de recomendações explicáveis: previsão de ruptura, estoque parado, clientes inativos e risco de meta.
- CRM que nasce da venda, sem redigitação entre PDV e marketing.
- Cashback com margem protegida, expiração transparente e regras por categoria/canal.
- Indicadores que explicam *por que* a meta não está sendo alcançada, em vez de mostrar apenas gráficos.
- Integrações omnichannel e rastreabilidade das alterações de preço, desconto, estoque e caixa.

## Situação desta entrega

**Demonstrável:** navegação, cadastros básicos, vendas locais simuladas, movimentação de estoque, crédito/resgate de cashback, metas, extrato e backup no navegador.

**Não implementado:** serviços de servidor, PostgreSQL, integração fiscal, pagamento real, RBAC, sincronização multifilial, API, compartilhamento entre usuários, emissão de nota, autenticação e políticas de segurança de produção.
