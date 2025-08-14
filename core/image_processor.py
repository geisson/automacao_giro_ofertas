import logging
from pathlib import Path
from typing import List, Tuple, Dict, Callable, Optional, Sequence
from enum import Enum, auto as enum_auto
from datetime import datetime, timedelta
import re
from dataclasses import dataclass
import os

from config import AppConfig
from core import file_manager

Image = None
try:
    from PIL import Image as PillowImage
    Image = PillowImage
except ImportError:
    logging.error("Pillow (PIL) não está instalado.")

class OfferType(Enum):
    DIARIA = enum_auto(); MULTIDIA = enum_auto(); BEBIDA_DIARIA = enum_auto()
    BEBIDA_MULTIDIA = enum_auto(); ELEMENTO_FIXO = enum_auto()

class ImageFormat(Enum):
    TV = enum_auto(); FEED = enum_auto(); STORY = enum_auto(); UNKNOWN = enum_auto()

class ImageSourceCategory(Enum):
    DOWNLOADS_ROOT = enum_auto(); OFERTAS_DIARIAS_BEBIDAS = enum_auto()
    OFERTAS_MULTIDIA_GERAL = enum_auto(); OFERTAS_MULTIDIA_BEBIDAS = enum_auto()
    ELEMENTOS_FIXOS = enum_auto()

@dataclass(frozen=True)
class SourceImageFile:
    path: Path; category: ImageSourceCategory; original_name: str
    modified_time: float

@dataclass(frozen=True)
class ProcessedImageInfo:
    source_file: SourceImageFile; offer_type: OfferType; image_format: ImageFormat
    target_filename: Optional[str] = None; target_dropbox_path: Optional[Path] = None
    target_archive_path: Optional[Path] = None

def _is_image_file(file_path: Path) -> bool:
    return file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']

def _get_image_dimensions(image_path: Path) -> Optional[Tuple[int, int]]:
    if not Image: return None
    try:
        with Image.open(image_path) as img: return img.size
    except Exception: return None

def _get_source_location_config(config: AppConfig) -> List[Tuple[Path, ImageSourceCategory, Optional[str]]]:
    downloads_root = config.paths.downloads_root_path
    return [
        (downloads_root, ImageSourceCategory.DOWNLOADS_ROOT, config.processing.qrofertas_keyword.lower()),
        (downloads_root / config.paths.ofertas_bebidas_folder_name, ImageSourceCategory.OFERTAS_DIARIAS_BEBIDAS, None),
        (downloads_root / config.paths.ofertas_multi_dia_folder_name, ImageSourceCategory.OFERTAS_MULTIDIA_GERAL, None),
        (downloads_root / config.paths.ofertas_multi_dia_folder_name / "BEBIDAS", ImageSourceCategory.OFERTAS_MULTIDIA_BEBIDAS, None),
        (downloads_root / config.paths.elementos_fixos_folder_name, ImageSourceCategory.ELEMENTOS_FIXOS, None),
    ]

def collect_source_images(config: AppConfig) -> List[SourceImageFile]:
    all_collected_images: List[SourceImageFile] = []
    source_locations = _get_source_location_config(config)
    for dir_path, category, keyword in source_locations:
        if not dir_path.is_dir(): logging.debug(f"Dir origem não encontrado: {dir_path.resolve()}"); continue
        logging.debug(f"Procurando em: {dir_path.resolve()} (Cat: {category.name})")
        potential_files_paths = file_manager.list_files_in_directory(dir_path, pattern="*")
        category_images: List[SourceImageFile] = []
        for file_path in potential_files_paths:
            if not _is_image_file(file_path): continue
            if category == ImageSourceCategory.DOWNLOADS_ROOT and keyword and keyword not in file_path.name.lower(): continue
            try:
                m_time = file_path.stat().st_mtime
                category_images.append(SourceImageFile(file_path, category, file_path.name, m_time))
            except FileNotFoundError: logging.warning(f"Arq {file_path} não encontrado (stat), pulando."); continue
        category_images.sort(key=lambda x: x.modified_time)
        all_collected_images.extend(category_images)
    if not all_collected_images: logging.info("Nenhuma imagem fonte encontrada.")
    else:
        logging.info(f"Total {len(all_collected_images)} imgs coletadas e ordenadas intra-categoria.")
        for img_info in all_collected_images: logging.debug(f"  Coletada: {img_info.path.name} (Cat: {img_info.category.name}, ModTime: {img_info.modified_time})")
    return all_collected_images

def classify_offer_type(image_info: SourceImageFile, config: AppConfig) -> OfferType:
    # ... (sem alteração) ...
    if image_info.category == ImageSourceCategory.DOWNLOADS_ROOT: return OfferType.DIARIA
    if image_info.category == ImageSourceCategory.OFERTAS_DIARIAS_BEBIDAS: return OfferType.BEBIDA_DIARIA
    if image_info.category == ImageSourceCategory.OFERTAS_MULTIDIA_GERAL: return OfferType.MULTIDIA
    if image_info.category == ImageSourceCategory.OFERTAS_MULTIDIA_BEBIDAS: return OfferType.BEBIDA_MULTIDIA
    if image_info.category == ImageSourceCategory.ELEMENTOS_FIXOS: return OfferType.ELEMENTO_FIXO
    logging.error(f"FALLBACK CLASSIFICAÇÃO: {image_info.path.name} cat {image_info.category.name}")
    return OfferType.DIARIA


def classify_image_format(image_path: Path, offer_type: OfferType, config: AppConfig) -> ImageFormat:
    # ... (sem alteração) ...
    dimensions = _get_image_dimensions(image_path)
    if not dimensions: logging.warning(f"Dimensões não obtidas para {image_path.name}, formato UNKNOWN."); return ImageFormat.UNKNOWN
    width, height = dimensions
    if offer_type in [OfferType.DIARIA, OfferType.MULTIDIA, OfferType.BEBIDA_DIARIA, OfferType.BEBIDA_MULTIDIA]:
        if (width, height) == config.processing.tv_dimensions_exact: return ImageFormat.TV
        if (width, height) == config.processing.feed_dimensions_exact: return ImageFormat.FEED
        if (width, height) == config.processing.story_dimensions_exact: return ImageFormat.STORY
        logging.debug(f"Dimensões {dimensions} para {offer_type.name} ({image_path.name}) não correspondem."); return ImageFormat.UNKNOWN
    elif offer_type == OfferType.ELEMENTO_FIXO:
        if height == 0: logging.warning(f"Altura 0 para {image_path.name}."); return ImageFormat.UNKNOWN
        ratio = width / height; tolerance = config.processing.aspect_ratio_tolerance
        if abs(ratio - config.processing.tv_target_ratio) <= tolerance: return ImageFormat.TV
        if abs(ratio - config.processing.feed_target_ratio) <= tolerance: return ImageFormat.FEED
        if abs(ratio - config.processing.story_target_ratio) <= tolerance: return ImageFormat.STORY
        logging.debug(f"Proporção {ratio:.4f} para ELEMENTO_FIXO ({image_path.name}) não corresponde."); return ImageFormat.UNKNOWN
    logging.error(f"Tipo {offer_type} não suportado para classif. formato ({image_path.name})"); return ImageFormat.UNKNOWN

def get_day_of_week_pt(date_obj: datetime = datetime.now()) -> str:
    days_pt = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
    return days_pt[date_obj.weekday()]

def generate_target_filename(offer_type: OfferType, image_format: ImageFormat, sequence_number: int, estrategia_dropbox: str, config: AppConfig, original_extension: str) -> str:
    # ... (sem alteração) ...
    tipo_base_map = { OfferType.DIARIA: config.naming_and_organization.base_type_diaria, OfferType.BEBIDA_DIARIA: config.naming_and_organization.base_type_diaria, OfferType.MULTIDIA: config.naming_and_organization.base_type_multidia, OfferType.BEBIDA_MULTIDIA: config.naming_and_organization.base_type_multidia, OfferType.ELEMENTO_FIXO: config.naming_and_organization.base_type_fixo }
    tipo_base = tipo_base_map.get(offer_type, "desconhecido")
    dia_ou_id = get_day_of_week_pt() if offer_type in [OfferType.DIARIA, OfferType.BEBIDA_DIARIA] else ""
    opcional_bebida = config.naming_and_organization.bebida_keyword if offer_type in [OfferType.BEBIDA_DIARIA, OfferType.BEBIDA_MULTIDIA] else ""
    seq_str = str(sequence_number).zfill(config.naming_and_organization.sequential_number_padding)
    parts = [p for p in [tipo_base, dia_ou_id, opcional_bebida, seq_str, estrategia_dropbox] if p]
    return f"{'_'.join(parts)}{original_extension.lower()}"


# MODIFICADA get_next_sequence_number
def get_next_sequence_number(
    directory: Path,
    filename_prefix_for_glob: str, # Ex: "diaria_sabado_videos_e_feeds" (sem seq, sem ext)
                                    # Ou mais precisamente: "diaria_sabado_" (parte antes do seq)
                                    # E "videos_e_feeds" (parte depois do seq)
    filename_suffix_for_glob: str, # Ex: "_videos_e_feeds" (sem ext)
    config: AppConfig
) -> int:
    """
    Encontra o próximo número sequencial.
    Lista todos os arquivos no diretório (independente da extensão inicial do glob).
    filename_prefix_for_glob: Parte do nome ANTES do número sequencial. (ex: "diaria_sabado_")
    filename_suffix_for_glob: Parte do nome DEPOIS do número sequencial, ANTES da extensão. (ex: "_videos_e_feeds")
    """
    max_seq = 0
    padding = config.naming_and_organization.sequential_number_padding

    # Regex para extrair o número: prefixo_NUMERO_sufixo.qualquercoisa
    # O prefixo e sufixo podem conter underscores.
    # Os números devem ter o comprimento do padding.
    # ^ escaped_prefix (\d{PADDING}) escaped_suffix \. .* $
    # (Não, o stem não inclui a extensão final, então a regex é no stem)
    # Regex: ^escaped_prefix(\d{PADDING})escaped_suffix$ (aplicado ao stem do arquivo)

    # Escapar prefixo e sufixo para uso em regex
    escaped_prefix = re.escape(filename_prefix_for_glob)
    escaped_suffix = re.escape(filename_suffix_for_glob)

    # Regex para o nome do arquivo SEM extensão (stem)
    # Ex: prefix="diaria_sexta_", padding=3, suffix="_videos_e_feeds"
    # Regex: r"^diaria_sexta_(\d{3})_videos_e_feeds$"
    regex_pattern_str = f"^{escaped_prefix}(\\d{{{padding}}}){escaped_suffix}$"

    try:
        regex_pattern = re.compile(regex_pattern_str)
    except re.error as e:
        logging.error(f"Erro ao compilar regex para sequencial '{regex_pattern_str}': {e}")
        return 1 # Fallback

    # Lista todos os arquivos no diretório de destino, depois filtra por nome.
    # Não podemos usar um glob muito específico aqui se quisermos ser agnósticos à extensão.
    # Mas o `filename_prefix_for_glob` já pode ser bem específico.
    # Ex: `list_files_in_directory(directory, pattern=f"{filename_prefix_for_glob}*")`
    #     Isso pegaria "diaria_sexta_001_videos_e_feeds.png" E "diaria_sexta_001_videos_e_feeds.jpg"

    files_to_check = file_manager.list_files_in_directory(directory, pattern=f"{filename_prefix_for_glob}*")

    for file_path in files_to_check:
        stem = file_path.stem # Nome do arquivo sem extensão
        match = regex_pattern.fullmatch(stem)
        if match:
            try:
                seq_str = match.group(1)
                max_seq = max(max_seq, int(seq_str))
            except (IndexError, ValueError):
                logging.warning(f"Não foi possível extrair número sequencial de '{stem}' usando padrão '{regex_pattern_str}'.")
        # else:
            # logging.debug(f"Stem '{stem}' não correspondeu ao regex '{regex_pattern_str}' para sequencial.")

    return max_seq + 1


def process_images(config: AppConfig, estrategia_dropbox: str, dry_run: bool = False) -> List[ProcessedImageInfo]:
    logging.info(f"Iniciando processamento. Estratégia: '{estrategia_dropbox}', Dry run: {dry_run}")
    if estrategia_dropbox not in config.naming_and_organization.dropbox_strategies:
        logging.error(f"Estratégia Dropbox '{estrategia_dropbox}' inválida."); return []

    source_image_files = collect_source_images(config)
    if not source_image_files: logging.info("Nenhuma imagem para processar."); return []

    processed_summary: List[ProcessedImageInfo] = []

    for src_img_file in source_image_files:
        logging.debug(f"Processando: {src_img_file.path.name} (Cat: {src_img_file.category.name})")
        offer_type = classify_offer_type(src_img_file, config)
        image_format = classify_image_format(src_img_file.path, offer_type, config)
        if image_format == ImageFormat.UNKNOWN:
            logging.warning(f"  Ignorada (formato desconhecido): {src_img_file.path.name}"); continue

        original_extension = src_img_file.path.suffix
        format_folder_map = {ImageFormat.TV: config.naming_and_organization.format_folder_tv,
                             ImageFormat.FEED: config.naming_and_organization.format_folder_feed,
                             ImageFormat.STORY: config.naming_and_organization.format_folder_story}
        format_folder_name = format_folder_map.get(image_format, "fmt_desconhecido")

        target_dropbox_dir = (config.paths.dropbox_base_path /
            config.paths.dropbox_main_offers_folder_name / estrategia_dropbox / format_folder_name)

        # Construir prefixo e sufixo para get_next_sequence_number
        # <tipo_base>_<dia_ou_id>_<opcional_bebida>   -> PREFIXO (antes do _seq)
        # _<estrategia>                               -> SUFIXO (depois do _seq)

        tipo_base_map = { OfferType.DIARIA: config.naming_and_organization.base_type_diaria, OfferType.BEBIDA_DIARIA: config.naming_and_organization.base_type_diaria, OfferType.MULTIDIA: config.naming_and_organization.base_type_multidia, OfferType.BEBIDA_MULTIDIA: config.naming_and_organization.base_type_multidia, OfferType.ELEMENTO_FIXO: config.naming_and_organization.base_type_fixo }

        name_parts_prefix = [tipo_base_map.get(offer_type)]
        if offer_type in [OfferType.DIARIA, OfferType.BEBIDA_DIARIA]: name_parts_prefix.append(get_day_of_week_pt())
        if offer_type in [OfferType.BEBIDA_DIARIA, OfferType.BEBIDA_MULTIDIA]: name_parts_prefix.append(config.naming_and_organization.bebida_keyword)

        filename_prefix_for_seq = "_".join(filter(None, name_parts_prefix))
        if filename_prefix_for_seq: # Adicionar underscore no final do prefixo se ele não estiver vazio
            filename_prefix_for_seq += "_"

        filename_suffix_for_seq = f"_{estrategia_dropbox}" # Sufixo sempre começa com _ e tem a estratégia

        if not dry_run: # Garante que o diretório exista para a contagem real de sequenciais
            file_manager.create_directory(target_dropbox_dir, dry_run=False)

        sequence_number = get_next_sequence_number(target_dropbox_dir, filename_prefix_for_seq, filename_suffix_for_seq, config)
        target_filename = generate_target_filename(offer_type, image_format, sequence_number, estrategia_dropbox, config, original_extension)
        target_dropbox_path = target_dropbox_dir / target_filename

        archive_base_folder = config.paths.downloads_root_path / config.paths.arquivos_ofertas_root_folder_name
        offer_type_folder_map = { OfferType.DIARIA: "DIARIAS", OfferType.BEBIDA_DIARIA: "DIARIAS",
                                  OfferType.MULTIDIA: "MULTI_DIA", OfferType.BEBIDA_MULTIDIA: "MULTI_DIA",
                                  OfferType.ELEMENTO_FIXO: "FIXOS" }
        archive_offer_type_folder = offer_type_folder_map.get(offer_type, "OUTROS")
        current_date_str = datetime.now().strftime(config.general.archive_date_format.replace("%%", "%"))
        tipo_original_folder = src_img_file.category.name.upper()
        target_archive_path = (archive_base_folder / archive_offer_type_folder /
                               current_date_str / tipo_original_folder / src_img_file.original_name)

        logging.info(f"  {src_img_file.path.name} -> Tipo: {offer_type.name}, Formato: {image_format.name}")
        logging.info(f"    Destino Dropbox: {target_dropbox_path.name} (em .../{estrategia_dropbox}/{format_folder_name})")
        logging.info(f"    Destino Arquivo: .../{archive_offer_type_folder}/{current_date_str}/{tipo_original_folder}/{src_img_file.original_name}")

        copied_to_dropbox = file_manager.copy_file(src_img_file.path, target_dropbox_path, dry_run)

        archived_original_action_success = False
        if copied_to_dropbox or dry_run:
            if offer_type == OfferType.ELEMENTO_FIXO:
                archived_original_action_success = file_manager.copy_file(src_img_file.path, target_archive_path, dry_run)
                if not archived_original_action_success and not dry_run: logging.warning(f"    Falha ARQUIVAR (copiar) ELEMENTO_FIXO {src_img_file.path.name}.")
                elif not dry_run and archived_original_action_success: logging.info(f"    ELEMENTO_FIXO {src_img_file.path.name} copiado para arq. Original mantido.")
            else:
                archived_original_action_success = file_manager.move_file(src_img_file.path, target_archive_path, dry_run)
                if not archived_original_action_success and not dry_run: logging.error(f"    Falha arquivar (mover) original {src_img_file.path.name}.")
        elif not dry_run: logging.error(f"    Falha copiar para Dropbox ({src_img_file.path.name}), arquivamento não tentado.")

        if (copied_to_dropbox and archived_original_action_success) or \
           (dry_run and copied_to_dropbox) or \
           (offer_type == OfferType.ELEMENTO_FIXO and copied_to_dropbox):
            processed_summary.append(ProcessedImageInfo(
                src_img_file, offer_type, image_format, target_filename, target_dropbox_path,
                target_archive_path if archived_original_action_success else None ))
            logging.debug(f"  Processamento de {src_img_file.path.name} (ou simulação) OK.")
        elif not dry_run: logging.error(f"  Falha no processamento completo de {src_img_file.path.name}.")

    logging.info(f"Processamento de imagens concluído. {len(processed_summary)} imagens processadas/simuladas.")
    return processed_summary

# Bloco de teste
if __name__ == "__main__":
    import sys
    import shutil
    from dataclasses import replace
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path: sys.path.insert(0, str(project_root))
    from config import load_app_config, CONFIG_FILE_PATH, AppConfig, PathsConfig, ProcessingConfig, NamingAndOrganizationConfig, VideoConfig, CleaningConfig, GeneralConfig

    log_format = "%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s"
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]: root_logger.removeHandler(handler)
    logging.basicConfig(level=logging.DEBUG, format=log_format, stream=sys.stdout)
    logging.info("Testando core/image_processor.py (Ordenação, Fixos, Sequencial Refinado)...")

    try: original_config = load_app_config(CONFIG_FILE_PATH)
    except Exception as e: logging.error(f"Falha carregar config: {e}"); sys.exit(1)

    test_env_root = project_root / "temp_imgproc_test_v_order_fixos_seq" # Novo dir
    if test_env_root.exists(): shutil.rmtree(test_env_root)
    test_env_root.mkdir(parents=True, exist_ok=True)

    mock_paths = PathsConfig(
        downloads_root_path = test_env_root / "Downloads",
        dropbox_base_path = test_env_root / "Dropbox",
        dropbox_main_offers_folder_name=original_config.paths.dropbox_main_offers_folder_name,
        ofertas_multi_dia_folder_name="OFERTAS_MULTI_DIA",
        ofertas_bebidas_folder_name="OFERTAS_BEBIDAS",
        elementos_fixos_folder_name="ELEMENTOS_FIXOS_TEST",
        arquivos_ofertas_root_folder_name="ARQUIVOS_OFERTAS",
        videos_ofertas_output_folder_name="VIDEOS_OFERTAS"
    )
    mock_config = replace(original_config, paths=mock_paths)

    dl_root = mock_config.paths.downloads_root_path
    fixos_origem_path = dl_root / mock_config.paths.elementos_fixos_folder_name
    fixos_origem_path.mkdir(parents=True, exist_ok=True)
    diarias_source_path = dl_root / "diarias_source"
    diarias_source_path.mkdir(parents=True, exist_ok=True)

    now_ts = datetime.now()
    file_c_path = diarias_source_path / f"{mock_config.processing.qrofertas_keyword}_ofertaC.png"
    file_a_path = diarias_source_path / f"{mock_config.processing.qrofertas_keyword}_ofertaA.png" # Mais antigo
    file_b_path = diarias_source_path / f"{mock_config.processing.qrofertas_keyword}_ofertaB.jpg" # Meio

    if Image:
        Image.new("RGB", mock_config.processing.tv_dimensions_exact, "blue").save(file_c_path)
        Image.new("RGB", mock_config.processing.tv_dimensions_exact, "red").save(file_a_path)
        Image.new("RGB", mock_config.processing.tv_dimensions_exact, "green").save(file_b_path)
    else:
        file_c_path.touch(); file_a_path.touch(); file_b_path.touch()

    os.utime(file_a_path, ((now_ts - timedelta(seconds=20)).timestamp(), (now_ts - timedelta(seconds=20)).timestamp()))
    os.utime(file_b_path, ((now_ts - timedelta(seconds=10)).timestamp(), (now_ts - timedelta(seconds=10)).timestamp()))
    # file_c_path tem mtime de "agora"

    fixo_original_path = fixos_origem_path / "elemento_fixo_teste.png"
    if Image: Image.new("RGB", mock_config.processing.story_dimensions_exact, "gray").save(fixo_original_path)
    else: fixo_original_path.touch()

    original_get_source_location_config = _get_source_location_config
    def mock_get_source_locations_for_test(config: AppConfig):
        return [
            (config.paths.downloads_root_path / "diarias_source", ImageSourceCategory.DOWNLOADS_ROOT, config.processing.qrofertas_keyword.lower()),
            (config.paths.downloads_root_path / config.paths.elementos_fixos_folder_name, ImageSourceCategory.ELEMENTOS_FIXOS, None)
        ]
    globals()['_get_source_location_config'] = mock_get_source_locations_for_test

    logging.info("\n--- Testando process_images (dry_run=False, sequencial agnóstico à extensão) ---")
    estrategia_teste = mock_config.naming_and_organization.dropbox_strategies[0]

    dropbox_test_dir_tv = mock_config.paths.dropbox_base_path / mock_config.paths.dropbox_main_offers_folder_name / estrategia_teste / mock_config.naming_and_organization.format_folder_tv
    if dropbox_test_dir_tv.exists(): shutil.rmtree(dropbox_test_dir_tv)
    # Não precisa criar, process_images fará isso.

    processed = process_images(mock_config, estrategia_teste, dry_run=False)
    globals()['_get_source_location_config'] = original_get_source_location_config

    assert len(processed) == 4, f"Esperado 4 itens processados, obteve {len(processed)}"

    ofertas_diarias_processadas = sorted(
        [p for p in processed if p.offer_type == OfferType.DIARIA],
        key=lambda p: p.source_file.modified_time # Ordenar por mtime original para verificar o sequencial
    )

    assert len(ofertas_diarias_processadas) == 3

    # Verificar se os nomes refletem a ordem de mtime (A->001, B->002, C->003)
    # independentemente da extensão original.
    # Assumindo que todos são classificados como TV e vão para a mesma pasta de destino.
    if ofertas_diarias_processadas[0].target_filename:
        assert "_001_" in ofertas_diarias_processadas[0].target_filename, f"Oferta A (mais antiga) deveria ser _001_, foi {ofertas_diarias_processadas[0].target_filename}"
    if ofertas_diarias_processadas[1].target_filename:
        assert "_002_" in ofertas_diarias_processadas[1].target_filename, f"Oferta B (meio) deveria ser _002_, foi {ofertas_diarias_processadas[1].target_filename}"
    if ofertas_diarias_processadas[2].target_filename:
        assert "_003_" in ofertas_diarias_processadas[2].target_filename, f"Oferta C (mais recente) deveria ser _003_, foi {ofertas_diarias_processadas[2].target_filename}"
    logging.info("Ordenação e nomeação sequencial (agnóstico à extensão) para ofertas diárias: OK")

    fixo_processado_info = next((p for p in processed if p.offer_type == OfferType.ELEMENTO_FIXO), None)
    assert fixo_processado_info is not None
    assert fixo_original_path.exists()
    logging.info(f"Elemento fixo '{fixo_original_path.name}' processado e original mantido: OK")
    if fixo_processado_info.target_archive_path:
         assert fixo_processado_info.target_archive_path.exists()
         logging.info("Elemento fixo copiado para arquivamento: OK")

    logging.info("\nTestes de image_processor.py (Ordenação, Fixos, Sequencial Refinado) concluídos.")
    # if test_env_root.exists(): shutil.rmtree(test_env_root)