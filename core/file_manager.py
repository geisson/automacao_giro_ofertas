import os
import shutil
import logging
from pathlib import Path
from typing import List, Callable, Union # Iterator removido pois não usado
from functools import partial # partial removido pois não usado
from datetime import datetime, timedelta # timedelta ainda pode ser útil para testes de criação de arquivos, mas não para a lógica de limpeza

# CleaningConfig agora só tem confirm_before_deletion
from config import AppConfig, PathsConfig, CleaningConfig, GeneralConfig

# --- Funções de Operações de Arquivo/Diretório (sem alteração) ---
def create_directory(path: Path, dry_run: bool = False) -> bool:
    if dry_run: logging.info(f"[DRY RUN] Criaria o diretório: {path.resolve()}"); return True
    try: path.mkdir(parents=True, exist_ok=True); logging.debug(f"Dir criado: {path.resolve()}"); return True
    except OSError as e: logging.error(f"Erro criar dir {path.resolve()}: {e}"); return False

def _log_operation(op_name: str, src: Union[Path, str], dst: Union[Path, str] | None = None, dry_run: bool = False) -> None:
    prefix = "[DRY RUN] " if dry_run else ""; msg_dst = f" para '{dst}'" if dst else ""
    logging.info(f"{prefix}{op_name} '{src}'{msg_dst}") # Simplificado

def copy_file(source_path: Path, destination_path: Path, dry_run: bool = False) -> bool:
    _log_operation("Copiaria arq", source_path, destination_path, dry_run)
    if dry_run:
        if not source_path.is_file(): logging.warning(f"[DRY RUN] Origem não arq: {source_path}"); return False
        return True
    if not source_path.is_file(): logging.error(f"Origem não arq: {source_path.resolve()}"); return False
    if not create_directory(destination_path.parent): logging.error(f"Não criar dir destino: {destination_path.parent.resolve()}"); return False
    try: shutil.copy2(source_path, destination_path); logging.debug(f"Copiado: '{source_path}' para '{destination_path}'"); return True
    except Exception as e: logging.error(f"Erro copiar '{source_path}': {e}", exc_info=True); return False

def move_file(source_path: Path, destination_path: Path, dry_run: bool = False) -> bool:
    _log_operation("Moveria arq", source_path, destination_path, dry_run)
    if dry_run:
        if not source_path.is_file(): logging.warning(f"[DRY RUN] Origem não arq: {source_path}"); return False
        return True
    if not source_path.is_file(): logging.error(f"Origem não arq: {source_path.resolve()}"); return False
    if not create_directory(destination_path.parent): logging.error(f"Não criar dir destino: {destination_path.parent.resolve()}"); return False
    try: shutil.move(str(source_path), str(destination_path)); logging.debug(f"Movido: '{source_path}' para '{destination_path}'"); return True
    except Exception as e: logging.error(f"Erro mover '{source_path}': {e}", exc_info=True); return False

def delete_file(file_path: Path, dry_run: bool = False) -> bool:
    _log_operation("Deletaria arq", file_path, dry_run=dry_run)
    if dry_run:
        if not file_path.exists(): logging.info(f"[DRY RUN] Arq não encontrado (OK): {file_path.resolve()}")
        elif not file_path.is_file(): logging.warning(f"[DRY RUN] Não é arq: {file_path.resolve()}"); return False
        return True
    try:
        if file_path.is_file(): file_path.unlink(); logging.debug(f"Arq deletado: {file_path.resolve()}")
        elif file_path.exists(): logging.warning(f"Tentativa deletar '{file_path.resolve()}' (não arq)."); return False
        else: logging.info(f"Arq não encontrado (ignorado): {file_path.resolve()}")
        return True
    except OSError as e: logging.error(f"Erro deletar arq {file_path.resolve()}: {e}"); return False

def delete_directory_recursively(dir_path: Path, dry_run: bool = False) -> bool:
    _log_operation("Deletaria dir recursivamente", dir_path, dry_run=dry_run)
    if dry_run:
        if not dir_path.exists(): logging.info(f"[DRY RUN] Dir não encontrado (OK): {dir_path.resolve()}")
        elif not dir_path.is_dir(): logging.warning(f"[DRY RUN] Não é dir: {dir_path.resolve()}"); return False
        return True
    try:
        if dir_path.is_dir(): shutil.rmtree(dir_path); logging.debug(f"Dir deletado: {dir_path.resolve()}")
        elif dir_path.exists(): logging.warning(f"Tentativa deletar '{dir_path.resolve()}' (não dir)."); return False
        else: logging.info(f"Dir não encontrado (ignorado): {dir_path.resolve()}")
        return True
    except OSError as e: logging.error(f"Erro deletar dir {dir_path.resolve()}: {e}"); return False

def list_files_in_directory(directory: Path, pattern: str = "*", filter_func: Callable[[Path], bool] | None = None) -> List[Path]:
    if not directory.is_dir(): logging.debug(f"Dir não encontrado: {directory.resolve()}"); return []
    try:
        base_files = list(directory.glob(pattern)); final_files: List[Path] = []
        for f_path in base_files:
            if f_path.is_file():
                if filter_func is None or filter_func(f_path): final_files.append(f_path)
        return final_files
    except Exception as e: logging.error(f"Erro listar arqs em '{directory.resolve()}': {e}", exc_info=True); return []

# --- Funções de Limpeza (Lógica Simplificada) ---
def _confirm_deletion(item_type: str, item_path: Path, config: AppConfig) -> bool:
    if config.cleaning.confirm_before_deletion:
        print("-" * 30)
        try:
            response = input(f"⚠️  CONFIRMAR DELEÇÃO: Deletar {item_type} '{item_path.resolve()}'? (s/n): ").strip().lower()
            if response in ['s', 'sim']: return True
            if response in ['n', 'nao', 'não']: logging.info(f"Deleção de {item_type} '{item_path.resolve()}' cancelada."); return False
            logging.warning("Resposta inválida. Assumindo 'não'."); return False
        except (EOFError, KeyboardInterrupt): logging.warning("Confirmação interrompida. Assumindo 'não'."); return False
        finally: print("-" * 30)
    return True

def _delete_all_items_in_path(
    base_path: Path,
    item_type_name: str, # Para logs
    config: AppConfig,
    dry_run: bool = False,
    delete_func: Callable[[Path, bool], bool] = delete_file,
    is_item_a_directory: bool = False # Se true, lista subdiretórios; senão, arquivos
) -> int:
    """Deleta TODOS os itens (arquivos ou subdiretórios) em base_path."""
    if not base_path.is_dir():
        logging.info(f"Diretório base para limpeza de {item_type_name} não encontrado: {base_path.resolve()}")
        return 0

    items_deleted_count = 0
    logging.info(f"Iniciando limpeza TOTAL de {item_type_name} em '{base_path.resolve()}'.")

    items_to_check: List[Path] = []
    if is_item_a_directory:
        try: items_to_check = [item for item in base_path.iterdir() if item.is_dir()]
        except OSError as e: logging.error(f"Erro ao listar subdirs em {base_path}: {e}"); return 0
    else:
        items_to_check = list_files_in_directory(base_path, pattern="*")

    if not items_to_check:
        logging.info(f"Nenhum {item_type_name} encontrado em {base_path.resolve()} para limpar.")
        return 0

    for item_path in items_to_check:
        logging.info(f"Candidato para deleção ({item_type_name}): '{item_path.name}'")
        if not dry_run and not _confirm_deletion(item_type_name, item_path, config):
            continue
        if delete_func(item_path, dry_run):
            if not dry_run: logging.info(f"DELETADO: {item_type_name} '{item_path.name}'")
            items_deleted_count += 1

    logging.info(f"Limpeza TOTAL de {item_type_name} concluída. {items_deleted_count} itens {'seriam afetados' if dry_run else 'afetados'}.")
    return items_deleted_count

def _list_all_processed_files_in_dropbox(config: AppConfig) -> List[Path]:
    # ... (sem alteração) ...
    all_files: List[Path] = []
    dropbox_offers_root = config.paths.dropbox_base_path / config.paths.dropbox_main_offers_folder_name
    if not dropbox_offers_root.is_dir(): logging.warning(f"Raiz Dropbox não encontrada: {dropbox_offers_root}"); return []
    for strat_folder in dropbox_offers_root.iterdir():
        if strat_folder.is_dir() and strat_folder.name in config.naming_and_organization.dropbox_strategies:
            for fmt_folder in strat_folder.iterdir():
                if fmt_folder.is_dir() and fmt_folder.name in [config.naming_and_organization.format_folder_tv,
                                                              config.naming_and_organization.format_folder_feed,
                                                              config.naming_and_organization.format_folder_story]:
                    all_files.extend(list_files_in_directory(fmt_folder, "*"))
    return all_files

def _clean_dropbox_files_by_prefix(prefix: str, item_type_display_name: str, config: AppConfig, dry_run: bool) -> int:
    """Deleta TODOS os arquivos no Dropbox que começam com o prefixo."""
    logging.info(f"Limpando TODOS os '{item_type_display_name}' PROCESSADOS no Dropbox (Dry run: {dry_run}).")
    all_dropbox_files = _list_all_processed_files_in_dropbox(config)
    files_to_delete = [f for f in all_dropbox_files if f.name.lower().startswith(prefix.lower() + "_")]

    items_deleted_count = 0
    if not files_to_delete:
        logging.info(f"Nenhum arquivo '{item_type_display_name}' com prefixo '{prefix}_' encontrado no Dropbox para limpar.")
        return 0

    logging.info(f"Encontrados {len(files_to_delete)} arquivos '{item_type_display_name}' para deleção no Dropbox.")
    for file_path in files_to_delete:
        logging.info(f"Candidato para deleção ({item_type_display_name} Dropbox): '{file_path.name}'")
        if not dry_run and not _confirm_deletion(item_type_display_name + " Dropbox", file_path, config):
            continue
        if delete_file(file_path, dry_run):
            if not dry_run: logging.info(f"DELETADO: {item_type_display_name} '{file_path.name}' do Dropbox.")
            items_deleted_count +=1

    logging.info(f"Limpeza de {item_type_display_name} no Dropbox concluída. {items_deleted_count} itens {'seriam afetados' if dry_run else 'afetados'}.")
    return items_deleted_count

# Funções específicas de limpeza do Dropbox (usam _clean_dropbox_files_by_prefix)
def clean_dropbox_processed_diarias(config: AppConfig, dry_run: bool = False) -> int:
    return _clean_dropbox_files_by_prefix(config.naming_and_organization.base_type_diaria, "ofertas diárias", config, dry_run)

def clean_dropbox_processed_multidia(config: AppConfig, dry_run: bool = False) -> int:
    return _clean_dropbox_files_by_prefix(config.naming_and_organization.base_type_multidia, "ofertas multi-dia", config, dry_run)

def clean_dropbox_processed_fixos(config: AppConfig, dry_run: bool = False) -> int:
    return _clean_dropbox_files_by_prefix(config.naming_and_organization.base_type_fixo, "elementos fixos", config, dry_run)

# Funções de limpeza de arquivamento local (agora deletam tudo na pasta do tipo)
def clean_archived_diarias_local(config: AppConfig, dry_run: bool = False) -> int:
    path = config.paths.downloads_root_path / config.paths.arquivos_ofertas_root_folder_name / "DIARIAS"
    return _delete_all_items_in_path(path, "arquivamento local de diárias (todas as datas)", config, dry_run, delete_directory_recursively, True)

def clean_archived_multidia_local(config: AppConfig, dry_run: bool = False) -> int:
    path = config.paths.downloads_root_path / config.paths.arquivos_ofertas_root_folder_name / "MULTI_DIA"
    return _delete_all_items_in_path(path, "arquivamento local de multi-dia (todas as datas)", config, dry_run, delete_directory_recursively, True)

def clean_archived_fixos_local(config: AppConfig, dry_run: bool = False) -> int:
    path = config.paths.downloads_root_path / config.paths.arquivos_ofertas_root_folder_name / "FIXOS"
    return _delete_all_items_in_path(path, "arquivamento local de fixos (todas as datas)", config, dry_run, delete_directory_recursively, True)

def clean_all_generated_videos(config: AppConfig, dry_run: bool = False) -> int:
    """Deleta TODOS os vídeos gerados."""
    path = config.paths.downloads_root_path / config.paths.videos_ofertas_output_folder_name
    return _delete_all_items_in_path(path, "todos os vídeos gerados", config, dry_run, delete_file, False)

# --- Funções de Limpeza Combinadas (chamadas pelo main.py) ---
def clean_diarias_comprehensive(config: AppConfig, dry_run: bool = False) -> int:
    logging.info(f"Limpeza COMPLETA DIÁRIAS (tudo local e tudo Dropbox). Dry run: {dry_run}")
    deleted_count = clean_archived_diarias_local(config, dry_run) # Deleta todas as pastas de data
    deleted_count += clean_dropbox_processed_diarias(config, dry_run) # Deleta todos os arquivos "diaria_"
    # Se "limpar diarias" deve limpar vídeos, adicione aqui:
    deleted_count += clean_all_generated_videos(config, dry_run)
    logging.info(f"Limpeza COMPLETA DIÁRIAS (+vídeos) finalizada. Total: {deleted_count}")
    return deleted_count

def clean_multidia_comprehensive(config: AppConfig, dry_run: bool = False) -> int:
    logging.info(f"Limpeza COMPLETA MULTI-DIA (tudo local e tudo Dropbox). Dry run: {dry_run}")
    deleted_count = clean_archived_multidia_local(config, dry_run)
    deleted_count += clean_dropbox_processed_multidia(config, dry_run)
    # Poderia limpar vídeos aqui também se fizesse sentido para multi-dia
    logging.info(f"Limpeza COMPLETA MULTI-DIA finalizada. Total: {deleted_count}")
    return deleted_count

def clean_fixos_comprehensive(config: AppConfig, dry_run: bool = False) -> int:
    logging.info(f"Limpeza COMPLETA FIXOS (tudo local e tudo Dropbox). Dry run: {dry_run}")
    deleted_count = clean_archived_fixos_local(config, dry_run)
    deleted_count += clean_dropbox_processed_fixos(config, dry_run)
    # Poderia limpar vídeos aqui também se fizesse sentido para fixos
    logging.info(f"Limpeza COMPLETA FIXOS finalizada. Total: {deleted_count}")
    return deleted_count

def clean_all_tracked_items(config: AppConfig, dry_run: bool = False) -> int:
    """Limpa TUDO: todos os arquivados locais, todos os processados no Dropbox, todos os vídeos."""
    logging.info(f"Limpeza GERAL de todos os itens (Dry run: {dry_run})...")
    total_deleted = 0
    # Limpar arquivados locais (todas as datas para cada tipo)
    total_deleted += clean_archived_diarias_local(config, dry_run)
    total_deleted += clean_archived_multidia_local(config, dry_run)
    total_deleted += clean_archived_fixos_local(config, dry_run)
    # Limpar processados no Dropbox (todos os arquivos de cada tipo)
    total_deleted += clean_dropbox_processed_diarias(config, dry_run)
    total_deleted += clean_dropbox_processed_multidia(config, dry_run)
    total_deleted += clean_dropbox_processed_fixos(config, dry_run)
    # Limpar todos os vídeos gerados
    total_deleted += clean_all_generated_videos(config, dry_run)
    logging.info(f"Limpeza GERAL finalizada. Total: {total_deleted} {'seriam afetados' if dry_run else 'afetados'}.")
    return total_deleted

# Bloco de teste
if __name__ == "__main__":
    import sys
    from dataclasses import replace
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path: sys.path.insert(0, str(project_root))
    from config import load_app_config, CONFIG_FILE_PATH

    log_format = "%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s"
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]: root_logger.removeHandler(handler)
    logging.basicConfig(level=logging.DEBUG, format=log_format, stream=sys.stdout)

    logging.info("Testes de limpeza (nova lógica) em core/file_manager.py...")
    test_cleanup_root_dir = project_root / "temp_cleanup_tests_v4" # Novo dir
    if test_cleanup_root_dir.exists(): shutil.rmtree(test_cleanup_root_dir)
    test_cleanup_root_dir.mkdir(parents=True, exist_ok=True)

    try: original_config = load_app_config(CONFIG_FILE_PATH)
    except Exception as e: logging.error(f"Falha ao carregar config: {e}"); sys.exit(1)

    mock_paths = PathsConfig(
        downloads_root_path = test_cleanup_root_dir,
        dropbox_base_path = test_cleanup_root_dir / "Dropbox",
        dropbox_main_offers_folder_name="00_ofertas_dropbox_test",
        ofertas_multi_dia_folder_name="OFERTAS_MULTI_DIA",
        ofertas_bebidas_folder_name="OFERTAS_BEBIDAS",
        elementos_fixos_folder_name="ELEMENTOS_FIXOS",
        arquivos_ofertas_root_folder_name="ARQUIVOS_OFERTAS_LOCAIS",
        videos_ofertas_output_folder_name="VIDEOS_OFERTAS_LOCAIS")

    mock_cleaning = CleaningConfig(confirm_before_deletion=False) # Sem max_days_*

    mock_general = GeneralConfig(log_level="DEBUG", archive_date_format=original_config.general.archive_date_format)
    mock_config: AppConfig = replace(original_config, paths=mock_paths, cleaning=mock_cleaning, general=mock_general)

    archive_base = mock_config.paths.downloads_root_path / mock_config.paths.arquivos_ofertas_root_folder_name
    videos_base = mock_config.paths.downloads_root_path / mock_config.paths.videos_ofertas_output_folder_name
    dropbox_base_test = mock_config.paths.dropbox_base_path / mock_config.paths.dropbox_main_offers_folder_name
    date_fmt = mock_config.general.archive_date_format.replace("%%", "%")

    # --- Setup da estrutura de teste ---
    # Arquivos Diários Locais (duas pastas de data)
    diarias_local_path = archive_base / "DIARIAS"; diarias_local_path.mkdir(parents=True, exist_ok=True)
    (diarias_local_path / "2024-01-01").mkdir(); (diarias_local_path / "2024-01-01" / "file1.txt").touch()
    (diarias_local_path / "2024-01-02").mkdir(); (diarias_local_path / "2024-01-02" / "file2.txt").touch()

    # Arquivos Diários Dropbox
    db_strategy_path = dropbox_base_test / mock_config.naming_and_organization.dropbox_strategies[0]
    diarias_dropbox_path_tv = db_strategy_path / mock_config.naming_and_organization.format_folder_tv
    diarias_dropbox_path_tv.mkdir(parents=True, exist_ok=True)
    (diarias_dropbox_path_tv / f"{mock_config.naming_and_organization.base_type_diaria}_tv_001_est.png").touch()
    (diarias_dropbox_path_tv / f"{mock_config.naming_and_organization.base_type_diaria}_tv_002_est.png").touch()
    (diarias_dropbox_path_tv / f"outro_arquivo_nao_diaria.png").touch() # Para testar o filtro de prefixo

    # Vídeos Locais
    videos_base.mkdir(parents=True, exist_ok=True)
    (videos_base / "video_ofertas_tv_segunda.mp4").touch()
    (videos_base / "video_ofertas_feed_terca.mp4").touch()

    logging.info(f"Ambiente de teste de limpeza (nova lógica) configurado em: {test_cleanup_root_dir.resolve()}")

    # --- Testar clean_diarias_comprehensive (dry_run=False) ---
    logging.info("\n--- Testando clean_diarias_comprehensive (dry_run=False, nova lógica) ---")
    # Deve deletar: 2 pastas locais, 2 arquivos diários no Dropbox, 2 vídeos
    deleted_count_diarias = clean_diarias_comprehensive(mock_config, dry_run=False)
    assert deleted_count_diarias == (2 + 2 + 2), f"Esperado 6 itens diários+vídeos deletados, obteve {deleted_count_diarias}"
    assert not (diarias_local_path / "2024-01-01").exists()
    assert not (diarias_local_path / "2024-01-02").exists()
    assert not (diarias_dropbox_path_tv / f"{mock_config.naming_and_organization.base_type_diaria}_tv_001_est.png").exists()
    assert not (diarias_dropbox_path_tv / f"{mock_config.naming_and_organization.base_type_diaria}_tv_002_est.png").exists()
    assert (diarias_dropbox_path_tv / f"outro_arquivo_nao_diaria.png").exists() # Não deve ser deletado
    assert not (videos_base / "video_ofertas_tv_segunda.mp4").exists()
    assert not (videos_base / "video_ofertas_feed_terca.mp4").exists()
    logging.info("clean_diarias_comprehensive (nova lógica): OK")

    # --- Testar clean_all_tracked_items (dry_run=True) ---
    logging.info("\n--- Testando clean_all_tracked_items (dry_run=True, nova lógica) ---")
    # Recriar alguns itens para o dry_run
    (diarias_local_path / "2024-01-01").mkdir(); (diarias_local_path / "2024-01-01" / "file1.txt").touch()
    (diarias_dropbox_path_tv / f"{mock_config.naming_and_organization.base_type_diaria}_tv_001_est.png").touch()
    (videos_base / "video_ofertas_tv_segunda.mp4").touch()
    # Adicionar itens para multidia e fixos (locais e dropbox)
    (archive_base / "MULTI_DIA" / "2024-01-03").mkdir(parents=True,exist_ok=True); (archive_base / "MULTI_DIA" / "2024-01-03" / "m1.txt").touch()
    multidia_db_path = db_strategy_path / mock_config.naming_and_organization.format_folder_feed
    multidia_db_path.mkdir(parents=True, exist_ok=True)
    (multidia_db_path / f"{mock_config.naming_and_organization.base_type_multidia}_feed_001_est.jpg").touch()

    (archive_base / "FIXOS" / "2024-01-04").mkdir(parents=True,exist_ok=True); (archive_base / "FIXOS" / "2024-01-04" / "f1.txt").touch()
    fixo_db_path = db_strategy_path / mock_config.naming_and_organization.format_folder_story
    fixo_db_path.mkdir(parents=True, exist_ok=True)
    (fixo_db_path / f"{mock_config.naming_and_organization.base_type_fixo}_story_001_est.webp").touch()


    total_would_delete = clean_all_tracked_items(mock_config, dry_run=True)
    # Esperado:
    # Diarias: 1 local (pasta) + 1 dropbox + 1 vídeo = 3
    # Multidia: 1 local (pasta) + 1 dropbox = 2
    # Fixos: 1 local (pasta) + 1 dropbox = 2
    # Vídeos já foram contados com diárias, então clean_generated_videos em clean_all não deve contar de novo se já zerado.
    # clean_all chama as _comprehensive. clean_diarias_comprehensive chama clean_all_generated_videos.
    # Então, os vídeos são contados uma vez.
    # Esperado: 1 local diaria + 1 db diaria + 1 local multidia + 1 db multidia + 1 local fixo + 1 db fixo + 1 video = 7
    assert total_would_delete == 7, f"Esperado 7 itens em dry_run para clean_all, obteve {total_would_delete}"
    logging.info(f"clean_all_tracked_items (dry_run=True, nova lógica): OK, {total_would_delete} itens seriam afetados.")

    logging.info("\nTestes de limpeza (nova lógica) de file_manager.py concluídos.")
    # if test_cleanup_root_dir.exists(): shutil.rmtree(test_cleanup_root_dir)