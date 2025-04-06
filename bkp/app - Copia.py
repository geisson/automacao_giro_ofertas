import pandas as pd
import os
import glob
import xmltodict
import json

# import xml.etree.ElementTree as ET


#-----------------------------

# FUNÇÕES PARA TRATAR O NOME DOS ARQUIVOS
def remover_acentuacao(texto):
    caracteres_acentuados = ['á', 'é', 'í', 'ó', 'ú', 'à', 'è', 'ì', 'ò', 'ù', 'â', 'ê', 'î', 'ô', 'û', 'ã', 'õ', 'ä', 'ë', 'ï', 'ö', 'ü', 'ç', 'ñ', 'ÿ', 'ý', 'Á', 'É', 'Í', 'Ó', 'Ú', 'À', 'È', 'Ì', 'Ò', 'Ù', 'Â', 'Ê', 'Î', 'Ô', 'Û', 'Ã', 'Õ', 'Ä', 'Ë', 'Ï', 'Ö', 'Ü', 'Ç', 'Ñ', 'Ÿ', 'Ý']
    caracteres_nao_acentuados = ['a', 'e', 'i', 'o', 'u', 'a', 'e', 'i', 'o', 'u', 'a', 'e', 'i', 'o', 'u', 'a', 'o', 'a', 'e', 'i', 'o', 'u', 'c', 'n', 'y', 'y', 'A', 'E', 'I', 'O', 'U', 'A', 'E', 'I', 'O', 'U', 'A', 'E', 'I', 'O', 'U', 'A', 'O', 'A', 'E', 'I', 'O', 'U', 'C', 'N', 'Y', 'Y']
    for letra in caracteres_acentuados:
        index_letra = caracteres_acentuados.index(letra)
        letra_sem_acento = caracteres_nao_acentuados[index_letra]
        texto = texto.replace(letra, letra_sem_acento)
    return texto

def texto_em_letras_minusculas(texto):
    return texto.lower()

def modificar_texto(texto):
    remover_acentos = remover_acentuacao(texto)
    texto_em_minusculo = texto_em_letras_minusculas(remover_acentos)
    return texto_em_minusculo

#-----------------------------

# FUNÇÕES PARA RENOMEAR ARQUIVOS

def renomear_arquivos(arquivos, diretorio):
    for arquivo_antigo in arquivos:
        nome_arquivo_ = os.path.basename(arquivo_antigo)
        modificar_nome = modificar_texto(nome_arquivo_)
        novo_nome = os.path.join(diretorio, modificar_nome)
        os.rename(arquivo_antigo, novo_nome)

#-----------------------------

# # FUNÇÕES UNIR .XML
# def merge_xml_files(diretorio, output_file):
#     # Encontrar todos os arquivos XML que correspondem ao padrão
#     xml_files = glob.glob(diretorio)

#     if not xml_files:
#         print("Nenhum arquivo XML encontrado com o padrão especificado.")
#         return

#     # Criar o elemento raiz para o novo XML
#     merged_root = ET.Element("MergedData")

#     for xml_file in xml_files:
#         try:
#             tree = ET.parse(xml_file)
#             root = tree.getroot()

#             # Adicionar todos os elementos filhos do arquivo atual ao merged_root
#             for child in root:
#                 merged_root.append(child)

#         except ET.ParseError as e:
#             print(f"Erro ao analisar {xml_file}: {e}")
#             continue

#     # Criar a árvore XML com o merged_root
#     merged_tree = ET.ElementTree(merged_root)

#     # Escrever o arquivo de saída
#     merged_tree.write(output_file, encoding='utf-8', xml_declaration=True)
#     print(f"Arquivos XML unidos com sucesso em {output_file}")

#-----------------------------

diretorio_arquivos_brutos = './dados_brutos/'
extensao = '.xml'

arquivos = glob.glob(os.path.join(diretorio_arquivos_brutos, '*{}'.format(extensao)))
# renomear_arquivos(arquivos, diretorio_arquivos_brutos)

# lista_de_arquivos = os.listdir(diretorio)
# arquivo_xml_unido = 'giro_da_praca_ofertas.xml'
# diretorio_salvamento = './dados_corrigidos/'

# merge_xml_files(f'{diretorio}*.xml', arquivo_xml_unido)

#-----------------------------

# def pegar_infos(nome_arquivo):
#     with open(f'./dados_brutos/{nome_arquivo}', 'rb') as arquivo_xml:
#         dic_arquivo = xmltodict.parse(arquivo_xml)

#         try:
#             infos_oferta = dic_arquivo['temporario_846']['temporario_846_row']
#             oferta_nome = infos_oferta['descrpromocao']
#             oferta_inicio = infos_oferta['dtinipromocao']
#             oferta_fim = infos_oferta['dtfimpromocao']
#             oferta_id_produto = infos_oferta['idsubproduto']
#             oferta_produto = infos_oferta['descrresproduto']
#             oferta_preco = infos_oferta['precopromocao']

#             print(oferta_nome, oferta_inicio, oferta_fim, oferta_id_produto, oferta_produto, oferta_preco, sep='\n')
#         except Exception as e:
#             print(e)
#             print(json.dumps(dic_arquivo, indent=4))

#         # # Só imprima se as variáveis foram definidas
#         # if all([oferta_nome, oferta_inicio, oferta_fim, oferta_id_produto, oferta_produto, oferta_preco]):
#         #     print(oferta_nome, oferta_inicio, oferta_fim, oferta_id_produto, oferta_produto, oferta_preco, sep='\n')
#         # else:
#         #     print(f"Não foi possível obter todas as informações do arquivo {nome_arquivo}")

def xml_para_lista_dicionarios(nome_arquivo):
    """Converte um XML em uma lista de dicionários (um para cada produto)."""
    with open(f'./dados_brutos/{nome_arquivo}', 'rb') as arquivo_xml:
        dic_arquivo = xmltodict.parse(arquivo_xml)
        lista_produtos = []

        # Padroniza 'temporario_846_row' para ser sempre uma lista
        if 'temporario_846' in dic_arquivo:
            temporario_846 = dic_arquivo['temporario_846']
            if 'temporario_846_row' in temporario_846:
                produtos = temporario_846['temporario_846_row']
                if isinstance(produtos, dict):  # Se for apenas 1 produto
                    produtos = [produtos]  # Transforma em lista

                # Adiciona cada produto à lista final
                for produto in produtos:
                    lista_produtos.append({
                        "Promoção": produto.get('descrpromocao', ''),
                        "ID Produto": int(produto.get('idsubproduto', '')),
                        "Produto": produto.get('descrresproduto', ''),
                        "Preço Promoção": float(produto.get('precopromocao', ''))
                    })

        return lista_produtos

# Lista todos os arquivos XML na pasta
lista_arquivos = [arq for arq in os.listdir('./dados_brutos/') if arq.endswith('.xml')]

# Lista consolidada de todos os produtos de todos os arquivos
todos_produtos = []

# Processa cada arquivo
for arquivo in lista_arquivos:
    try:
        produtos = xml_para_lista_dicionarios(arquivo)
        todos_produtos.extend(produtos)  # Adiciona à lista consolidada
        print(f"✅ {arquivo}: {len(produtos)} produtos processados.")
    except Exception as e:
        print(f"❌ Erro em {arquivo}: {e}")

# Cria um DataFrame (tabela) com pandas e exporta para Excel
if todos_produtos:
    df = pd.DataFrame(todos_produtos)
    df.to_excel("ofertas_consolidadas.xlsx", index=False)
    print(f"🎉 Excel gerado com {len(df)} produtos!")
else:
    print("Nenhum dado foi processado.")

