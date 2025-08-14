import argparse
import sys
import logging
from typing import List, Callable, Dict, Any
from pathlib import Path

from config import AppConfig, load_app_config, CONFIG_FILE_PATH
from core import image_processor
from core import video_creator
from core import file_manager


def process_offers_command(config: AppConfig, args: argparse.Namespace) -> None:
    logging.info(f"Comando 'processar' com estratégia: {args.estrategia_dropbox}")
    try:
        processed_results = image_processor.process_images(config, args.estrategia_dropbox, args.dry_run)
        if processed_results: logging.info(f"{len(processed_results)} ofertas processadas/simuladas.")
        else: logging.info("Nenhuma oferta processada/encontrada.")
    except Exception as e: logging.error(f"Erro processar ofertas: {e}", exc_info=args.verbose); raise

def create_videos_command(config: AppConfig, args: argparse.Namespace) -> None:
    logging.info("Comando 'criar_videos'.")
    try:
        success = video_creator.create_videos(config, args.dry_run)
        if success: logging.info("Criação de vídeos concluída/simulada.")
        else: logging.warning("Criação de vídeos com problemas.")
    except Exception as e: logging.error(f"Erro criar vídeos: {e}", exc_info=args.verbose); raise

def clean_system_command(config: AppConfig, args: argparse.Namespace) -> None:
    logging.info(f"Comando 'limpar': '{args.tipo_limpeza}', Dry run: {args.dry_run}")
    items_affected = 0
    try:
        if args.tipo_limpeza == "limpar_diarias":
            items_affected = file_manager.clean_diarias_comprehensive(config, args.dry_run)
        elif args.tipo_limpeza == "limpar_multidias":
            items_affected = file_manager.clean_multidia_comprehensive(config, args.dry_run)
        elif args.tipo_limpeza == "limpar_elementos_fixos":
            items_affected = file_manager.clean_fixos_comprehensive(config, args.dry_run)
        elif args.tipo_limpeza == "limpar_tudo":
            items_affected = file_manager.clean_all_tracked_items(config, args.dry_run)
        else: logging.error(f"Tipo limpeza desconhecido: {args.tipo_limpeza}"); return
        verb = "seriam afetados" if args.dry_run else "afetados"
        logging.info(f"Limpeza '{args.tipo_limpeza}' concluída. {items_affected} itens/pastas {verb}.")
    except Exception as e: logging.error(f"Erro limpeza '{args.tipo_limpeza}': {e}", exc_info=args.verbose); raise

def setup_logging(log_level_str: str, verbose: bool) -> None:
    level = logging.DEBUG if verbose else getattr(logging, log_level_str.upper(), logging.INFO)
    for handler in logging.root.handlers[:]: logging.root.removeHandler(handler)
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S", stream=sys.stdout)
    if verbose: logging.info("Logging DEBUG (verbose mode).")

def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Sistema de Processamento de Ofertas.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Saída detalhada.")
    parser.add_argument("--dry-run", action="store_true", help="Modo de simulação.")
    parser.add_argument("--config-file", type=str, default=None, help=f"Config alternativo (padrão: {CONFIG_FILE_PATH.name}).")
    subparsers = parser.add_subparsers(dest="command", title="Comandos", required=True)
    p_proc = subparsers.add_parser("processar", help="Processa imagens."); p_proc.add_argument("estrategia_dropbox", type=str, help="Estratégia Dropbox."); p_proc.set_defaults(func=process_offers_command)
    p_video = subparsers.add_parser("criar_videos", help="Gera vídeos."); p_video.set_defaults(func=create_videos_command)
    p_clean = subparsers.add_parser("limpar", help="Limpeza."); p_clean.add_argument("tipo_limpeza", type=str, choices=["limpar_diarias", "limpar_multidias", "limpar_elementos_fixos", "limpar_tudo"], help="Tipo de limpeza."); p_clean.set_defaults(func=clean_system_command)
    args = parser.parse_args(argv)
    try:
        cfg_path = Path(args.config_file).resolve() if args.config_file else CONFIG_FILE_PATH.resolve()
        app_config = load_app_config(cfg_path)
    except (FileNotFoundError, ValueError) as e: print(f"ERRO CRÍTICO config '{cfg_path}': {e}", file=sys.stderr); sys.exit(1)
    setup_logging(app_config.general.log_level, args.verbose)
    logging.info(f"Sistema iniciado. Cmd: {args.command}, Dry-run: {args.dry_run}, Config: {cfg_path}")
    if hasattr(args, 'func'):
        try: args.func(app_config, args); logging.info(f"Cmd '{args.command}' OK.")
        except Exception: logging.critical(f"Falha Cmd '{args.command}'.", exc_info=args.verbose); sys.exit(1)
    else: parser.print_help(); sys.exit(1)

if __name__ == "__main__":
    main()