# -*- coding: utf-8 -*-
"""
Script para processamento de arquivos XML de ofertas, refatorado com paradigma funcional.
Dividido em seções bem definidas com funções puras sempre que possível.
"""

# ------------------------------------------
# DEPENDÊNCIAS
# ------------------------------------------
import pandas as pd
import os
import glob
import xmltodict
from typing import List, Dict, Any

# ------------------------------------------
# CONSTANTES
# ------------------------------------------
INPUT_DIR = './dados_brutos/'
OUTPUT_DIR = './'
XML_EXTENSION = '.xml'
CORRECTED_FILE = 'dados_produtos_corrigidos.xlsx'
CONSOLIDATED_FILE = 'ofertas_consolidadas.xlsx'
CORRECTED_OFFERS_FILE = 'ofertas_corrigidas.xlsx'

# ------------------------------------------
# FUNÇÕES PARA TRATAMENTO DE TEXTO
# ------------------------------------------

def remover_acentuacao(texto: str) -> str:
    """
    Remove acentuação de um texto.

    Args:
        texto: String com possíveis caracteres acentuados

    Returns:
        String sem caracteres acentuados
    """
    mapeamento_acentos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
        'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u',
        'ã': 'a', 'õ': 'o', 'ä': 'a', 'ë': 'e', 'ï': 'i',
        'ö': 'o', 'ü': 'u', 'ç': 'c', 'ñ': 'n', 'ÿ': 'y',
        'ý': 'y', 'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O',
        'Ú': 'U', 'À': 'A', 'È': 'E', 'Ì': 'I', 'Ò': 'O',
        'Ù': 'U', 'Â': 'A', 'Ê': 'E', 'Î': 'I', 'Ô': 'O',
        'Û': 'U', 'Ã': 'A', 'Õ': 'O', 'Ä': 'A', 'Ë': 'E',
        'Ï': 'I', 'Ö': 'O', 'Ü': 'U', 'Ç': 'C', 'Ñ': 'N',
        'Ÿ': 'Y', 'Ý': 'Y'
    }

    return ''.join(mapeamento_acentos.get(c, c) for c in texto)

def normalizar_texto(texto: str) -> str:
    """
    Normaliza um texto removendo acentos e convertendo para minúsculas.

    Args:
        texto: String a ser normalizada

    Returns:
        String normalizada
    """
    texto_sem_acentos = remover_acentuacao(texto)
    return texto_sem_acentos.lower()

# ------------------------------------------
# FUNÇÕES PARA MANIPULAÇÃO DE ARQUIVOS
# ------------------------------------------

def listar_arquivos_xml(diretorio: str) -> List[str]:
    """
    Lista todos os arquivos XML em um diretório.

    Args:
        diretorio: Caminho do diretório a ser pesquisado

    Returns:
        Lista com caminhos completos dos arquivos XML
    """
    return glob.glob(os.path.join(diretorio, f'*{XML_EXTENSION}'))

def renomear_arquivo(arquivo_antigo: str, diretorio: str) -> None:
    """
    Renomeia um arquivo normalizando seu nome.

    Args:
        arquivo_antigo: Caminho completo do arquivo a ser renomeado
        diretorio: Diretório onde o arquivo está localizado
    """
    nome_arquivo = os.path.basename(arquivo_antigo)
    novo_nome = normalizar_texto(nome_arquivo)
    novo_caminho = os.path.join(diretorio, novo_nome)
    os.rename(arquivo_antigo, novo_caminho)

def renomear_arquivos_em_lote(arquivos: List[str], diretorio: str) -> None:
    """
    Renomeia vários arquivos em lote.

    Args:
        arquivos: Lista de caminhos completos dos arquivos
        diretorio: Diretório onde os arquivos estão localizados
    """
    for arquivo in arquivos:
        renomear_arquivo(arquivo, diretorio)

# ------------------------------------------
# FUNÇÕES PARA PROCESSAMENTO DE XML
# ------------------------------------------

def parse_produto(produto: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai e formata os dados relevantes de um produto.

    Args:
        produto: Dicionário com dados brutos do produto

    Returns:
        Dicionário com dados formatados do produto
    """
    return {
        "Promoção": produto.get('descrpromocao', ''),
        "ID Produto": int(produto.get('idsubproduto', 0)),
        "Produto": produto.get('descrresproduto', ''),
        "Preço Promoção": float(produto.get('precopromocao', 0.0))
    }

def processar_xml(nome_arquivo: str) -> List[Dict[str, Any]]:
    """
    Processa um arquivo XML e retorna uma lista de produtos.

    Args:
        nome_arquivo: Nome do arquivo XML a ser processado

    Returns:
        Lista de dicionários contendo os produtos
    """
    caminho_arquivo = os.path.join(INPUT_DIR, nome_arquivo)

    with open(caminho_arquivo, 'rb') as arquivo_xml:
        dados_xml = xmltodict.parse(arquivo_xml)

        if 'temporario_846' not in dados_xml:
            return []

        temporario_846 = dados_xml['temporario_846']
        produtos = temporario_846.get('temporario_846_row', [])

        # Garante que produtos seja sempre uma lista
        if isinstance(produtos, dict):
            produtos = [produtos]

        return [parse_produto(p) for p in produtos]

# ------------------------------------------
# FUNÇÕES PARA CONSOLIDAÇÃO DE DADOS
# ------------------------------------------

def consolidar_produtos(lista_arquivos: List[str]) -> List[Dict[str, Any]]:
    """
    Processa múltiplos arquivos XML e consolida todos os produtos.

    Args:
        lista_arquivos: Lista de nomes de arquivos XML

    Returns:
        Lista consolidada de todos os produtos
    """
    todos_produtos = []

    for arquivo in lista_arquivos:
        try:
            produtos = processar_xml(arquivo)
            todos_produtos.extend(produtos)
            print(f"✅ {arquivo}: {len(produtos)} produtos processados.")
        except Exception as e:
            print(f"❌ Erro em {arquivo}: {e}")

    return todos_produtos

def gerar_planilha_ofertas(produtos: List[Dict[str, Any]]) -> None:
    """
    Gera uma planilha Excel com os produtos consolidados.

    Args:
        produtos: Lista de produtos a serem exportados
    """
    if not produtos:
        print("Nenhum dado foi processado.")
        return

    df = pd.DataFrame(produtos)
    df.to_excel(CONSOLIDATED_FILE, index=False)
    print(f"🎉 Excel gerado com {len(df)} produtos!")

# ------------------------------------------
# FUNÇÕES PARA INTEGRAÇÃO DE DADOS
# ------------------------------------------

def adicionar_novos_produtos() -> None:
    """
    Adiciona novos produtos ao arquivo corrigido, evitando duplicatas.
    """
    df_corrigidos = pd.read_excel(CORRECTED_FILE)
    df_ofertas = pd.read_excel(CONSOLIDATED_FILE)

    # Filtra apenas produtos que não existem no arquivo corrigido
    ids_existentes = df_corrigidos['ID Produto'].unique()
    novos_produtos = df_ofertas[~df_ofertas['ID Produto'].isin(ids_existentes)]

    # Seleciona colunas relevantes
    colunas_desejadas = ['ID Produto', 'Produto', 'Preço Promoção']
    novos_produtos_filtrados = novos_produtos[colunas_desejadas]

    # Concatena os DataFrames
    df_final = pd.concat([df_corrigidos, novos_produtos_filtrados], ignore_index=True)

    # Salva o resultado
    df_final.to_excel(CORRECTED_FILE, index=False)
    print("Registros adicionados com sucesso!")

def gerar_ofertas_corrigidas() -> None:
    """
    Gera um arquivo com as ofertas corrigidas, combinando dados das duas fontes.
    Mantém o preço promocional original do arquivo consolidado e renomeia as colunas conforme especificado.
    """
    # Carrega os dados
    df_corrigidos = pd.read_excel(CORRECTED_FILE)
    df_ofertas = pd.read_excel(CONSOLIDATED_FILE)

    # Realiza o merge das tabelas mantendo o preço do arquivo consolidado
    df_final = df_ofertas[['ID Produto', 'Promoção', 'Preço Promoção']].merge(
        df_corrigidos[['ID Produto', 'Seção', 'Produto Corrigido']],
        on='ID Produto',
        how='left'
    )

    # Seleciona e renomeia as colunas conforme especificado
    df_final = df_final[[
        'Promoção',
        'Seção',
        'ID Produto',
        'Produto Corrigido',
        'Preço Promoção'
    ]].rename(columns={
        'ID Produto': 'ID',
        'Produto Corrigido': 'PRODUTO',
        'Preço Promoção': 'PROMOÇÃO'
    })

    # Salva o resultado
    df_final.to_excel(CORRECTED_OFFERS_FILE, index=False)
    print(f"✅ Tabela '{CORRECTED_OFFERS_FILE}' criada com sucesso!")

# ------------------------------------------
# FUNÇÃO PRINCIPAL
# ------------------------------------------

def main() -> None:
    """Fluxo principal de execução do script."""
    # 1. Normalizar nomes dos arquivos
    arquivos_xml = listar_arquivos_xml(INPUT_DIR)
    renomear_arquivos_em_lote(arquivos_xml, INPUT_DIR)

    # 2. Processar arquivos e consolidar produtos
    arquivos_renomeados = [f for f in os.listdir(INPUT_DIR) if f.endswith(XML_EXTENSION)]
    todos_produtos = consolidar_produtos(arquivos_renomeados)

    # 3. Gerar planilha consolidada
    gerar_planilha_ofertas(todos_produtos)

    # 4. Integrar com dados corrigidos
    adicionar_novos_produtos()
    gerar_ofertas_corrigidas()

if __name__ == "__main__":
    main()