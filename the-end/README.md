# THE END — Commerce OS

Plataforma de gestão comercial para operações de varejo. Esta entrega é um **protótipo funcional local**: vendas simuladas, catálogo, estoque, clientes/CRM, cashback, acompanhamento de meta e painel fiscal informativo.

## O que já funciona

- Dashboard com indicadores calculados a partir de vendas realmente cadastradas no protótipo.
- Cadastro/edição de produtos, preços, custos, SKUs únicos, limite mínimo de estoque.
- Cadastro/edição de clientes com observações, telefone, e-mail e histórico de vendas.
- PDV demonstrativo com múltiplos itens, quantidades, desconto, forma de pagamento informada e associação de cliente.
- Validação de saldo disponível no estoque antes da venda.
- Baixa automática do estoque e lançamento em histórico de movimentações.
- Geração/resgate de cashback para cliente identificado, com extrato de créditos e débitos.
- Inventário com ajustes positivos/negativos justificados e bloqueio de estoque negativo.
- Configuração de meta global e taxa de cashback.
- Exportação/importação do backup JSON no navegador.
- Testes automatizados das regras centrais, sem dependências externas.

## Como executar

Requisitos: Python 3 (ou qualquer servidor HTTP estático). Não precisa instalar frameworks nem banco de dados.

```bash
cd the-end
python -m http.server 3000
```

Abra **http://localhost:3000** no navegador. Use Chrome, Edge ou Firefox. **Não abra `index.html` diretamente pelo Explorador:** módulos JavaScript costumam exigir origem HTTP.

Alternativamente, quem já usa Node.js pode executar `npx serve -l 3000 .`.

### Testes

Requer Node.js 20 ou superior:

```bash
npm test
```

## Pastas

```text
the-end/
├── index.html
├── assets/
│   ├── app.js       # Interface e fluxos do protótipo
│   ├── domain.js    # Regras de negócio, em centavos e testáveis
│   ├── data.js      # Persistência local e dados de exemplo
│   └── styles.css   # Identidade visual responsiva
├── docs/
│   ├── ARCHITECTURE.md
│   └── ROADMAP.md
├── tests/
│   └── domain.test.js
└── package.json
```

## Avisos importantes

**Este projeto não está pronto para uso comercial nem produção.** Seu armazenamento é `localStorage`, localizado no navegador e dispositivo onde for usado. Não há login, permissões, servidor transacional, persistência centralizada, conciliação bancária, captura de pagamentos ou emissão fiscal. Dados podem ser apagados pelo navegador. Não utilize dados pessoais reais, informações financeiras sensíveis ou operações comerciais efetivas.

As modalidades de pagamento são rótulos informativos e não movimentam dinheiro. O módulo fiscal mostra “não emitido” e não gera NF-e/NFC-e. Lucro bruto é apenas uma estimativa contábil simplificada.

Para evoluir até produção, seguir o [ROADMAP](docs/ROADMAP.md) e a [ARCHITECTURE](docs/ARCHITECTURE.md).

## Publicação no GitHub

O repositório previsto é `https://github.com/Davi4545/the-end`. Quando tiver permissões de escrita (ou via terminal autenticado), publique:

```bash
git init
git branch -M main
git add .
git commit -m "feat: initial The End functional prototype"
git remote add origin https://github.com/Davi4545/the-end.git
git push -u origin main
```

Se já houver arquivos no repositório remoto, primeiro sincronize o histórico antes de enviar. Não sobrescreva alterações existentes.
