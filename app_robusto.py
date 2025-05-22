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
import re # Nova importação
import numpy as np # Nova importação

# ------------------------------------------
# CONSTANTES
# ------------------------------------------
INPUT_DIR = './dados_brutos/'
OUTPUT_DIR = './' # OUTPUT_DIR não é usado diretamente para os arquivos de saída, mas mantido
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
    try:
        if arquivo_antigo != novo_caminho: # Só renomeia se o nome for diferente
            os.rename(arquivo_antigo, novo_caminho)
    except FileExistsError:
        print(f"⚠️  Arquivo '{novo_caminho}' já existe. Não foi renomeado '{arquivo_antigo}'.")
    except Exception as e:
        print(f"❌ Erro ao renomear '{arquivo_antigo}' para '{novo_caminho}': {e}")


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
        "Promoção": produto.get('descrpromocao', ''), # Descrição da promoção (ex: LEVE 3 PAGUE 2)
        "ID Produto": int(produto.get('idsubproduto', 0)),
        "Produto": produto.get('descrresproduto', ''),
        "Preço Promoção": float(produto.get('precopromocao', 0.0)) # Valor da promoção
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

    try:
        with open(caminho_arquivo, 'rb') as arquivo_xml: # 'rb' para robustez com encodings
            dados_xml = xmltodict.parse(arquivo_xml)

            if 'temporario_846' not in dados_xml:
                print(f"⚠️ Estrutura 'temporario_846' não encontrada em {nome_arquivo}.")
                return []

            temporario_846 = dados_xml['temporario_846']
            # 'temporario_846_row' pode ser uma lista de produtos ou um único produto como dict
            produtos_data = temporario_846.get('temporario_846_row', [])

            # Garante que produtos_data seja sempre uma lista para processamento uniforme
            if isinstance(produtos_data, dict):
                produtos_data = [produtos_data]

            if not produtos_data: # Lista vazia de produtos
                return []

            return [parse_produto(p) for p in produtos_data if isinstance(p, dict)]
    except FileNotFoundError:
        print(f"❌ Arquivo XML não encontrado: {caminho_arquivo}")
        return []
    except Exception as e: # Captura outras exceções do xmltodict ou processamento
        print(f"❌ Erro ao processar XML {nome_arquivo}: {e}")
        return []


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
        produtos = processar_xml(arquivo) # processar_xml já lida com erros internos
        if produtos: # Adiciona apenas se houver produtos processados
            todos_produtos.extend(produtos)
            print(f"✅ {arquivo}: {len(produtos)} produtos processados.")
        # A função processar_xml já imprime erros específicos ou avisos.

    return todos_produtos

def gerar_planilha_ofertas(produtos: List[Dict[str, Any]]) -> None:
    """
    Gera uma planilha Excel com os produtos consolidados.

    Args:
        produtos: Lista de produtos a serem exportados
    """
    if not produtos:
        print(f"⚠️ Nenhum dado de produto foi processado para gerar '{CONSOLIDATED_FILE}'.")
        return

    try:
        df = pd.DataFrame(produtos)
        df.to_excel(CONSOLIDATED_FILE, index=False)
        print(f"🎉 Excel '{CONSOLIDATED_FILE}' gerado com {len(df)} produtos!")
    except Exception as e:
        print(f"❌ Erro ao gerar planilha '{CONSOLIDATED_FILE}': {e}")


# ------------------------------------------
# FUNÇÕES AUXILIARES PARA INTEGRAÇÃO DE DADOS
# ------------------------------------------

def extract_product_base_name(product_name: str) -> str:
    """
    Extrai o nome base de um produto, mantendo a quantidade e unidade principal,
    removendo variações de sabor/tipo subsequentes.
    Ex: "AMACIANTE CONCENTRADO 500ML AZUL" -> "AMACIANTE CONCENTRADO 500ML"
    """
    if not isinstance(product_name, str):
        return ""

    unidades = [
        "KILOGRAMAS", "KILOGRAMA", "QUILOGRAMAS", "QUILOGRAMA", "LITROS", "LITRO",
        "UNIDADES", "UNIDADE", "PACOTES", "PACOTE", "CAIXAS", "CAIXA", "FARDOS", "FARDO",
        "GARRAFAS", "GARRAFA", "LATAS", "LATA", "POTES", "POTE", "ROLOS", "ROLO",
        "SACHES", "SACHE", "TUBOS", "TUBO", "VIDROS", "VIDRO", "SACOLAS", "SACOLA",
        "BLISTERS", "BLISTER", "CARTELAS", "CARTELA", "DISPLAYS", "DISPLAY",
        "GALÕES", "GALÃO", "REFILs", "REFIL", "TABLETES", "TABLETE",
        "PEÇAS", "PEÇA", "FOLHAS", "FOLHA", "FLACONETES", "FLACONETE",
        "BISNAGAS", "BISNAGA", "AMPOLAS", "AMPOLA", "DRAGEAS", "CAPSULAS", "CAPSULA",
        "COMPRIMIDOS", "COMPRIMIDO", "ENVELOPES", "ENVELOPE",
        "KG", "GR", "G", "MG", "L", "ML", "CM", "MM", "M", "UN", "UND", "UNID", "PC", "PÇ", "PCT",
        "CX", "FD", "GF", "LT", "PT", "RL", "SC", "TB", "VD", "BL", "CT", "DP", "GL",
        "RF", "TBL", "FL", "CAPS", "COMP", "ENV"
    ]
    # Ordena unidades da mais longa para a mais curta para evitar matches parciais (ex: "L" antes de "LT")
    # Escapa caracteres regex nas unidades
    unidades_regex_part = "|".join(map(re.escape, sorted(unidades, key=len, reverse=True)))

    # Regex: (nome_produto_nao_guloso)(\s_opcional)(\d_com_ou_sem_decimal)(\s_opcional)(unidade_da_lista)(\b_word_boundary)(resto_opcional)
    regex_str = r"^(.*?)(\s?)(\d+[\.,]?\d*)(\s*)(" + unidades_regex_part + r")\b.*$"
    match = re.match(regex_str, product_name, re.IGNORECASE)

    if match:
        nome_antes = match.group(1).strip()
        quantidade = match.group(3)
        espaco_unidade = match.group(4) # Espaço entre quantidade e unidade, se houver
        unidade_texto = match.group(5)

        # Recria a base do nome: "Nome QuantidadeUnidade"
        # Garante um único espaço entre nome_antes e quantidade se nome_antes não estiver vazio.
        if nome_antes:
            base_nome = f"{nome_antes} {quantidade}{espaco_unidade}{unidade_texto}"
        else: # Caso o nome comece diretamente com a quantidade/unidade
            base_nome = f"{quantidade}{espaco_unidade}{unidade_texto}"

        return base_nome.strip().replace("  ", " ") # Limpa espaços extras
    return product_name # Retorna nome original se não houver match


def get_section_group(section_name: Any) -> str:
    """
    Define o grupo da seção para fins de ordenação e inserção de linhas em branco.
    Subseções de '#01 MERCEARIA - ... ALTO GIRO' são agrupadas.
    """
    if not isinstance(section_name, str) or pd.isna(section_name):
        return "SEM SEÇÃO DEFINIDA" # Valor padrão para NaN ou tipos inesperados

    # Regra para agrupar todas as subseções de "ALTO GIRO" de "#01 MERCEARIA"
    # Ex: "#01 MERCEARIA - #01 ALTO GIRO", "#01 MERCEARIA - #02 ALTO GIRO", etc.
    # serão agrupadas sob o identificador comum "#01 MERCEARIA - ALTO GIRO".
    if section_name.startswith("#01 MERCEARIA - #") and "ALTO GIRO" in section_name:
        return "#01 MERCEARIA - ALTO GIRO"

    # Regra geral para outras seções: pega a parte antes do primeiro " - "
    # Se não houver " - ", usa o nome da seção inteira como grupo.
    return section_name.split(" - ", 1)[0]

# ------------------------------------------
# FUNÇÕES PARA INTEGRAÇÃO DE DADOS
# ------------------------------------------

def adicionar_novos_produtos() -> None:
    """
    Adiciona novos produtos do arquivo consolidado ao arquivo corrigido, evitando duplicatas de ID.
    """
    try:
        df_corrigidos = pd.read_excel(CORRECTED_FILE)
    except FileNotFoundError:
        print(f"⚠️  Arquivo '{CORRECTED_FILE}' não encontrado. Será criado um novo se houver ofertas consolidadas.")
        # Define um DataFrame vazio com as colunas esperadas para permitir a concatenação
        df_corrigidos = pd.DataFrame(columns=['ID Produto', 'Produto', 'Preço Promoção', 'Seção', 'Produto Corrigido']) # Ajuste as colunas conforme necessário
    except Exception as e:
        print(f"❌ Erro ao carregar '{CORRECTED_FILE}': {e}")
        return

    try:
        df_ofertas = pd.read_excel(CONSOLIDATED_FILE)
    except FileNotFoundError:
        print(f"ℹ️ Arquivo '{CONSOLIDATED_FILE}' não encontrado. Nenhum novo produto para adicionar.")
        return
    except Exception as e:
        print(f"❌ Erro ao carregar '{CONSOLIDATED_FILE}': {e}")
        return

    if df_ofertas.empty:
        print(f"ℹ️ Arquivo '{CONSOLIDATED_FILE}' está vazio. Nenhum novo produto para adicionar.")
        return

    # Garante que 'ID Produto' exista em ambos DataFrames
    if 'ID Produto' not in df_ofertas.columns:
        print(f"❌ Coluna 'ID Produto' não encontrada em '{CONSOLIDATED_FILE}'. Não é possível adicionar novos produtos.")
        return
    if 'ID Produto' not in df_corrigidos.columns and not df_corrigidos.empty:
         print(f"❌ Coluna 'ID Produto' não encontrada em '{CORRECTED_FILE}'. Não é possível verificar duplicatas.")
         # Decide se continua ou para. Por ora, continuará e poderá adicionar duplicatas se df_corrigidos não for vazio.
         # Se df_corrigidos foi criado vazio acima, 'ID Produto' já estará lá.

    ids_existentes = set(df_corrigidos['ID Produto'].unique()) if 'ID Produto' in df_corrigidos.columns else set()
    novos_produtos = df_ofertas[~df_ofertas['ID Produto'].isin(ids_existentes)]

    if novos_produtos.empty:
        print(f"ℹ️ Nenhum produto novo (baseado em 'ID Produto') encontrado em '{CONSOLIDATED_FILE}' para adicionar a '{CORRECTED_FILE}'.")
        return

    # Seleciona colunas de novos_produtos e prepara para concatenação
    # Mantém apenas as colunas que existem em df_corrigidos ou são essenciais de novos_produtos
    colunas_para_novos = ['ID Produto', 'Produto', 'Preço Promoção'] # Essenciais de df_ofertas
    novos_produtos_filtrados = novos_produtos[colunas_para_novos].copy()

    # Adiciona colunas que existem em df_corrigidos mas não em novos_produtos_filtrados (ex: 'Seção', 'Produto Corrigido')
    # preenchendo com valores padrão ou NaN
    for col in df_corrigidos.columns:
        if col not in novos_produtos_filtrados.columns:
            if col == 'Seção':
                novos_produtos_filtrados[col] = 'SEÇÃO NÃO ESPECIFICADA'
            elif col == 'Produto Corrigido':
                # Usa o nome original do produto se 'Produto Corrigido' não for fornecido
                novos_produtos_filtrados[col] = novos_produtos_filtrados['Produto'] if 'Produto' in novos_produtos_filtrados else 'PRODUTO NÃO ESPECIFICADO'
            else:
                novos_produtos_filtrados[col] = np.nan

    # Garante que novos_produtos_filtrados tenha as mesmas colunas que df_corrigidos para concatenação limpa
    novos_produtos_alinhados = novos_produtos_filtrados.reindex(columns=df_corrigidos.columns, fill_value=np.nan)


    df_final = pd.concat([df_corrigidos, novos_produtos_alinhados], ignore_index=True)
    df_final.drop_duplicates(subset=['ID Produto'], keep='first', inplace=True) # Segurança extra

    try:
        df_final.to_excel(CORRECTED_FILE, index=False)
        print(f"✅ '{CORRECTED_FILE}' atualizado/criado com {len(novos_produtos_alinhados)} novos produtos adicionados.")
    except Exception as e:
        print(f"❌ Erro ao salvar '{CORRECTED_FILE}' após adicionar novos produtos: {e}")


def gerar_ofertas_corrigidas() -> None:
    """
    Gera um arquivo com as ofertas corrigidas, combinando dados das duas fontes,
    aplicando agrupamento de produtos, ordenação específica e inserindo linhas em branco entre seções.
    """
    try:
        df_corrigidos = pd.read_excel(CORRECTED_FILE)
    except FileNotFoundError:
        print(f"❌ Arquivo '{CORRECTED_FILE}' não encontrado. Execute a etapa de adição de produtos ou crie-o manualmente.")
        return
    except Exception as e:
        print(f"❌ Erro ao carregar '{CORRECTED_FILE}': {e}")
        return

    try:
        df_ofertas = pd.read_excel(CONSOLIDATED_FILE)
    except FileNotFoundError:
        print(f"❌ Arquivo '{CONSOLIDATED_FILE}' não encontrado. Execute a etapa de consolidação de XMLs.")
        return
    except Exception as e:
        print(f"❌ Erro ao carregar '{CONSOLIDATED_FILE}': {e}")
        return

    if df_ofertas.empty:
        print(f"⚠️ Arquivo '{CONSOLIDATED_FILE}' está vazio. Não é possível gerar '{CORRECTED_OFFERS_FILE}'.")
        return
    if df_corrigidos.empty:
        print(f"⚠️ Arquivo '{CORRECTED_FILE}' está vazio. As colunas 'Seção' e 'Produto Corrigido' podem ficar ausentes ou com padrões.")
        # Se df_corrigidos estiver vazio, o merge 'left' em df_ofertas ainda funciona, mas 'Seção' e 'Produto Corrigido' serão NaN

    # Merge: traz 'Seção' e 'Produto Corrigido' de df_corrigidos para df_ofertas
    # Mantém todas as ofertas de df_ofertas
    df_merged = df_ofertas[['ID Produto', 'Promoção', 'Preço Promoção']].merge(
        df_corrigidos[['ID Produto', 'Seção', 'Produto Corrigido']],
        on='ID Produto',
        how='left' # Mantém todas as linhas de df_ofertas
    )

    # Preenche NaNs que surgem do merge se um ID Produto de df_ofertas não está em df_corrigidos
    # Ou se 'Produto Corrigido'/'Seção' já eram NaN em df_corrigidos
    df_merged['Produto Corrigido'] = df_merged['Produto Corrigido'].fillna(df_merged['ID Produto'].astype(str) + '_NOME_ORIGINAL_OU_FALTANTE')
    df_merged['Seção'] = df_merged['Seção'].fillna('SEÇÃO NÃO ESPECIFICADA')
    # 'Promoção' (descrição) e 'Preço Promoção' (valor) vêm de df_ofertas e devem estar presentes.
    df_merged['Promoção_Descricao'] = df_merged['Promoção'].fillna('') # Assegura que é string

    # 1. Agrupamento de Produtos com base no nome truncado e preço
    df_merged['Produto_Base'] = df_merged['Produto Corrigido'].apply(extract_product_base_name)

    # Agrupa por 'Produto_Base' e 'Preço Promoção'.
    # 'Preço Promoção' (valor numérico) será uma das chaves do groupby e, portanto, uma coluna em df_aggregated.
    df_aggregated = df_merged.groupby(['Produto_Base', 'Preço Promoção'], as_index=False).agg(
        # Pega a primeira ocorrência das outras colunas dentro de cada grupo
        Promoção_Original_Desc=pd.NamedAgg(column='Promoção_Descricao', aggfunc='first'),
        ID_Produto_Agg=pd.NamedAgg(column='ID Produto', aggfunc='first'),
        Seção_Agg=pd.NamedAgg(column='Seção', aggfunc='first')
    ).reset_index(drop=True) # Garante um índice limpo

    # Renomeia colunas para o formato final desejado
    df_final_agrupado = df_aggregated.rename(columns={
        'Produto_Base': 'PRODUTO',                 # Nome do produto (base)
        'Preço Promoção': 'PROMOÇÃO_VALOR',       # Valor numérico da promoção (temporário)
        'Promoção_Original_Desc': 'Promoção',     # Descrição textual da promoção
        'ID_Produto_Agg': 'ID',
        'Seção_Agg': 'Seção'
    })

    # Reordena e renomeia a coluna de valor da promoção para 'PROMOÇÃO'
    # Resultando em duas colunas chamadas 'PROMOÇÃO' (uma textual, uma numérica)
    colunas_saida_ordem = ['Promoção', 'Seção', 'ID', 'PRODUTO', 'PROMOÇÃO_VALOR']
    df_final_formatado = df_final_agrupado[colunas_saida_ordem].rename(columns={'PROMOÇÃO_VALOR': 'PROMOÇÃO'})

    # 2. Criar a coluna "Seção_Agrupada" para ordenação e linhas em branco
    df_final_formatado['Seção_Agrupada'] = df_final_formatado['Seção'].apply(get_section_group)

    # 3. Ordenação: Seção_Agrupada, Seção (original), PRODUTO
    df_ordenado = df_final_formatado.sort_values(
        by=['Seção_Agrupada', 'Seção', 'PRODUTO'],
        ascending=[True, True, True]
    ).reset_index(drop=True)

    # 4. Inserir Linhas em Branco entre diferentes 'Seção_Agrupada'
    lista_linhas_com_espacos = []
    ultima_secao_agrupada_vista = None
    colunas_para_linha_em_branco = df_ordenado.columns # Inclui 'Seção_Agrupada' temporariamente

    for index, row_data in df_ordenado.iterrows():
        secao_agrupada_atual = row_data['Seção_Agrupada']
        if ultima_secao_agrupada_vista is not None and secao_agrupada_atual != ultima_secao_agrupada_vista:
            # Adicionar linha em branco (dicionário de NaNs para todas as colunas)
            linha_em_branco = {col: np.nan for col in colunas_para_linha_em_branco}
            lista_linhas_com_espacos.append(linha_em_branco)

        lista_linhas_com_espacos.append(row_data.to_dict())
        ultima_secao_agrupada_vista = secao_agrupada_atual

    if not lista_linhas_com_espacos:
        print(f"⚠️ Nenhum dado para gravar em '{CORRECTED_OFFERS_FILE}' após processamento e formatação.")
        return

    df_com_linhas_em_branco = pd.DataFrame(lista_linhas_com_espacos)

    # Remover a coluna auxiliar 'Seção_Agrupada' antes de salvar
    # E garantir que as colunas de saída estejam na ordem correta final, caso o drop afete
    df_output = df_com_linhas_em_branco.drop(columns=['Seção_Agrupada'])

    colunas_finais_excel = ['Promoção', 'Seção', 'ID', 'PRODUTO', 'PROMOÇÃO'] # Ordem final desejada
    # Assegura que apenas colunas existentes sejam selecionadas e na ordem correta
    df_output = df_output[[col for col in colunas_finais_excel if col in df_output.columns]]

    try:
        df_output.to_excel(CORRECTED_OFFERS_FILE, index=False, sheet_name='Ofertas Corrigidas')
        print(f"✅ Tabela '{CORRECTED_OFFERS_FILE}' criada com sucesso com {len(df_ordenado)} ofertas e nova formatação!")
    except Exception as e:
        print(f"❌ Erro ao salvar o arquivo Excel '{CORRECTED_OFFERS_FILE}': {e}")

# ------------------------------------------
# FUNÇÃO PRINCIPAL
# ------------------------------------------

def main() -> None:
    """Fluxo principal de execução do script."""
    # 0. Criar diretórios se não existirem
    os.makedirs(INPUT_DIR, exist_ok=True)
    # OUTPUT_DIR é onde os arquivos de saída são salvos (raiz './' por padrão), não precisa de os.makedirs se for './'

    # 1. Normalizar nomes dos arquivos XML de entrada
    arquivos_xml_originais = listar_arquivos_xml(INPUT_DIR)
    if not arquivos_xml_originais:
        print(f"ℹ️ Nenhum arquivo XML encontrado em '{INPUT_DIR}'. Verifique o diretório.")
    else:
        print(f"Normalizando nomes de {len(arquivos_xml_originais)} arquivos XML...")
        renomear_arquivos_em_lote(arquivos_xml_originais, INPUT_DIR)

    # 2. Processar arquivos XML e consolidar produtos
    # Lista arquivos novamente, pois podem ter sido renomeados
    arquivos_xml_para_processar = [
        f for f in os.listdir(INPUT_DIR)
        if f.endswith(XML_EXTENSION) and os.path.isfile(os.path.join(INPUT_DIR, f))
    ]

    if not arquivos_xml_para_processar:
        print(f"ℹ️ Nenhum arquivo XML para processar em '{INPUT_DIR}' (após renomeação ou nenhum encontrado inicialmente).")
        # As funções subsequentes são escritas para lidar com a ausência de arquivos de entrada.

    todos_produtos = consolidar_produtos(arquivos_xml_para_processar)

    # 3. Gerar planilha consolidada de todas as ofertas lidas
    # Esta função já verifica se 'todos_produtos' está vazio.
    gerar_planilha_ofertas(todos_produtos)

    # 4. Integrar com dados corrigidos (dados_produtos_corrigidos.xlsx)
    # Adiciona novos produtos de 'ofertas_consolidadas.xlsx' para 'dados_produtos_corrigidos.xlsx'
    adicionar_novos_produtos()

    # Gera o arquivo final 'ofertas_corrigidas.xlsx' com a formatação solicitada
    gerar_ofertas_corrigidas()

    print("🏁 Processamento concluído.")

if __name__ == "__main__":
    main()