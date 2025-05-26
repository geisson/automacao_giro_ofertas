# Automação de Processamento de Ofertas XML

Este script Python automatiza o processamento de arquivos XML contendo ofertas de produtos, gerando um relatório final em Excel com dados consolidados, corrigidos e formatados.

## Funcionalidades Principais

1. **Leitura de XMLs:**
    * Lê múltiplos arquivos XML de um diretório de entrada especificado (`./arquivos_xml_entrada/`).
    * Normaliza os nomes dos arquivos XML (converte para minúsculas e remove acentuação).
    * Parseia os dados XML para extrair informações de produtos: ID, nome do produto no sistema, descrição da promoção e preço promocional.

2. **Cadastro de Produtos (Correção e Enriquecimento):**
    * Utiliza um arquivo Excel mestre (`./produtos_cadastrados.xlsx`) para armazenar uma lista de produtos com seus IDs, nomes originais do sistema, seções (categorias) e nomes corrigidos/padronizados.
    * **Colunas do `produtos_cadastrados.xlsx`:**
        * `ID`: Identificador único do produto.
        * `SESSÃO`: Categoria/seção do produto (ex: "#01 MERCEARIA", "#03 LIMPEZA").
        * `NOME_SISTEMA`: Nome do produto como vem originalmente do XML.
        * `NOME_CORRIGIDO`: Nome do produto após correções manuais ou padronização.
    * Ao processar novos XMLs, o script identifica produtos que ainda não existem no `produtos_cadastrados.xlsx` e os adiciona automaticamente. Novos produtos recebem "SEÇÃO NÃO ESPECIFICADA" como seção padrão e o `NOME_SISTEMA` como `NOME_CORRIGIDO` inicial, permitindo posterior edição manual no arquivo Excel.

3. **Consolidação e Geração de Relatório Final (`./giro_da_praça_ofertas.xlsx`):**
    * Combina os dados das ofertas atuais (dos XMLs) com as informações do `produtos_cadastrados.xlsx` (seções e nomes corrigidos).
    * **Agrupamento Inteligente de Produtos:**
        * Produtos com o mesmo "nome base" (nome até a unidade/medida, ex: "PRODUTO X 500G") e mesmo preço promocional são agrupados em uma única linha no relatório final.
        * Este agrupamento é **desabilitado** para produtos pertencentes a seções específicas (atualmente "#01 MERCEARIA - #01 ALTO GIRO" e "#01 MERCEARIA - #02 ALTO GIRO").
    * **Ordenação:** As ofertas no relatório são ordenadas por uma chave de grupo de seção principal, depois pela seção completa e, por fim, pelo nome do produto.
    * **Formatação do Excel:**
        * O relatório final (`giro_da_praça_ofertas.xlsx`) é formatado para melhor legibilidade:
            * Colunas na ordem: `NOME_PROMOÇÃO`, `SESSÃO`, `ID`, `PRODUTO`, `PROMOÇÃO` (valor).
            * A coluna `PROMOÇÃO` (valor) é formatada como contábil (R$ #,##0.00).
            * Bordas são aplicadas às células de dados.
            * Linhas em branco são inseridas entre diferentes grupos principais de seções e **não** possuem bordas.
            * A largura das colunas é ajustada automaticamente ao conteúdo.
            * As linhas de grade padrão do Excel são ocultadas na planilha gerada.

## Como Usar

### Pré-requisitos

* Python 3.7+
* Bibliotecas Python (instalar via pip):

    ```bash
    pip install pandas openpyxl xmltodict
    ```

### Estrutura de Pastas e Arquivos Esperada

O script espera a seguinte estrutura na pasta raiz onde ele é executado:

```md

seu_projeto/
├── app.py (ou o nome do seu script principal)
├── arquivos_xml_entrada/
│   ├── oferta1.xml
│   ├── oferta2.xml
│   └── ... (outros arquivos XML de ofertas)
└── produtos_cadastrados.xlsx (opcional na primeira execução, será criado se não existir)

```

* **`app.py`**: O script Python principal.
* **`arquivos_xml_entrada/`**: Diretório onde os arquivos XML de ofertas devem ser colocados. O script irá ler todos os arquivos `.xml` desta pasta.
* **`produtos_cadastrados.xlsx`**: Arquivo mestre para correções e categorização de produtos. Se não existir na primeira execução, o script o criará. É fundamental para manter os nomes dos produtos e suas seções corretas ao longo do tempo.

### Execução

1. Certifique-se de que os pré-requisitos estão instalados.
2. Coloque os arquivos XML de ofertas na pasta `./arquivos_xml_entrada/`.
3. (Opcional, mas recomendado após a primeira execução) Verifique e edite o arquivo `./produtos_cadastrados.xlsx` para corrigir nomes de produtos ou atribuir seções.
4. Execute o script Python a partir da pasta raiz do projeto:

    ```bash
    python app.py
    ```

### Saídas

* **`./produtos_cadastrados.xlsx`**: Será criado ou atualizado com novos produtos encontrados nos XMLs.
* **`./giro_da_praça_ofertas.xlsx`**: O relatório final consolidado e formatado com as ofertas processadas.

## Configuração Interna (Constantes no Script)

* `INPUT_XML_DIR`: Diretório de entrada para os arquivos XML (padrão: `./arquivos_xml_entrada/`).
* `PRODUCT_MASTER_FILE_NAME`: Nome do arquivo de cadastro de produtos (padrão: `produtos_cadastrados.xlsx`).
* `FINAL_OFFERS_REPORT_NAME`: Nome do arquivo de relatório final (padrão: `giro_da_praça_ofertas.xlsx`).
* `SECOES_EXCECAO_AGRUPAMENTO`: Lista de seções cujos produtos não devem ser agrupados mesmo que atendam aos critérios de nome e preço (padrão: `["#01 MERCEARIA - #01 ALTO GIRO", "#01 MERCEARIA - #02 ALTO GIRO"]`).

## Lógica XML Esperada

O script espera que os dados dos produtos dentro do XML estejam em uma estrutura similar a:

```xml
<temporario_846>
  <temporario_846_row>
    <idsubproduto>12345</idsubproduto>
    <descrresproduto>NOME DO PRODUTO ABC 500G</descrresproduto>
    <precopromocao>10.99</precopromocao>
    <descrpromocao>OFERTA ESPECIAL</descrpromocao>
    <!-- outros campos -->
  </temporario_846_row>
  <temporario_846_row>
    <!-- ... outro produto ... -->
  </temporario_846_row>
</temporario_846>
```

As tags relevantes são `idsubproduto`, `descrresproduto`, `precopromocao`, e `descrpromocao` dentro de cada `temporario_846_row`.

## Solução de Problemas e Avisos

* **`FutureWarning` do Pandas:** O script foi atualizado para seguir as recomendações do Pandas e evitar estes avisos em versões futuras.
* **Avisos de Conversão de Número no Excel:** Se um produto no XML tiver um preço promocional vazio ou não numérico, o script tentará converter para 0.0. Se a conversão para formato contábil no Excel falhar para algum valor específico, uma mensagem de aviso será exibida, e o valor será mantido como texto.
* **Bordas em Linhas de Espaçamento:** A lógica foi refinada para garantir que as linhas em branco (espaçadoras) entre seções no relatório final não recebam bordas. As linhas de grade padrão do Excel também são desabilitadas para esta planilha.

---

Desenvolvido para otimizar o processo de criação de relatórios de ofertas.
