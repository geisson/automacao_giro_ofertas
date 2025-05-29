# -*- coding: utf-8 -*-
"""
Script para processamento de arquivos XML de ofertas, refatorado com paradigma funcional.
Dividido em seções bem definidas com funções puras sempre que possível.
Modificado para incluir agrupamento condicional de produtos, formatação de Excel
avançada (contábil, bordas) e ordenação específica de seções com linhas em branco.
V6: Corrigida a lógica de identificação de linhas de espaçamento para não aplicar bordas.
V7: Adicionada funcionalidade para limpar cores e destacar produtos de oferta em verde no 'produtos_cadastrados.xlsx'.
"""

# ------------------------------------------
# DEPENDÊNCIAS
# ------------------------------------------
import pandas as pd
import os
import glob
import xmltodict # Certifique-se de que está instalado: pip install xmltodict
from typing import List, Dict, Any, Optional
import re
import numpy as np
from openpyxl import load_workbook # Adicionado para carregar um workbook existente
from openpyxl.styles import Border, Side, Alignment, Font, PatternFill # PatternFill é para cores de célula
from openpyxl.utils import get_column_letter # Para ajuste de largura de coluna
import traceback # Para melhor depuração de erros

# ------------------------------------------
# CONSTANTES
# ------------------------------------------
INPUT_XML_DIR = './arquivos_xml_entrada/'
XML_EXTENSION = '.xml'
PRODUCT_MASTER_FILE_NAME = 'produtos_cadastrados.xlsx'
FINAL_OFFERS_REPORT_NAME = 'giro_da_praça_ofertas.xlsx'

SECOES_EXCECAO_AGRUPAMENTO = ["#01 MERCEARIA - #01 ALTO GIRO", "#01 MERCEARIA - #02 ALTO GIRO"]

# ------------------------------------------
# FUNÇÕES PARA TRATAMENTO DE TEXTO
# ------------------------------------------

def remover_acentuacao(texto: str) -> str:
    if not isinstance(texto, str): return ""
    mapeamento_acentos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
        'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u', 'ã': 'a', 'õ': 'o', 'ä': 'a', 'ë': 'e', 'ï': 'i',
        'ö': 'o', 'ü': 'u', 'ç': 'c', 'ñ': 'n', 'ÿ': 'y', 'ý': 'y', 'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O',
        'Ú': 'U', 'À': 'A', 'È': 'E', 'Ì': 'I', 'Ò': 'O', 'Ù': 'U', 'Â': 'A', 'Ê': 'E', 'Î': 'I', 'Ô': 'O',
        'Û': 'U', 'Ã': 'A', 'Õ': 'O', 'Ä': 'A', 'Ë': 'E', 'Ï': 'I', 'Ö': 'O', 'Ü': 'U', 'Ç': 'C', 'Ñ': 'N',
        'Ÿ': 'Y', 'Ý': 'Y'
    }
    return ''.join(mapeamento_acentos.get(c, c) for c in texto)

def normalizar_texto(texto: str) -> str:
    if not isinstance(texto, str): return ""
    texto_sem_acentos = remover_acentuacao(texto)
    return texto_sem_acentos.lower()

# ------------------------------------------
# FUNÇÕES PARA MANIPULAÇÃO DE ARQUIVOS
# ------------------------------------------

def listar_arquivos_xml(diretorio: str) -> List[str]:
    return glob.glob(os.path.join(diretorio, f'*{XML_EXTENSION}'))

def renomear_arquivo(arquivo_antigo: str, diretorio: str) -> None:
    nome_arquivo = os.path.basename(arquivo_antigo)
    novo_nome = normalizar_texto(nome_arquivo)
    novo_caminho = os.path.join(diretorio, novo_nome)
    try:
        if arquivo_antigo != novo_caminho:
            os.rename(arquivo_antigo, novo_caminho)
    except FileExistsError:
        print(f"⚠️  Arquivo '{novo_caminho}' já existe. Não foi renomeado '{arquivo_antigo}'.")
    except Exception as e:
        print(f"❌ Erro ao renomear '{arquivo_antigo}' para '{novo_caminho}': {e}")

def renomear_arquivos_em_lote(arquivos: List[str], diretorio: str) -> None:
    for arquivo in arquivos:
        renomear_arquivo(arquivo, diretorio)

# ------------------------------------------
# FUNÇÕES PARA PROCESSAMENTO DE XML
# ------------------------------------------

def parse_produto_xml(produto_xml_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "Promoção_XML": produto_xml_data.get('descrpromocao', ''),
        "ID_Produto_XML": int(produto_xml_data.get('idsubproduto', 0)),
        "Nome_Produto_XML": produto_xml_data.get('descrresproduto', ''),
        "Preco_Promocao_XML": float(produto_xml_data.get('precopromocao', 0.0) if produto_xml_data.get('precopromocao') not in [None, ''] else 0.0)
    }

def processar_arquivo_xml(nome_arquivo_xml: str) -> List[Dict[str, Any]]:
    caminho_arquivo = os.path.join(INPUT_XML_DIR, nome_arquivo_xml)
    try:
        with open(caminho_arquivo, 'rb') as arquivo_xml:
            dados_xml = xmltodict.parse(arquivo_xml)
            if 'temporario_846' not in dados_xml:
                print(f"⚠️ Estrutura 'temporario_846' não encontrada em {nome_arquivo_xml}.")
                return []
            temporario_846 = dados_xml['temporario_846']
            produtos_data_xml = temporario_846.get('temporario_846_row', [])
            if isinstance(produtos_data_xml, dict):
                produtos_data_xml = [produtos_data_xml]
            if not produtos_data_xml:
                return []
            return [parse_produto_xml(p) for p in produtos_data_xml if isinstance(p, dict)]
    except FileNotFoundError:
        print(f"❌ Arquivo XML não encontrado: {caminho_arquivo}")
        return []
    except Exception as e:
        print(f"❌ Erro ao processar XML {nome_arquivo_xml}: {e}")
        traceback.print_exc()
        return []

# ------------------------------------------
# FUNÇÃO PARA CONSOLIDAÇÃO DE DADOS XML
# ------------------------------------------

def consolidar_dados_de_xmls(lista_arquivos_xml: List[str]) -> pd.DataFrame:
    todos_produtos_lista = []
    for arquivo_nome in lista_arquivos_xml:
        produtos_do_arquivo = processar_arquivo_xml(arquivo_nome)
        if produtos_do_arquivo:
            todos_produtos_lista.extend(produtos_do_arquivo)
            print(f"✅ {arquivo_nome}: {len(produtos_do_arquivo)} produtos processados.")
    if not todos_produtos_lista:
        print("⚠️ Nenhum produto encontrado nos arquivos XML.")
        return pd.DataFrame()
    return pd.DataFrame(todos_produtos_lista)

# ------------------------------------------
# FUNÇÕES AUXILIARES PARA INTEGRAÇÃO DE DADOS
# ------------------------------------------

def extract_product_base_name(product_name: str) -> str:
    if not isinstance(product_name, str): return ""
    unidades = [
        "KILOGRAMAS", "KILOGRAMA", "QUILOGRAMAS", "QUILOGRAMA", "LITROS", "LITRO", "UNIDADES", "UNIDADE",
        "PACOTES", "PACOTE", "CAIXAS", "CAIXA", "FARDOS", "FARDO", "GARRAFAS", "GARRAFA", "LATAS", "LATA",
        "POTES", "POTE", "ROLOS", "ROLO", "SACHES", "SACHE", "TUBOS", "TUBO", "VIDROS", "VIDRO", "SACOLAS",
        "SACOLA", "BLISTERS", "BLISTER", "CARTELAS", "CARTELA", "DISPLAYS", "DISPLAY", "GALÕES", "GALÃO",
        "REFILs", "REFIL", "TABLETES", "TABLETE", "PEÇAS", "PEÇA", "FOLHAS", "FOLHA", "FLACONETES",
        "FLACONETE", "BISNAGAS", "BISNAGA", "AMPOLAS", "AMPOLA", "DRAGEAS", "CAPSULAS", "CAPSULA",
        "COMPRIMIDOS", "COMPRIMIDO", "ENVELOPES", "ENVELOPE",
        "KG", "GR", "G", "MG", "L", "ML", "CM", "MM", "M",
        "UN", "UND", "UNID", "PC", "PÇ", "PCT", "CX", "FD", "GF", "LT", "PT", "RL", "SC", "TB", "VD",
        "BL", "CT", "DP", "GL", "RF", "TBL", "FL", "CAPS", "COMP", "ENV"
    ]
    unidades_regex_part = "|".join(map(re.escape, sorted(unidades, key=len, reverse=True)))
    regex_str = r"^(.*?)(\s?)(\d+[\.,]?\d*)(\s*)(" + unidades_regex_part + r")($|\s+.*$)"
    match = re.match(regex_str, product_name, re.IGNORECASE)

    if match:
        nome_antes_da_medida = match.group(1).strip()
        quantidade = match.group(3)
        unidade_texto = match.group(5)
        base_nome = f"{nome_antes_da_medida} {quantidade}{unidade_texto}".strip()
        return base_nome.replace("  ", " ")
    return product_name

def get_section_sort_key(section_name: Any) -> str:
    if not isinstance(section_name, str) or pd.isna(section_name): return "SEM SEÇÃO DEFINIDA"
    if section_name.startswith("#01 MERCEARIA - #") and "ALTO GIRO" in section_name:
        return "#01 MERCEARIA - ALTO GIRO"
    return section_name.split(" - ", 1)[0]

# ------------------------------------------
# FUNÇÕES PARA INTEGRAÇÃO E MANUTENÇÃO DE DADOS
# ------------------------------------------

def atualizar_cadastro_produtos_base(df_ofertas_xml: pd.DataFrame) -> None:
    path_cadastro_base = f'./{PRODUCT_MASTER_FILE_NAME}'
    cols_cadastro_base_ordenadas = ['ID', 'SESSÃO', 'NOME_SISTEMA', 'NOME_CORRIGIDO']

    try:
        df_cadastro_base = pd.read_excel(path_cadastro_base)
        if 'ID' not in df_cadastro_base.columns:
            print(f"⚠️  Arquivo '{PRODUCT_MASTER_FILE_NAME}' não possui coluna 'ID'. Tratando como novo.")
            df_cadastro_base = pd.DataFrame(columns=cols_cadastro_base_ordenadas)
        temp_df = pd.DataFrame(columns=cols_cadastro_base_ordenadas)
        for col in cols_cadastro_base_ordenadas:
            if col in df_cadastro_base.columns:
                temp_df[col] = df_cadastro_base[col]
            else:
                temp_df[col] = np.nan
        df_cadastro_base = temp_df
    except FileNotFoundError:
        print(f"ℹ️  Arquivo '{PRODUCT_MASTER_FILE_NAME}' não encontrado. Será criado.")
        df_cadastro_base = pd.DataFrame(columns=cols_cadastro_base_ordenadas)
    except Exception as e:
        print(f"❌ Erro ao carregar '{PRODUCT_MASTER_FILE_NAME}': {e}. Operação cancelada.")
        return

    novos_produtos_df = pd.DataFrame() # Inicializa para o caso de df_ofertas_xml estar vazio

    if df_ofertas_xml.empty:
        print(f"ℹ️ DataFrame de ofertas XML está vazio. Nenhum produto novo para adicionar ao '{PRODUCT_MASTER_FILE_NAME}'.")
    else:
        if 'ID_Produto_XML' not in df_ofertas_xml.columns or 'Nome_Produto_XML' not in df_ofertas_xml.columns:
            print(f"❌ Colunas 'ID_Produto_XML' ou 'Nome_Produto_XML' ausentes no DataFrame de ofertas. Não é possível atualizar o cadastro.")
            # Mesmo sem novos produtos, precisamos salvar o arquivo base, possivelmente com cores
        else:
            # Garante que a coluna 'ID' em df_cadastro_base seja do tipo que pode ser comparado com int
            if 'ID' in df_cadastro_base.columns:
                df_cadastro_base['ID'] = pd.to_numeric(df_cadastro_base['ID'], errors='coerce')
                ids_existentes_cadastro = set(df_cadastro_base['ID'].dropna().astype(int).unique())
            else:
                ids_existentes_cadastro = set()

            df_ofertas_xml['ID_Produto_XML'] = pd.to_numeric(df_ofertas_xml['ID_Produto_XML'], errors='coerce')
            novos_produtos_df = df_ofertas_xml[
                ~df_ofertas_xml['ID_Produto_XML'].dropna().astype(int).isin(ids_existentes_cadastro)
            ].copy()


            if novos_produtos_df.empty:
                print(f"ℹ️ Nenhum produto novo das ofertas XML para adicionar ao '{PRODUCT_MASTER_FILE_NAME}'.")
            else:
                print(f"ℹ️ {len(novos_produtos_df)} novos produtos encontrados para adicionar.")
                novos_para_cadastro_list = []
                for _, row in novos_produtos_df.iterrows():
                    novos_para_cadastro_list.append({
                        'ID': row['ID_Produto_XML'],
                        'NOME_SISTEMA': row['Nome_Produto_XML'],
                        'SESSÃO': 'SEÇÃO NÃO ESPECIFICADA',
                        'NOME_CORRIGIDO': row['Nome_Produto_XML']
                    })
                df_novos_formatados = pd.DataFrame(novos_para_cadastro_list, columns=cols_cadastro_base_ordenadas)
                df_cadastro_base = pd.concat([df_cadastro_base, df_novos_formatados], ignore_index=True)
                df_cadastro_base.drop_duplicates(subset=['ID'], keep='first', inplace=True)

    try:
        # 1. Preparar e salvar o DataFrame com pandas (isso define a estrutura e dados)
        df_para_salvar = df_cadastro_base.reindex(columns=cols_cadastro_base_ordenadas)
        df_para_salvar = df_para_salvar.sort_values(by=['SESSÃO', 'NOME_SISTEMA', 'ID'])

        # Certificar que a coluna ID é numérica antes de salvar, se ela existir
        if 'ID' in df_para_salvar.columns:
            df_para_salvar['ID'] = pd.to_numeric(df_para_salvar['ID'], errors='coerce')

        df_para_salvar.to_excel(path_cadastro_base, index=False)

        # 2. Reabrir com openpyxl para aplicar formatação de cores
        if not df_para_salvar.empty or os.path.exists(path_cadastro_base): # Prosseguir se o arquivo existe
            # Definir estilos de preenchimento
            green_fill = PatternFill(start_color="45A045", end_color="45A045", fill_type="solid") # Verde mais claro
            no_fill = PatternFill(fill_type=None) # Sem preenchimento

            # Obter IDs dos produtos presentes nos XMLs desta execução
            ids_produtos_oferta_xml = set()
            if not df_ofertas_xml.empty and 'ID_Produto_XML' in df_ofertas_xml.columns:
                ids_produtos_oferta_xml = set(df_ofertas_xml['ID_Produto_XML'].dropna().astype(int).unique())

            produtos_coloridos_info_list = [] # Para listar os produtos coloridos

            wb = load_workbook(path_cadastro_base)
            ws = wb.active

            # Encontrar o índice da coluna 'ID' (1-based para openpyxl)
            id_col_index = None
            nome_corrigido_col_index = None
            nome_sistema_col_index = None

            if ws.max_row > 0: # Se a planilha não estiver completamente vazia
                header_cells = ws[1] # Primeira linha (cabeçalho)
                for i, cell in enumerate(header_cells):
                    if cell.value == 'ID':
                        id_col_index = i + 1
                    elif cell.value == 'NOME_CORRIGIDO':
                        nome_corrigido_col_index = i + 1
                    elif cell.value == 'NOME_SISTEMA':
                        nome_sistema_col_index = i + 1

            if id_col_index is None and ws.max_row > 0:
                print(f"⚠️  Aviso: Coluna 'ID' não encontrada no cabeçalho de '{PRODUCT_MASTER_FILE_NAME}'. Não será possível aplicar cores.")
            elif ws.max_row <= 1 and not ids_produtos_oferta_xml : # Arquivo só com cabeçalho ou vazio, e sem produtos XML
                 print(f"ℹ️  Arquivo '{PRODUCT_MASTER_FILE_NAME}' está vazio ou contém apenas cabeçalho e não há produtos XML para colorir.")
            elif ws.max_row > 1 and id_col_index is not None: # Prossegue apenas se há dados e coluna ID foi encontrada
                # Iterar pelas linhas de dados (a partir da segunda linha)
                for row_num in range(2, ws.max_row + 1):
                    # Primeiro, limpar a cor de todas as células da linha
                    for col_num in range(1, ws.max_column + 1):
                        ws.cell(row=row_num, column=col_num).fill = no_fill

                    # Verificar se o ID desta linha está nos produtos da oferta XML
                    id_cell_value = ws.cell(row=row_num, column=id_col_index).value
                    if id_cell_value is not None:
                        try:
                            current_id = int(float(id_cell_value)) # Tenta converter para float primeiro, depois int
                            if current_id in ids_produtos_oferta_xml:
                                # Colorir todas as células da linha de verde
                                for col_num in range(1, ws.max_column + 1):
                                    ws.cell(row=row_num, column=col_num).fill = green_fill

                                # Coletar informação do produto colorido
                                nome_produto = "NOME NÃO ENCONTRADO"
                                if nome_corrigido_col_index and ws.cell(row=row_num, column=nome_corrigido_col_index).value:
                                    nome_produto = ws.cell(row=row_num, column=nome_corrigido_col_index).value
                                elif nome_sistema_col_index and ws.cell(row=row_num, column=nome_sistema_col_index).value:
                                     nome_produto = ws.cell(row=row_num, column=nome_sistema_col_index).value

                                produtos_coloridos_info_list.append({'ID': current_id, 'Nome': nome_produto})
                        except ValueError:
                            # Se não puder converter para int diretamente, não é um ID válido para comparação.
                            # Isso pode acontecer se a célula ID tiver texto ou estiver vazia após coerção.
                            # print(f"⚠️  Aviso: Valor não numérico ou inválido para ID na linha {row_num} de '{PRODUCT_MASTER_FILE_NAME}': '{id_cell_value}'. Pulando coloração.")
                            pass # Silenciosamente ignora linhas onde ID não é numérico
                        except TypeError:
                            # print(f"⚠️  Aviso: Tipo inesperado para ID na linha {row_num} de '{PRODUCT_MASTER_FILE_NAME}': '{id_cell_value}'. Pulando coloração.")
                            pass # Silenciosamente ignora


            wb.save(path_cadastro_base)

            if not novos_produtos_df.empty:
                print(f"✅ '{PRODUCT_MASTER_FILE_NAME}' atualizado com {len(novos_produtos_df)} novos produtos e formatação de cores aplicada.")
            else:
                print(f"✅ '{PRODUCT_MASTER_FILE_NAME}' salvo com formatação de cores aplicada.")

            if produtos_coloridos_info_list:
                print(f"ℹ️ Produtos das ofertas XML (coloridos em verde em '{PRODUCT_MASTER_FILE_NAME}'):")
                # Remover duplicados da lista de informação antes de imprimir, caso um produto seja processado múltiplas vezes
                unique_produtos_coloridos = [dict(t) for t in {tuple(d.items()) for d in produtos_coloridos_info_list}]
                for prod_info in sorted(unique_produtos_coloridos, key=lambda x: x['ID']):
                    print(f"  - ID: {prod_info['ID']}, Nome: {str(prod_info['Nome'])}") # Garantir que Nome seja string
            elif ids_produtos_oferta_xml: # Havia produtos no XML, mas não foram encontrados no arquivo base ou ID não encontrado
                print(f"ℹ️ Havia {len(ids_produtos_oferta_xml)} produtos nas ofertas XML, mas nenhum correspondente foi encontrado ou pode ser colorido em '{PRODUCT_MASTER_FILE_NAME}'.")
                # print(f"   Verifique se os IDs dos produtos XML (ex: {list(ids_produtos_oferta_xml)[:5]}...) existem na coluna 'ID' do arquivo Excel e são numéricos.")
            else:
                print(f"ℹ️ Nenhum produto das ofertas XML para colorir em '{PRODUCT_MASTER_FILE_NAME}'.")


    except Exception as e:
        print(f"❌ Erro ao salvar ou formatar '{PRODUCT_MASTER_FILE_NAME}': {e}")
        traceback.print_exc()

def gerar_relatorio_ofertas_finais(df_ofertas_xml: pd.DataFrame) -> None:
    path_cadastro_base = f'./{PRODUCT_MASTER_FILE_NAME}'
    path_relatorio_final = f'./{FINAL_OFFERS_REPORT_NAME}'

    try:
        df_cadastro_base = pd.read_excel(path_cadastro_base)
        colunas_cadastro_esperadas = ['ID', 'SESSÃO', 'NOME_SISTEMA', 'NOME_CORRIGIDO']
        if not all(col in df_cadastro_base.columns for col in colunas_cadastro_esperadas):
            missing_cols = [col for col in colunas_cadastro_esperadas if col not in df_cadastro_base.columns]
            print(f"❌ Arquivo '{PRODUCT_MASTER_FILE_NAME}' não contém todas as colunas esperadas. Faltando: {missing_cols}. Não é possível gerar relatório.")
            return
    except FileNotFoundError:
        print(f"❌ Arquivo de cadastro '{PRODUCT_MASTER_FILE_NAME}' não encontrado. Execute a atualização do cadastro primeiro."); return
    except Exception as e:
        print(f"❌ Erro ao carregar '{PRODUCT_MASTER_FILE_NAME}': {e}"); return

    if df_ofertas_xml.empty:
        print(f"⚠️ DataFrame de ofertas XML está vazio. Nada a processar para '{FINAL_OFFERS_REPORT_NAME}'."); return

    required_xml_cols = ['ID_Produto_XML', 'Promoção_XML', 'Preco_Promocao_XML', 'Nome_Produto_XML']
    if not all(col in df_ofertas_xml.columns for col in required_xml_cols):
        print(f"❌ DataFrame de ofertas XML não contém todas as colunas requeridas: {required_xml_cols}.")
        return

    df_ofertas_xml_copy = df_ofertas_xml[required_xml_cols].copy()
    df_cadastro_base_copy = df_cadastro_base[['ID', 'SESSÃO', 'NOME_CORRIGIDO']].copy()

    # Garantir que as colunas de merge sejam do mesmo tipo (int)
    df_ofertas_xml_copy['ID_Produto_XML'] = pd.to_numeric(df_ofertas_xml_copy['ID_Produto_XML'], errors='coerce').astype('Int64')
    df_cadastro_base_copy['ID'] = pd.to_numeric(df_cadastro_base_copy['ID'], errors='coerce').astype('Int64')


    df_merged = pd.merge(
        df_ofertas_xml_copy,
        df_cadastro_base_copy,
        left_on='ID_Produto_XML',
        right_on='ID',
        how='left'
    )

    df_merged['NOME_CORRIGIDO'] = df_merged['NOME_CORRIGIDO'].fillna(df_merged['Nome_Produto_XML'])
    df_merged['SESSÃO'] = df_merged['SESSÃO'].fillna('SEÇÃO NÃO ESPECIFICADA')
    df_merged['Promoção_XML'] = df_merged['Promoção_XML'].fillna('')

    df_merged['Produto_Base_Para_Agrupamento'] = df_merged['NOME_CORRIGIDO'].apply(extract_product_base_name)
    df_merged['Excecao_Agrupamento'] = df_merged['SESSÃO'].isin(SECOES_EXCECAO_AGRUPAMENTO)
    df_merged['Grupo_Agrupamento_ID'] = df_merged['Produto_Base_Para_Agrupamento'].astype(str) + '_' + df_merged['Preco_Promocao_XML'].astype(str)

    counts = df_merged[~df_merged['Excecao_Agrupamento']].groupby('Grupo_Agrupamento_ID')['ID_Produto_XML'].transform('size')
    df_merged['Contagem_No_Grupo'] = counts
    df_merged['Contagem_No_Grupo'] = df_merged['Contagem_No_Grupo'].fillna(1)

    df_merged['Nome_Produto_Final_Para_Relatorio'] = np.where(
        (~df_merged['Excecao_Agrupamento'] & (df_merged['Contagem_No_Grupo'] > 1)),
        df_merged['Produto_Base_Para_Agrupamento'],
        df_merged['NOME_CORRIGIDO']
    )

    df_aggregated = df_merged.groupby(
        ['Nome_Produto_Final_Para_Relatorio', 'Preco_Promocao_XML'], as_index=False
    ).agg(
        Descricao_Promocao_Agg=pd.NamedAgg(column='Promoção_XML', aggfunc='first'),
        ID_Produto_Agg=pd.NamedAgg(column='ID_Produto_XML', aggfunc='first'),
        Sessao_Agg=pd.NamedAgg(column='SESSÃO', aggfunc='first')
    )

    df_relatorio_final = df_aggregated.rename(columns={
        'Nome_Produto_Final_Para_Relatorio': 'PRODUTO',
        'Preco_Promocao_XML': 'PROMOÇÃO',
        'Descricao_Promocao_Agg': 'NOME_PROMOÇÃO',
        'ID_Produto_Agg': 'ID',
        'Sessao_Agg': 'SESSÃO'
    })

    colunas_finais_excel_ordenadas = ['NOME_PROMOÇÃO', 'SESSÃO', 'ID', 'PRODUTO', 'PROMOÇÃO']
    df_relatorio_final = df_relatorio_final[colunas_finais_excel_ordenadas]

    df_relatorio_final['Chave_Grupo_Secao_Ordenacao'] = df_relatorio_final['SESSÃO'].apply(get_section_sort_key)

    df_ordenado = df_relatorio_final.sort_values(
        by=['Chave_Grupo_Secao_Ordenacao', 'SESSÃO', 'PRODUTO'], ascending=[True, True, True]
    ).reset_index(drop=True)

    lista_linhas_com_espacos = []
    ultima_chave_grupo_vista = None
    colunas_df_ordenado = df_ordenado.columns.tolist()

    for _, row_data in df_ordenado.iterrows():
        chave_grupo_atual = row_data['Chave_Grupo_Secao_Ordenacao']
        if ultima_chave_grupo_vista is not None and chave_grupo_atual != ultima_chave_grupo_vista:
            lista_linhas_com_espacos.append({col: np.nan for col in colunas_df_ordenado})
        lista_linhas_com_espacos.append(row_data.to_dict())
        ultima_chave_grupo_vista = chave_grupo_atual

    if not lista_linhas_com_espacos:
        print(f"⚠️ Nenhum dado para gerar o relatório '{FINAL_OFFERS_REPORT_NAME}'."); return

    df_com_espacos = pd.DataFrame(lista_linhas_com_espacos)
    df_output_excel = df_com_espacos.drop(columns=['Chave_Grupo_Secao_Ordenacao'])

    try:
        with pd.ExcelWriter(path_relatorio_final, engine='openpyxl') as writer:
            df_output_excel.to_excel(writer, index=False, sheet_name='Ofertas Finais')
            ws = writer.sheets['Ofertas Finais']

            ws.sheet_view.showGridLines = False

            thin_side = Side(style='thin')
            border_style = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
            formato_contabil = 'R$ #,##0.00'

            col_idx_valor_promo_excel = -1
            if 'PROMOÇÃO' in df_output_excel.columns:
                # Encontra o índice da coluna 'PROMOÇÃO' (base 1 para openpyxl)
                col_idx_valor_promo_excel = df_output_excel.columns.get_loc('PROMOÇÃO') + 1
            else:
                print(f"⚠️ Aviso: A coluna 'PROMOÇÃO' não foi encontrada no output. Não formatando como contábil.")


            for row_idx_excel in range(1, ws.max_row + 1):
                is_spacer_row = all(
                    (ws.cell(row=row_idx_excel, column=c_idx_excel).value is None or
                     str(ws.cell(row=row_idx_excel, column=c_idx_excel).value).strip() == '' or
                     pd.isna(ws.cell(row=row_idx_excel, column=c_idx_excel).value)
                    )
                    for c_idx_excel in range(1, ws.max_column + 1)
                )


                if is_spacer_row:
                    continue

                for col_idx_excel in range(1, ws.max_column + 1):
                    cell = ws.cell(row=row_idx_excel, column=col_idx_excel)
                    cell.border = border_style

                    if row_idx_excel > 1 and col_idx_excel == col_idx_valor_promo_excel and cell.value is not None:
                        if isinstance(cell.value, (int, float)):
                            if cell.value == 0.0 and str(cell.value) == "0.0": # Tratar 0.0 especificamente
                                cell.value = 0.00
                            cell.number_format = formato_contabil
                        else:
                            try:
                                val_str = str(cell.value).upper().replace("R$", "").replace(".", "").replace(",", ".").strip()
                                if val_str: # Evitar erro com string vazia
                                    numeric_value = float(val_str)
                                    cell.value = numeric_value
                                    cell.number_format = formato_contabil
                            except ValueError:
                                # print(f"⚠️ Não foi possível converter '{cell.value}' para número na L{row_idx_excel}C{col_idx_excel}. Mantido como texto.")
                                pass # Silenciosamente mantém como texto

            for col_idx_openpyxl in range(1, ws.max_column + 1):
                column_letter = get_column_letter(col_idx_openpyxl)
                max_len = 0
                for cell_tuple in ws.iter_cols(min_col=col_idx_openpyxl, max_col=col_idx_openpyxl, min_row=1, max_row=ws.max_row):
                    cell = cell_tuple[0]
                    if cell.value is not None:
                        is_header = cell.row == 1
                        is_formatted_promo_col = (col_idx_openpyxl == col_idx_valor_promo_excel and
                                                  not is_header and
                                                  cell.number_format == formato_contabil and
                                                  isinstance(cell.value, (int, float)))

                        if is_formatted_promo_col:
                            text_val = f"R$ {cell.value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            current_len = len(text_val)
                        else:
                            current_len = len(str(cell.value))

                        max_len = max(max_len, current_len)

                adjusted_width = min(max_len + 3, 50) # Ajusta a largura, max 50
                ws.column_dimensions[column_letter].width = adjusted_width if adjusted_width > 5 else 10 # Largura mínima de 10, a menos que seja muito pequeno


        num_ofertas_reais = len(df_ordenado.dropna(subset=['PRODUTO'], how='all'))
        print(f"✅ Relatório '{FINAL_OFFERS_REPORT_NAME}' criado com {num_ofertas_reais} ofertas na raiz do projeto.")

    except Exception as e:
        print(f"❌ Erro ao salvar/formatar Excel '{FINAL_OFFERS_REPORT_NAME}': {e}")
        traceback.print_exc()

# ------------------------------------------
# FUNÇÃO PRINCIPAL
# ------------------------------------------

def main() -> None:
    print("🚀 Iniciando processamento de ofertas...")

    if not os.path.isdir(INPUT_XML_DIR):
        print(f"❌ ERRO: Diretório de entrada '{INPUT_XML_DIR}' não encontrado. Crie-o e adicione os arquivos XML.")
        print("🏁 Processamento abortado.")
        return

    arquivos_xml_originais = listar_arquivos_xml(INPUT_XML_DIR)
    if not arquivos_xml_originais:
        print(f"ℹ️ Nenhum arquivo XML encontrado em '{INPUT_XML_DIR}'.")
    else:
        print(f"🔄 Normalizando nomes de {len(arquivos_xml_originais)} arquivos XML...")
        renomear_arquivos_em_lote(arquivos_xml_originais, INPUT_XML_DIR)

    arquivos_xml_para_processar = [
        f for f in os.listdir(INPUT_XML_DIR)
        if f.endswith(XML_EXTENSION) and os.path.isfile(os.path.join(INPUT_XML_DIR, f))
    ]
    if not arquivos_xml_para_processar:
        print(f"ℹ️ Nenhum arquivo XML para processar em '{INPUT_XML_DIR}' após normalização.")
        # Continua para permitir que atualizar_cadastro_produtos_base seja chamado para limpar cores, se o arquivo existir
        # print("🏁 Processamento concluído (sem dados processados).")
        # return # Removido para permitir a limpeza de cores mesmo sem XMLs

    print(f"📄 Consolidando dados de {len(arquivos_xml_para_processar)} arquivos XML...")
    df_ofertas_consolidadas_xml = consolidar_dados_de_xmls(arquivos_xml_para_processar)

    # Não retorna mais se df_ofertas_consolidadas_xml estiver vazio,
    # pois queremos que atualizar_cadastro_produtos_base seja chamado para limpar cores e possivelmente listar produtos antigos.
    if df_ofertas_consolidadas_xml.empty:
        print("ℹ️ Nenhum dado de produto foi consolidado dos arquivos XML nesta execução.")
        # print("🏁 Processamento concluído (sem dados para gerar relatórios).") # Movido para depois
        # return

    print(f"💾 Atualizando o arquivo de cadastro de produtos: './{PRODUCT_MASTER_FILE_NAME}'...")
    atualizar_cadastro_produtos_base(df_ofertas_consolidadas_xml) # df_ofertas_xml pode estar vazio aqui

    if df_ofertas_consolidadas_xml.empty: # Verifica novamente aqui antes de gerar relatório final
        print("🏁 Processamento concluído (sem dados XML para gerar relatório de ofertas).")
        return

    print(f"📊 Gerando o relatório final de ofertas: './{FINAL_OFFERS_REPORT_NAME}'...")
    gerar_relatorio_ofertas_finais(df_ofertas_consolidadas_xml)

    print("🏁 Processamento concluído.")

if __name__ == "__main__":
    main()