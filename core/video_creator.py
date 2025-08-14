import logging
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Sequence, Optional
from dataclasses import dataclass, field
from enum import Enum, auto as enum_auto
from datetime import datetime, timedelta
import math # Para math.isclose

from config import AppConfig, PathsConfig # Adicionado PathsConfig para o mock
from core import file_manager
from core.image_processor import ImageFormat

Image = None
try:
    from PIL import Image as PillowImage
    Image = PillowImage
except ImportError:
    logging.error("Pillow (PIL) não está instalado.")

# --- Constantes ---
TARGET_VIDEO_DURATION = 45.0  # Segundos

# --- Estruturas de Dados Específicas para Vídeo ---
class VideoOutputFormat(Enum):
    TV = enum_auto()
    STORY = enum_auto()
    FEED = enum_auto() # Mantido para mapeamento, mas filtrado na geração

@dataclass(frozen=True)
class VideoSegment:
    image_path: Path
    duration: float # Duração de input para FFmpeg (-t) para esta imagem

@dataclass(frozen=True)
class PlannedVideo:
    output_path: Path
    output_format: VideoOutputFormat
    segments: List[VideoSegment]
    framerate: int
    video_codec: str
    audio_codec: str
    video_preset: str
    crf: int
    transition_effect: str
    transition_duration: float # Duração de cada transição individual

# --- Funções Auxiliares ---
def _get_ffmpeg_path() -> str:
    return "ffmpeg"

def _map_str_to_video_output_format(format_str: str) -> Optional[VideoOutputFormat]:
    try:
        return VideoOutputFormat[format_str.strip().upper()]
    except KeyError:
        logging.error(f"Formato de vídeo desconhecido na configuração: '{format_str}'")
        return None

def get_day_of_week_pt(date_obj: datetime = datetime.now()) -> str:
    days_pt = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
    return days_pt[date_obj.weekday()]

# --- Coleta de Imagens para Vídeos ---
def _collect_images_for_video_creation(
    config: AppConfig,
    target_strategy: str,
    target_image_formats: List[str]
) -> Dict[str, List[Path]]:
    """
    Coleta imagens APENAS da estratégia e formatos de imagem especificados.
    Retorna um dicionário: {formato_imagem_key: [lista_de_paths_de_imagem]}
    """
    images_by_format: Dict[str, List[Path]] = {fmt: [] for fmt in target_image_formats}
    dropbox_base = config.paths.dropbox_base_path
    main_offers_folder_name = config.paths.dropbox_main_offers_folder_name

    format_key_to_folder_name = {
        "tv": config.naming_and_organization.format_folder_tv,
        "feed": config.naming_and_organization.format_folder_feed,
        "story": config.naming_and_organization.format_folder_story,
    }

    path_raiz_ofertas_dropbox = dropbox_base / main_offers_folder_name
    if not path_raiz_ofertas_dropbox.is_dir():
        logging.warning(f"Diretório principal de ofertas no Dropbox não encontrado: {path_raiz_ofertas_dropbox}")
        return images_by_format

    strategy_path = path_raiz_ofertas_dropbox / target_strategy
    if not strategy_path.is_dir():
        logging.warning(f"Diretório da estratégia '{target_strategy}' não encontrado em Dropbox: {strategy_path}")
        return images_by_format

    for fmt_key in target_image_formats:
        fmt_folder_name = format_key_to_folder_name.get(fmt_key)
        if not fmt_folder_name:
            logging.warning(f"Nome da pasta para o formato de imagem chave '{fmt_key}' não encontrado na configuração.")
            continue

        current_search_path = strategy_path / fmt_folder_name
        image_files_for_current_key: List[Path] = []
        if current_search_path.is_dir():
            image_files_for_current_key = sorted(file_manager.list_files_in_directory(
                current_search_path,
                pattern="*",
                filter_func=lambda p: p.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']
            ))
            if image_files_for_current_key:
                logging.debug(f"Encontradas {len(image_files_for_current_key)} imagens para estratégia '{target_strategy}', formato '{fmt_key}'")
        else:
             relative_path_log = current_search_path
             try:
                 relative_path_log = current_search_path.relative_to(dropbox_base)
             except ValueError:
                 pass
             logging.debug(f"Diretório não encontrado para estratégia '{target_strategy}', formato '{fmt_key}': {relative_path_log}")
        images_by_format[fmt_key] = image_files_for_current_key

    return images_by_format

# --- Planejamento de Vídeos ---
def _sort_images_for_video(image_paths: List[Path], config: AppConfig) -> List[Path]:
    base_type_prio = {
        config.naming_and_organization.base_type_fixo: 0,
        config.naming_and_organization.base_type_diaria: 1,
        config.naming_and_organization.base_type_multidia: 2,
    }
    def get_sort_key(path: Path) -> Tuple[int, str]:
        filename_stem = path.stem.lower()
        priority = 99
        file_base_type = filename_stem.split('_')[0]
        if file_base_type in base_type_prio:
            priority = base_type_prio[file_base_type]
        return (priority, filename_stem)
    return sorted(image_paths, key=get_sort_key)

def plan_videos(config: AppConfig) -> List[PlannedVideo]:
    planned_videos_list: List[PlannedVideo] = []

    video_source_strategy = "videos_e_feeds"
    source_image_formats_for_video = ["tv", "story"]

    if video_source_strategy not in config.naming_and_organization.dropbox_strategies:
        logging.error(f"Estratégia fonte vídeo '{video_source_strategy}' não config. Nenhum vídeo planejado.")
        return []

    images_for_videos = _collect_images_for_video_creation(config, video_source_strategy, source_image_formats_for_video)

    output_video_dir = config.paths.downloads_root_path / config.paths.videos_ofertas_output_folder_name
    if not file_manager.create_directory(output_video_dir):
        logging.error(f"Não criar dir saída vídeos: {output_video_dir}. Nenhum vídeo planejado."); return []

    target_output_video_formats_config: List[str] = [fmt.strip().lower() for fmt in config.video.output_video_formats]
    logging.debug(f"Formatos de vídeo de SAÍDA alvo (config.ini): {target_output_video_formats_config}")

    transition_duration_config = config.video.default_transition_duration_sec

    for fmt_imagem_key, image_paths in images_for_videos.items():
        if not image_paths:
            logging.debug(f"Sem imagens para {video_source_strategy}/{fmt_imagem_key}.")
            continue

        video_output_format_enum = _map_str_to_video_output_format(fmt_imagem_key)
        if not video_output_format_enum:
            logging.warning(f"Formato img '{fmt_imagem_key}' não mapeado. Pulando."); continue

        current_output_format_name_lower = video_output_format_enum.name.lower()
        if current_output_format_name_lower not in target_output_video_formats_config:
            logging.debug(f"Formato vídeo saída '{video_output_format_enum.name}' (de imgs '{fmt_imagem_key}') "
                          f"NÃO está em config.video.output_video_formats ({target_output_video_formats_config}). Pulando.")
            continue

        logging.info(f"Planejando vídeo para '{video_source_strategy}', formato saída '{video_output_format_enum.name}'...")

        sorted_image_paths = _sort_images_for_video(image_paths, config)
        num_images = len(sorted_image_paths)
        if num_images == 0: continue # Já verificado por 'if not image_paths'

        segments: List[VideoSegment] = []
        duration_per_image_input: float
        final_video_duration_calc: float

        if num_images == 1:
            duration_per_image_input = TARGET_VIDEO_DURATION
            final_video_duration_calc = TARGET_VIDEO_DURATION
        else:
            num_transitions = num_images - 1
            # Fórmula para DURAÇÃO DE INPUT por imagem, para que o vídeo FINAL tenha TARGET_VIDEO_DURATION
            # D_input_img = (TARGET_VIDEO_DURATION + N_transicoes * D_transicao_individual) / N_imagens
            duration_per_image_input = (TARGET_VIDEO_DURATION + num_transitions * transition_duration_config) / num_images

            # Duração final calculada do vídeo será: (N_imgs * D_input_img) - (N_transicoes * D_transicao_individual)
            # Esta deve ser igual a TARGET_VIDEO_DURATION
            final_video_duration_calc = (num_images * duration_per_image_input) - (num_transitions * transition_duration_config)

            # Verificar se a duração de input é muito pequena (pode ser problema para FFmpeg)
            if duration_per_image_input < 0.1: # Limiar arbitrário, mas < 3 frames a 30fps
                logging.warning(f"Duração de input por imagem ({duration_per_image_input:.3f}s) é muito baixa para {num_images} imagens "
                                f"e transições de {transition_duration_config}s para um vídeo de {TARGET_VIDEO_DURATION}s. "
                                "O vídeo pode não ser gerado corretamente ou ter qualidade ruim.")
                # Não vamos forçar um mínimo aqui, pois a meta é atingir TARGET_VIDEO_DURATION.
                # Se o cálculo resultar em duração muito baixa, é uma consequência de muitas imagens/transições.

        logging.info(f"  Para {num_images} imagens e {max(0, num_images - 1)} transições ({transition_duration_config}s cada):")
        logging.info(f"  Duração de CADA imagem (input FFmpeg -t): {duration_per_image_input:.3f}s.")
        logging.info(f"  Duração total do vídeo calculada (esperada após xfade): {final_video_duration_calc:.2f}s (Alvo: {TARGET_VIDEO_DURATION:.2f}s)")

        for img_path in sorted_image_paths:
            segments.append(VideoSegment(image_path=img_path, duration=duration_per_image_input))

        if not segments: continue

        dia_semana = get_day_of_week_pt(datetime.now())
        video_filename = f"video_ofertas_{video_output_format_enum.name.lower()}_{dia_semana}.mp4"
        video_output_path = output_video_dir / video_filename

        crf_value = config.video.video_crf_tv
        if video_output_format_enum == VideoOutputFormat.STORY: crf_value = config.video.video_crf_story
        elif video_output_format_enum == VideoOutputFormat.FEED: crf_value = config.video.video_crf_feed

        planned_videos_list.append(PlannedVideo(
            output_path=video_output_path, output_format=video_output_format_enum, segments=segments,
            framerate=config.video.video_framerate, video_codec=config.video.video_codec,
            audio_codec=config.video.audio_codec, video_preset=config.video.video_preset,
            crf=crf_value, transition_effect=config.video.default_transition_effect,
            transition_duration=transition_duration_config ))
        logging.info(f"Vídeo planejado: {video_output_path.name} com {len(segments)} segmentos.")

    if not planned_videos_list: logging.info("Nenhum vídeo foi planejado.")
    return planned_videos_list

def _get_output_dimensions_for_format(video_format: VideoOutputFormat, config: AppConfig) -> Tuple[int, int]:
    if video_format == VideoOutputFormat.TV: return config.processing.tv_dimensions_exact
    if video_format == VideoOutputFormat.FEED: return config.processing.feed_dimensions_exact
    if video_format == VideoOutputFormat.STORY: return config.processing.story_dimensions_exact
    logging.warning(f"Dimensões não definidas para {video_format}. Usando 1920x1080."); return (1920, 1080)

def _generate_video_with_ffmpeg(planned_video: PlannedVideo, ffmpeg_path: str, config: AppConfig, dry_run: bool = False) -> bool:
    logging.info(f"Geração de vídeo: {planned_video.output_path.name} (Formato: {planned_video.output_format.name})")
    out_w, out_h = _get_output_dimensions_for_format(planned_video.output_format, config)
    logging.debug(f"Dimensões de saída vídeo: {out_w}x{out_h}")

    input_commands: List[str] = []
    # Cada segmento já tem sua 'duration' calculada para o -t do input no FFmpeg
    for seg in planned_video.segments:
        input_commands.extend(["-loop", "1", "-t", f"{seg.duration:.3f}", "-i", str(seg.image_path.resolve())])

    if not input_commands: logging.error("Nenhum segmento input FFmpeg."); return False

    ffmpeg_cmd_list: List[str]

    if len(planned_video.segments) == 1:
        # Para vídeo de imagem única, o input -t já deve ser TARGET_VIDEO_DURATION
        # e o output -t também força essa duração.
        ffmpeg_cmd_list = [ffmpeg_path, "-y"] + input_commands + \
                       ["-vf", f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease:eval=frame,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1",
                        "-c:v", planned_video.video_codec, "-preset", planned_video.video_preset,
                        "-crf", str(planned_video.crf), "-r", str(planned_video.framerate),
                        "-pix_fmt", "yuv420p", "-an",
                        "-t", f"{TARGET_VIDEO_DURATION:.3f}",
                        str(planned_video.output_path.resolve())]
    else:
        filter_complex_parts: List[str] = []; scaled_streams: List[str] = []
        for i in range(len(planned_video.segments)):
            s_label = f"s{i}"
            scale_f = (f"[{i}:v]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease:eval=frame"
                       f",pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[{s_label}]")
            filter_complex_parts.append(scale_f); scaled_streams.append(f"[{s_label}]")

        stream_prev = scaled_streams[0]; num_transitions = len(planned_video.segments) - 1
        # current_timeline_pos agora é o tempo total que o vídeo teria se não houvesse sobreposição
        # mas o offset do xfade é relativo ao *início do stream de saída do xfade anterior*.
        # O offset da transição 'k' (0-indexed) é a soma das durações de input das imagens 0..k,
        # menos a soma das durações das transições 0..k.
        # Offset para transição i (entre imagem i e imagem i+1)
        # Esta é a duração de exibição da imagem i ANTES da transição começar.
        # D_img_input - D_trans. O offset é acumulativo.

        accumulated_offset_time = 0.0
        for i in range(num_transitions):
            stream_curr = scaled_streams[i+1]

            # Ponto no tempo do vídeo final onde a transição i (entre seg[i] e seg[i+1]) deve começar.
            # Se D_img é a duração de input de cada imagem e D_tr é a duração da transição:
            # Offset da 1ª transição (i=0): D_img - D_tr
            # Offset da 2ª transição (i=1): (D_img - D_tr) + (D_img - D_tr) = 2 * (D_img - D_tr)
            # Offset da transição i: (i+1) * (planned_video.segments[0].duration - planned_video.transition_duration)
            # No entanto, os exemplos do FFmpeg usam offset como o tempo absoluto no vídeo.
            # A transição i começa quando a imagem i esteve visível por D_img - D_tr.
            # O tempo acumulado até o início da transição i é:
            # accumulated_duration_so_far = i * (D_img - D_tr) (para as i transições anteriores)
            # offset_val = accumulated_duration_so_far + D_img - D_tr

            offset_val = (i + 1) * planned_video.segments[0].duration - (i + 1) * planned_video.transition_duration
            offset_val = max(0.001, offset_val)

            out_label = f"v{i+1}" if i < num_transitions - 1 else "vout"

            xfade_filter_segment = (
                f"{stream_prev}{stream_curr}"
                f"xfade=transition={planned_video.transition_effect}"
                f":duration={planned_video.transition_duration}"
                f":offset={offset_val:.3f}[{out_label}]"
            )
            filter_complex_parts.append(xfade_filter_segment)
            stream_prev = f"[{out_label}]"

        filter_complex_str = ";".join(filter_complex_parts)

        # A duração final do vídeo deve ser TARGET_VIDEO_DURATION.
        # O filter_complex deve produzir um stream dessa duração se os inputs -t forem calculados corretamente.
        # Forçar com -t na saída é uma garantia.
        ffmpeg_cmd_list = [ffmpeg_path, "-y"] + input_commands + \
                       ["-filter_complex", filter_complex_str, "-map", stream_prev,
                        "-c:v", planned_video.video_codec, "-preset", planned_video.video_preset,
                        "-crf", str(planned_video.crf), "-r", str(planned_video.framerate),
                        "-pix_fmt", "yuv420p", "-an",
                        "-t", f"{TARGET_VIDEO_DURATION:.3f}",
                        str(planned_video.output_path.resolve())]

    logging.debug(f"Comando FFmpeg: {' '.join(ffmpeg_cmd_list)}")
    if dry_run: logging.info(f"[DRY RUN] Geraria: {planned_video.output_path.name}"); return True
    try:
        process = subprocess.run(ffmpeg_cmd_list, capture_output=True, text=True, check=False, encoding='utf-8')
        if process.returncode == 0:
            logging.info(f"Vídeo gerado: {planned_video.output_path.name}")
            if process.stderr: logging.debug(f"FFmpeg stderr:\n{process.stderr}");
            return True
        else:
            logging.error(f"Falha gerar vídeo: {planned_video.output_path.name}")
            logging.error(f"Comando: {' '.join(ffmpeg_cmd_list)}")
            logging.error(f"FFmpeg stdout:\n{process.stdout}")
            logging.error(f"FFmpeg stderr:\n{process.stderr}"); return False
    except FileNotFoundError: logging.error(f"FFmpeg não encontrado: '{ffmpeg_path}'"); return False
    except Exception as e: logging.error(f"Erro FFmpeg: {e}", exc_info=True); return False

def create_videos(config: AppConfig, dry_run: bool = False) -> bool:
    logging.info(f"Iniciando criação de vídeos. Dry run: {dry_run}")
    ffmpeg_exe = _get_ffmpeg_path()
    planned_videos = plan_videos(config)
    if not planned_videos: logging.info("Nenhum vídeo planejado."); return True
    all_successful = True
    for video_plan in planned_videos:
        if not _generate_video_with_ffmpeg(video_plan, ffmpeg_exe, config, dry_run):
            all_successful = False
    if all_successful: logging.info("Vídeos gerados com sucesso (ou simulados).")
    else: logging.warning("Alguns vídeos falharam. Verifique logs.")
    return all_successful

# Bloco de teste
if __name__ == "__main__":
    import sys
    import shutil
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from config import load_app_config, CONFIG_FILE_PATH
    from dataclasses import replace

    log_format = "%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s"
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]: root_logger.removeHandler(handler)
    logging.basicConfig(level=logging.DEBUG, format=log_format, stream=sys.stdout)

    logging.info("Testando core/video_creator.py (Duração Exata de 45s)...")

    try: original_config = load_app_config(CONFIG_FILE_PATH)
    except Exception as e: logging.error(f"Falha carregar config: {e}"); sys.exit(1)

    test_env_root = project_root / "temp_video_creator_tests_v4_exact_duration"
    if test_env_root.exists(): shutil.rmtree(test_env_root)
    test_env_root.mkdir(parents=True, exist_ok=True)

    mock_paths = PathsConfig(
        downloads_root_path = test_env_root / "Downloads",
        dropbox_base_path = test_env_root / "Dropbox",
        dropbox_main_offers_folder_name=original_config.paths.dropbox_main_offers_folder_name,
        ofertas_multi_dia_folder_name="OFERTAS_MULTI_DIA",
        ofertas_bebidas_folder_name="OFERTAS_BEBIDAS",
        elementos_fixos_folder_name="ELEMENTOS_FIXOS",
        arquivos_ofertas_root_folder_name="ARQUIVOS_OFERTAS_LOCAIS",
        videos_ofertas_output_folder_name="VIDEOS_OFERTAS_LOCAIS"
    )
    # Manter output_video_formats=["tv", "story"] para testar o filtro de fonte
    mock_video_cfg = replace(original_config.video, output_video_formats=["tv", "story"])
    mock_config: AppConfig = replace(original_config, paths=mock_paths, video=mock_video_cfg)

    dropbox_video_src_dir_base = mock_config.paths.dropbox_base_path / mock_config.paths.dropbox_main_offers_folder_name
    video_source_strategy_teste = "videos_e_feeds"
    strategy_dir_in_dropbox = dropbox_video_src_dir_base / video_source_strategy_teste
    strategy_dir_in_dropbox.mkdir(parents=True, exist_ok=True)

    formatos_fonte_para_video = {
        "tv": (mock_config.naming_and_organization.format_folder_tv, mock_config.processing.tv_dimensions_exact),
        "story": (mock_config.naming_and_organization.format_folder_story, mock_config.processing.story_dimensions_exact),
    }

    if Image:
        dia_atual_str = get_day_of_week_pt(datetime.now())
        images_counts_test_map = {"tv": 1, "story": 10}

        for fmt_key, (fmt_folder_name, dims) in formatos_fonte_para_video.items():
            fmt_dir = strategy_dir_in_dropbox / fmt_folder_name
            fmt_dir.mkdir(parents=True, exist_ok=True)
            for child in fmt_dir.iterdir():
                if child.is_file(): child.unlink() # Limpar apenas arquivos

            num_images_this_format = images_counts_test_map.get(fmt_key, 5)

            for i in range(num_images_this_format):
                Image.new("RGB", dims, "gray").save(fmt_dir / f"{mock_config.naming_and_organization.base_type_fixo}_{i+1:03d}_{video_source_strategy_teste}.png")
            logging.info(f"{num_images_this_format} imagens FIXAS de teste (Pillow) criadas para '{fmt_key}' em {fmt_dir}")
    else:
        logging.warning("Pillow não disponível.")

    logging.info("\n--- Testando plan_videos (duração exata de 45s) ---")
    planned_list = plan_videos(mock_config)

    assert len(planned_list) == 2, f"Esperado 2 vídeos planejados (TV e Story), obteve {len(planned_list)}"

    for pv in planned_list:
        logging.info(f"Vídeo Planejado: {pv.output_path.name}, Formato Saída: {pv.output_format.name}, N.Segmentos: {len(pv.segments)}")
        assert len(pv.segments) > 0, "Vídeo planejado não tem segmentos."

        expected_seg_duration = pv.segments[0].duration
        logging.info(f"  Duração calculada por segmento (input FFmpeg -t): {expected_seg_duration:.3f}s")

        num_images_pv = len(pv.segments)
        num_transitions_pv = max(0, num_images_pv - 1)
        # Esta é a duração final REAL do vídeo que o FFmpeg deve produzir com xfade
        final_video_duration_estimate_pv = (num_images_pv * expected_seg_duration) - (num_transitions_pv * pv.transition_duration)

        logging.info(f"  Duração total REALMENTE ESPERADA para {pv.output_path.name}: {final_video_duration_estimate_pv:.2f}s (Alvo: {TARGET_VIDEO_DURATION:.2f}s)")

        assert math.isclose(final_video_duration_estimate_pv, TARGET_VIDEO_DURATION, rel_tol=0.01, abs_tol=0.05), \
            f"Vídeo {pv.output_path.name} ({final_video_duration_estimate_pv:.2f}s) fora da duração alvo de {TARGET_VIDEO_DURATION}s (tolerância pequena)."

    logging.info("Planejamento com duração exata de 45s: OK.")

    logging.info("\n--- Testando create_videos (dry_run=True, com novas regras de duração) ---")
    mock_video_output_dir = mock_config.paths.downloads_root_path / mock_config.paths.videos_ofertas_output_folder_name
    if mock_video_output_dir.exists(): shutil.rmtree(mock_video_output_dir)

    ffmpeg_path_test = _get_ffmpeg_path()
    can_run_ffmpeg_tests = False
    try:
        ff_ver = subprocess.run([ffmpeg_path_test, "-version"], capture_output=True, check=True, timeout=5, encoding='utf-8')
        logging.info(f"FFmpeg OK: {ffmpeg_path_test} ({ff_ver.stdout.splitlines()[0] if ff_ver.stdout else 'N/A'})")
        can_run_ffmpeg_tests = True
    except Exception as e: logging.warning(f"FFmpeg N/OK ({ffmpeg_path_test} -version: {e}).")

    if can_run_ffmpeg_tests and Image:
        all_gen_success = create_videos(mock_config, dry_run=True)
        assert all_gen_success, "create_videos (dry_run) reportou falha."
        if planned_list:
             for pv_plan in planned_list:
                 assert not pv_plan.output_path.exists(), f"Vídeo {pv_plan.output_path} NÃO deveria existir (dry_run)."
        logging.info("create_videos (dry_run=True) com novas regras de duração: OK (simulado).")
    else:
        logging.info("Pulando teste create_videos (dry_run=True) - FFmpeg ou Pillow não funcional / imagens não criadas.")

    logging.info("\nTestes de video_creator.py (Duração Exata de 45s) concluídos.")
    # if test_env_root.exists(): shutil.rmtree(test_env_root)