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

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# AQUI É ONDE TUDO É FEITO!
# NADA AQUI DEVE SER DELETADO

# diretorio_arquivos_brutos = './dados_brutos/'
# extensao = '.xml'

# arquivos = glob.glob(os.path.join(diretorio_arquivos_brutos, '*{}'.format(extensao)))
# renomear_arquivos(arquivos, diretorio_arquivos_brutos)



# # Lista todos os arquivos XML na pasta
# lista_arquivos = [arq for arq in os.listdir('./dados_brutos/') if arq.endswith('.xml')]

# # Lista consolidada de todos os produtos de todos os arquivos
# todos_produtos = []

# # Processa cada arquivo
# for arquivo in lista_arquivos:
#     try:
#         produtos = xml_para_lista_dicionarios(arquivo)
#         todos_produtos.extend(produtos)  # Adiciona à lista consolidada
#         print(f"✅ {arquivo}: {len(produtos)} produtos processados.")
#     except Exception as e:
#         print(f"❌ Erro em {arquivo}: {e}")

# # Cria um DataFrame (tabela) com pandas e exporta para Excel
# if todos_produtos:
#     df = pd.DataFrame(todos_produtos)
#     df.to_excel("ofertas_consolidadas.xlsx", index=False)
#     print(f"🎉 Excel gerado com {len(df)} produtos!")
# else:
#     print("Nenhum dado foi processado.")


#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------

# # MESCLAR PLANILHAS

# tabela_nomes_produtos_corrigidos = pd.read_excel('./banco_dados/nomes_produtos_corrigidos.xlsx')
# tabela_ofertas_consolidadas = pd.read_excel('ofertas_consolidadas.xlsx')



# # 1. Carregar as tabelas
# df_corrigidos = pd.read_excel('dados_produtos_corrigidos.xlsx')
# df_ofertas = pd.read_excel('ofertas_consolidadas.xlsx')

# # 2. Filtrar apenas IDs que não existem na tabela corrigidos
# ids_existentes = df_corrigidos['ID Produto'].unique()  # Pega todos os IDs únicos da tabela original
# novos_produtos = df_ofertas[~df_ofertas['ID Produto'].isin(ids_existentes)]  # Filtra apenas os que não existem

# # 3. Selecionar apenas as colunas desejadas para adicionar (opcional, se quiser todas, pode pular)
# colunas_desejadas = ['ID Produto', 'Produto', 'Preço Promoção']
# novos_produtos_filtrados = novos_produtos[colunas_desejadas]

# # 4. Concatenar (adicionar) os novos registros na tabela original
# df_final = pd.concat([df_corrigidos, novos_produtos_filtrados], ignore_index=True)

# # 5. Salvar de volta no arquivo original (ou em outro, se preferir)
# df_final.to_excel('dados_produtos_corrigidos.xlsx', index=False)

# print("Registros adicionados com sucesso!")


#------------------------


# Carregar os dados
df_corrigidos = pd.read_excel('dados_produtos_corrigidos.xlsx')
df_ofertas = pd.read_excel('ofertas_consolidadas.xlsx')

# Realizar o merge (junção) das tabelas
df_final = df_ofertas.merge(
    df_corrigidos[['ID Produto', 'Seção', 'Produto Corrigido', 'Preço Promoção']],
    on='ID Produto',
    how='left'
)

# Selecionar e renomear as colunas conforme especificado
df_final = df_final[['Promoção', 'Seção', 'ID Produto', 'Produto Corrigido', 'Preço Promoção_y']]
df_final = df_final.rename(columns={'Preço Promoção_y': 'Preço Promoção'})

# Salvar o resultado
df_final.to_excel('ofertas_corrigidas.xlsx', index=False)

print("Tabela 'ofertas_corrigidas.xls' criada com sucesso!")