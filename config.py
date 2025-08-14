import configparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Dict

CONFIG_FILE_PATH = Path(__file__).parent / "config.ini"

def _parse_dimensions(dim_str: str) -> Tuple[int, int]:
    try: width, height = map(int, dim_str.lower().split('x')); return width, height
    except ValueError: raise ValueError(f"Formato de dimensão inválido: '{dim_str}'.")

def _parse_comma_separated_list(list_str: str) -> List[str]:
    if not list_str.strip(): return []
    return [item.strip() for item in list_str.split(',')]

@dataclass(frozen=True)
class PathsConfig:
    downloads_root_path: Path; dropbox_base_path: Path
    dropbox_main_offers_folder_name: str; ofertas_multi_dia_folder_name: str
    ofertas_bebidas_folder_name: str; elementos_fixos_folder_name: str
    arquivos_ofertas_root_folder_name: str; videos_ofertas_output_folder_name: str

@dataclass(frozen=True)
class ProcessingConfig:
    qrofertas_keyword: str; aspect_ratio_tolerance: float
    tv_dimensions_exact: Tuple[int, int]; feed_dimensions_exact: Tuple[int, int]
    story_dimensions_exact: Tuple[int, int]; tv_target_ratio: float
    feed_target_ratio: float; story_target_ratio: float

@dataclass(frozen=True)
class NamingAndOrganizationConfig:
    sequential_number_padding: int; bebida_keyword: str
    base_type_diaria: str; base_type_multidia: str; base_type_fixo: str
    dropbox_strategies: List[str]; format_folder_tv: str
    format_folder_feed: str; format_folder_story: str

@dataclass(frozen=True)
class VideoConfig:
    elementos_fixos_duration_sec: float; diarias_duration_sec: float
    multi_dias_duration_sec: float; default_transition_effect: str
    default_transition_duration_sec: float; video_codec: str
    video_preset: str; video_framerate: int; audio_codec: str
    audio_bitrate: str; video_crf_tv: int; video_crf_story: int
    video_crf_feed: int; output_video_formats: List[str]

@dataclass(frozen=True)
class CleaningConfig: # Removidas todas as chaves max_days_*
    confirm_before_deletion: bool

@dataclass(frozen=True)
class GeneralConfig:
    log_level: str; archive_date_format: str

@dataclass(frozen=True)
class AppConfig:
    paths: PathsConfig; processing: ProcessingConfig
    naming_and_organization: NamingAndOrganizationConfig
    video: VideoConfig; cleaning: CleaningConfig; general: GeneralConfig

def load_app_config(config_file_path: Path = CONFIG_FILE_PATH) -> AppConfig:
    if not config_file_path.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_file_path}")
    parser = configparser.ConfigParser()
    parser.read(config_file_path, encoding='utf-8')
    cfg = {}
    try:
        cfg['paths'] = PathsConfig(
            downloads_root_path=Path(parser.get('Paths', 'downloads_root_path')),
            dropbox_base_path=Path(parser.get('Paths', 'dropbox_base_path')),
            dropbox_main_offers_folder_name=parser.get('Paths', 'dropbox_main_offers_folder_name'),
            ofertas_multi_dia_folder_name=parser.get('Paths', 'ofertas_multi_dia_folder_name'),
            ofertas_bebidas_folder_name=parser.get('Paths', 'ofertas_bebidas_folder_name'),
            elementos_fixos_folder_name=parser.get('Paths', 'elementos_fixos_folder_name'),
            arquivos_ofertas_root_folder_name=parser.get('Paths', 'arquivos_ofertas_root_folder_name'),
            videos_ofertas_output_folder_name=parser.get('Paths', 'videos_ofertas_output_folder_name'))
        cfg['processing'] = ProcessingConfig(
            qrofertas_keyword=parser.get('Processing', 'qrofertas_keyword'),
            aspect_ratio_tolerance=parser.getfloat('Processing', 'aspect_ratio_tolerance'),
            tv_dimensions_exact=_parse_dimensions(parser.get('Processing', 'tv_dimensions_exact')),
            feed_dimensions_exact=_parse_dimensions(parser.get('Processing', 'feed_dimensions_exact')),
            story_dimensions_exact=_parse_dimensions(parser.get('Processing', 'story_dimensions_exact')),
            tv_target_ratio=parser.getfloat('Processing', 'tv_target_ratio'),
            feed_target_ratio=parser.getfloat('Processing', 'feed_target_ratio'),
            story_target_ratio=parser.getfloat('Processing', 'story_target_ratio'))
        cfg['naming_and_organization'] = NamingAndOrganizationConfig(
            sequential_number_padding=parser.getint('NamingAndOrganization', 'sequential_number_padding'),
            bebida_keyword=parser.get('NamingAndOrganization', 'bebida_keyword'),
            base_type_diaria=parser.get('NamingAndOrganization', 'base_type_diaria'),
            base_type_multidia=parser.get('NamingAndOrganization', 'base_type_multidia'),
            base_type_fixo=parser.get('NamingAndOrganization', 'base_type_fixo'),
            dropbox_strategies=_parse_comma_separated_list(parser.get('NamingAndOrganization', 'dropbox_strategies')),
            format_folder_tv=parser.get('NamingAndOrganization', 'format_folder_tv'),
            format_folder_feed=parser.get('NamingAndOrganization', 'format_folder_feed'),
            format_folder_story=parser.get('NamingAndOrganization', 'format_folder_story'))
        cfg['video'] = VideoConfig(
            elementos_fixos_duration_sec=parser.getfloat('Video', 'elementos_fixos_duration_sec'),
            diarias_duration_sec=parser.getfloat('Video', 'diarias_duration_sec'),
            multi_dias_duration_sec=parser.getfloat('Video', 'multi_dias_duration_sec'),
            default_transition_effect=parser.get('Video', 'default_transition_effect'),
            default_transition_duration_sec=parser.getfloat('Video', 'default_transition_duration_sec'),
            video_codec=parser.get('Video', 'video_codec'),
            video_preset=parser.get('Video', 'video_preset'),
            video_framerate=parser.getint('Video', 'video_framerate'),
            audio_codec=parser.get('Video', 'audio_codec'),
            audio_bitrate=parser.get('Video', 'audio_bitrate'),
            video_crf_tv=parser.getint('Video', 'video_crf_tv'),
            video_crf_story=parser.getint('Video', 'video_crf_story'),
            video_crf_feed=parser.getint('Video', 'video_crf_feed'),
            output_video_formats=_parse_comma_separated_list(parser.get('Video', 'output_video_formats')))
        cfg['cleaning'] = CleaningConfig( # ATUALIZADO
            confirm_before_deletion=parser.getboolean('Cleaning', 'confirm_before_deletion'))
        cfg['general'] = GeneralConfig(
            log_level=parser.get('General', 'log_level'),
            archive_date_format=parser.get('General', 'archive_date_format'))
        return AppConfig(**cfg)
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        raise ValueError(f"Erro ao ler config: {e}")
    except ValueError as e:
        raise ValueError(f"Erro de valor no config: {e}")

if __name__ == "__main__":
    print(f"Carregando config de: {CONFIG_FILE_PATH.resolve()}")
    try:
        config = load_app_config()
        print("\nConfigurações carregadas:")
        print(f"  Paths: {config.paths}")
        print(f"  Processing: {config.processing}")
        print(f"  Naming: {config.naming_and_organization}")
        print(f"  Video: {config.video}")
        print(f"  Cleaning: {config.cleaning}") # Deve mostrar apenas confirm_before_deletion
        print(f"  General: {config.general}")
    except Exception as e:
        print(f"ERRO: {e}")