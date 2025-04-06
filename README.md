# Ofertas Processor - Processamento de Dados de Ofertas em XML

## 📌 Visão Geral

O **Ofertas Processor** é um script Python projetado para automatizar o processamento de arquivos XML contendo dados de ofertas comerciais. Ele realiza a consolidação, normalização e integração desses dados com informações corrigidas pré-existentes, gerando relatórios em formato Excel prontos para análise.

## ✨ Funcionalidades Principais

- **Processamento Automatizado** de múltiplos arquivos XML em lote
- **Normalização inteligente** de nomes de arquivos (remoção de acentos e padronização)
- **Consolidação de dados** de diferentes fontes em uma única planilha
- **Integração com dados corrigidos** evitando duplicações
- **Geração de relatórios** em Excel formatados e prontos para uso

## 🛠️ Tecnologias Utilizadas

- **Python 3** (com type hints)
- **Pandas** para manipulação de dados tabulares
- **xmltodict** para parsing de arquivos XML
- **glob/os** para manipulação de arquivos

## 📂 Estrutura do Projeto

```
ofertas-processor/
├── dados_brutos/          # Pasta com arquivos XML de entrada
├── dados_produtos_corrigidos.xlsx  # Base de dados corrigidos
├── ofertas_consolidadas.xlsx       # Saída consolidada
├── ofertas_corrigidas.xlsx         # Saída final integrada
└── processador_ofertas.py          # Script principal
```

## 🚀 Como Usar

1. Coloque seus arquivos XML na pasta `dados_brutos/`
2. Execute o script Python:
   ```bash
   python processador_ofertas.py
   ```
3. Os arquivos de saída serão gerados automaticamente:
   - `ofertas_consolidadas.xlsx` - Todos os produtos processados
   - `ofertas_corrigidas.xlsx` - Dados integrados com informações corrigidas

## 🌟 Benefícios

- **Economia de tempo** ao processar centenas de arquivos manualmente
- **Padronização automática** dos dados
- **Facilidade de integração** com sistemas existentes
- **Código limpo e modular** seguindo boas práticas de programação funcional

## 🤝 Como Contribuir

Contribuições são bem-vindas! Sinta-se à vontade para:
- Reportar issues
- Sugerir melhorias
- Enviar pull requests

## 📄 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

Desenvolvido com ❤️ para automatizar processos tediosos e transformar dados brutos em informações valiosas!
