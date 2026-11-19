# Relatório de entrega — v1.0 RC

## Implementado

- Identidade visual integrada com API e persistência.
- Separação por organização e perfis em endpoints.
- Produtos, clientes, filiais, usuários, vendas demonstrativas, estoque e cashback.
- Orçamentos e itens, tarefas de CRM e oportunidades.
- Financeiro manual com lançamentos e baixa.
- Transferências entre lojas, devoluções administrativas parciais.
- Política de fidelidade por empresa.
- Alertas e relatórios operacionais, trilha de auditoria.
- Backup SQLite manual com verificação de integridade.

## Validação

- `unittest`: 10 testes automatizados aprovados no ambiente de criação.
- `node --check web/app.js`: análise sintática JavaScript aprovada.
- Smoke test HTTP local: página inicial, login e 11 endpoints GET aprovados.
- Renderização ponta a ponta no Chromium: não concluída, ambiente bloqueia acesso HTTP local.
- Integração fiscal e de pagamento: não implementadas; bloqueadas intencionalmente.

## Não confundir com produção

- Vendas são registradas sem captura real de pagamento.
- Devoluções não processam reembolso e podem exigir ajuste manual no cashback já gasto.
- Crédito de cashback não é garantia monetária.
- Fiscal é preparação, não emissão real de notas.
- Não existe infraestrutura cloud SaaS, isolamento por RLS, bilhetagem/assinaturas nem app mobile.
- O produto exige testes de cenários fiscais, financeiros e de segurança antes de atender clientes.
