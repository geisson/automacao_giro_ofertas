# Processador de Ofertas XML para Excel

Este script Python automatiza o processamento de arquivos XML contendo ofertas de produtos, consolida essas informações, atualiza um arquivo mestre de cadastro de produtos e gera um relatório final em formato Excel (`giro_da_praça_ofertas.xlsx`) com formatação avançada.

## Comandos de Execução

Para gerar o relatório do zero, substituindo qualquer versão anterior:

```bash
python processador_ofertas.py --mode create
```

ou simplesmente (pois `create` é o padrão):

```bash
python processador_ofertas.py
```

Para atualizar o relatório existente, destacando novos produtos ou alterações de preço:

```bash
python processador_ofertas.py --mode update
```

## Funcionalidades Principais

* **Leitura de Múltiplos XMLs:** Processa todos os arquivos `.xml` localizados no diretório `./arquivos_xml_entrada/`.
* **Normalização de Nomes:** Renomeia arquivos XML para um formato padronizado (sem acentos, minúsculas).
* **Consolidação de Dados:** Extrai informações de ID, nome do produto, preço promocional e descrição da promoção de cada XML.
* **Atualização do Cadastro Mestre (`produtos_cadastrados.xlsx`):**
  * Adiciona novos produtos encontrados nos XMLs ao arquivo de cadastro.
  * Destaca (com fundo verde) os produtos no arquivo de cadastro que estão presentes nas ofertas XML da execução atual.
  * Mantém o arquivo de cadastro ordenado.
* **Geração de Relatório de Ofertas (`giro_da_praça_ofertas.xlsx`):**
  * Agrupa produtos com o mesmo "nome base" (nome até a unidade/medida) e mesmo preço, criando uma coluna `TIPO` com as variações (ex: sabores, fragrâncias).
  * Exceções de agrupamento podem ser definidas para seções específicas.
  * Ordena o relatório por seções e insere linhas em branco entre grupos de seções.
  * Aplica formatação detalhada por coluna (fonte, tamanho, cor, formato de número, alinhamento) conforme configurado em `COLUMNS_FORMATTING_CONFIG` no script.
  * Remove linhas de grade do Excel.
  * Aplica bordas às células de dados.
  * Ajusta automaticamente a largura das colunas.
* **Modo de Operação (`create` vs `update`):**
  * **`create`**: Gera o relatório `giro_da_praça_ofertas.xlsx` do zero a cada execução.
  * **`update`**: Compara o relatório gerado com uma versão anterior do `giro_da_praça_ofertas.xlsx`. Linhas correspondentes a produtos novos ou com alteração de preço são destacadas com fundo verde e fonte branca no relatório final.

## Comandos de Execução

Para gerar o relatório do zero, substituindo qualquer versão anterior:

```bash
python processador_ofertas.py --mode create
```

ou simplesmente (pois `create` é o padrão):

```bash
python processador_ofertas.py
```

Para atualizar o relatório existente, destacando novos produtos ou alterações de preço:

```bash
python processador_ofertas.py --mode update
```

## Estrutura de Diretórios Esperada

```
.
├── arquivos_xml_entrada/      # Diretório para colocar os arquivos XML de entrada
│   ├── oferta_loja1.xml
│   └── oferta_loja2.xml
├── produtos_cadastrados.xlsx  # Arquivo mestre de cadastro (criado/atualizado pelo script)
├── giro_da_praça_ofertas.xlsx # Relatório final de ofertas (criado/atualizado pelo script)
└── processador_ofertas.py     # Este script
```

## Pré-requisitos

* Python 3.x
* Bibliotecas Python listadas no script (pandas, openpyxl, xmltodict). Para instalar:

    ```bash
    pip install pandas openpyxl xmltodict
    ```

    (Recomenda-se o uso de um ambiente virtual Python)

## Configuração

* **Diretório de Entrada:** Os arquivos XML devem ser colocados em `./arquivos_xml_entrada/`.
* **Nomes de Arquivos de Saída:** Definidos como constantes no script (`PRODUCT_MASTER_FILE_NAME`, `FINAL_OFFERS_REPORT_NAME`).
* **Seções de Exceção para Agrupamento:** A constante `SECOES_EXCECAO_AGRUPAMENTO` no script define quais seções não devem ter seus produtos agrupados pela lógica de "nome base + preço".
* **Formatação de Colunas:** A constante `COLUMNS_FORMATTING_CONFIG` no script permite personalizar a aparência de cada coluna no relatório `giro_da_praça_ofertas.xlsx`.

## Detalhes da Implementação

* **Tratamento de Texto:** Funções para remover acentuação e normalizar texto. Uma função específica (`extract_product_base_name`) usa regex para padronizar nomes de produtos e extrair a base para agrupamento.
* **Processamento de XML:** Utiliza a biblioteca `xmltodict`.
* **Manipulação de Dados:** Forte uso da biblioteca `pandas` para manipulação e agregação de dados.
* **Interação com Excel:**
  * `pandas` para leitura e escrita básica.
  * `openpyxl` para formatação avançada (estilos, cores, bordas, largura de coluna).
* **Tratamento de Erros:** Blocos `try-except` para lidar com arquivos ausentes, formatos inesperados, etc.

## Possíveis Melhorias Futuras

* Extrair configurações (como `SECOES_EXCECAO_AGRUPAMENTO` e `COLUMNS_FORMATTING_CONFIG`) para um arquivo de configuração externo (JSON, YAML).
* Adicionar logging mais detalhado para um arquivo de log.
* Interface gráfica simples para usuários não técnicos.
