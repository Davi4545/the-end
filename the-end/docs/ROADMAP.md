# Roadmap — The End

## Etapa 0 — protótipo de validação (entregue)
- [x] Identidade visual e navegação por módulos
- [x] Dashboard com dados calculados
- [x] Produtos, clientes e inventário local
- [x] Venda demonstrativa e regras de estoque
- [x] Cashback básico e metas da unidade
- [x] Testes de funções críticas
- [x] Exportação/importação de backup JSON

## Etapa 1 — MVP real e infraestrutura
- [ ] Backend TypeScript, API e PostgreSQL com migrações
- [ ] Cadastro de organizações/unidades e isolamento entre empresas
- [ ] Autenticação, RBAC e trilha de auditoria
- [ ] Regras de saldo e carrinho com operações transacionais e idempotentes
- [ ] CRUD e consultas paginadas, filtros, importação de catálogo
- [ ] Testes e pipeline CI/CD, backups e observabilidade

## Etapa 2 — PDV comercial
- [ ] Sessão de caixa, abertura, sangria e fechamento
- [ ] Pagamento via integrador, conciliação e estorno
- [ ] Orçamento, pedidos, trocas e devoluções
- [ ] Tabelas de preço, desconto sob aprovação e promoções
- [ ] Emissão fiscal integrada e homologada conforme operação-alvo

## Etapa 3 — fidelização e inteligência
- [ ] CRM 360° com histórico, segmentos e consentimentos
- [ ] Cashback por regra/campanha, expiração e estorno
- [ ] Metas por vendedor, equipe, loja e período
- [ ] Comissões auditáveis e dashboards por perfil
- [ ] Alertas inteligentes de ruptura, margem e clientes inativos

## Etapa 4 — omnichannel e escala
- [ ] Integrações com e-commerce, marketplaces e mensageria
- [ ] Reserva de estoque e retirada em loja
- [ ] Transferências entre unidades e compras de fornecedor
- [ ] Consolidação multiempresa/multifilial
- [ ] Segurança, performance, offline controlado e expansão gradual

## Critérios para produção

Sem ambiente produtivo antes de: autenticação e isolamento entre empresas; testes de segurança; backups e restauração; integrações homologadas; política de privacidade e auditoria; requisitos fiscais aplicáveis; recuperação de falhas e conciliação de saldos.
