# Roadmap Venqra

## Implementado na fundação v0.2
- [x] API local e banco SQLite persistente
- [x] Autenticação, sessão e papéis básicos
- [x] Organizações e filiais
- [x] Produtos e clientes
- [x] Estoque, movimentações e vendas demonstrativas
- [x] Cashback como ledger demonstrativo
- [x] Metas por filial e trilha de auditoria

## Próximos blocos de desenvolvimento
- [ ] Migrar para PostgreSQL e preparar migrações versionadas
- [ ] Controle fino de permissões, vínculo de vendedor a lojas e segurança de produção
- [ ] Histórico detalhado e edição segura de produtos e clientes
- [ ] Gestão de pedidos, orçamentos, devoluções e reserva de estoque
- [ ] Integração real de pagamentos, webhooks assinados, conciliação e estornos
- [ ] Política versionada de cashback, validade, bloqueios e antifraude
- [ ] CRM: tarefas, funil, campanhas e consentimento LGPD
- [ ] Metas por vendedor/equipe, comissões e regras de cálculo
- [ ] Financeiro: contas, caixa e fechamento
- [ ] Adapters para e-commerce, mensageria e integrador fiscal
- [ ] Fluxos NF-e/NFC-e com configuração e homologação tributária por cenário
- [ ] Observabilidade, backup, restauração, deploy seguro

## Testes e homologação
A campanha completa de testes ocorrerá após completar os módulos; entretanto, verificações de integridade, autenticação e transações devem permanecer contínuas para evitar regressões graves.
