#!/usr/bin/env python3
"""
競輪予想アプリケーション メインエントリーポイント
"""
import sys
import logging
import click
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from interface.cli import KeirinCLI
from config.settings import ensure_directories, LOG_CONFIG, APP_NAME, APP_VERSION
from utils.cache import cache


def setup_logging():
    """ログ設定を初期化"""
    ensure_directories()
    
    log_file = project_root / "logs" / "keirin.log"
    
    logging.basicConfig(
        level=getattr(logging, LOG_CONFIG['level']),
        format=LOG_CONFIG['format'],
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 外部ライブラリのログレベルを調整
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='バージョン情報を表示')
@click.option('--debug', is_flag=True, help='デバッグモードで実行')
@click.pass_context
def main(ctx, version, debug):
    """競輪予想CLI アプリケーション"""
    
    if version:
        click.echo(f"{APP_NAME} v{APP_VERSION}")
        return
    
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        click.echo("デバッグモードで起動しました")
    
    # コマンドが指定されていない場合はCLIを起動
    if ctx.invoked_subcommand is None:
        try:
            setup_logging()
            logger = logging.getLogger(__name__)
            logger.info(f"{APP_NAME} v{APP_VERSION} 起動")
            
            # CLIアプリケーション起動
            app = KeirinCLI()
            app.run()
            
            logger.info("アプリケーション終了")
            
        except KeyboardInterrupt:
            click.echo("\n終了しました。")
        except Exception as e:
            click.echo(f"エラーが発生しました: {e}", err=True)
            if debug:
                raise


@main.command()
@click.argument('race_id', required=False)
def predict(race_id):
    """特定レースの予想を実行"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    if not race_id:
        click.echo("レースIDが必要です。例: python main.py predict 20241205_平塚_01")
        return
    
    try:
        from data.fetcher import KeirinDataFetcher
        from prediction.predictor import KeirinPredictor
        
        fetcher = KeirinDataFetcher()
        predictor = KeirinPredictor()
        
        # レース詳細取得
        click.echo(f"レース詳細を取得中: {race_id}")
        race_detail = fetcher.get_race_details(race_id)
        
        if not race_detail:
            click.echo("レース詳細の取得に失敗しました。", err=True)
            return
        
        # 予想実行
        click.echo("予想計算中...")
        prediction = predictor.predict_race(race_detail)
        
        # 結果表示
        click.echo(f"\n=== {race_detail.race_info.venue} {race_detail.race_info.race_number}R 予想結果 ===")
        
        if not prediction.rankings:
            click.echo("予想結果が生成されませんでした。", err=True)
            return
            
        for i, rider_num in enumerate(prediction.rankings[:3], 1):
            rider = race_detail.get_rider_by_number(rider_num)
            if rider:
                score = prediction.scores[rider_num]
                click.echo(f"{i}位: {rider_num}番 {rider.name} (スコア: {score.total_score:.1f})")
            else:
                click.echo(f"{i}位: {rider_num}番 (選手情報なし)")
        
        click.echo(f"\n信頼度: {prediction.confidence:.1%}")
        
        if prediction.betting_recommendations:
            click.echo("\n=== おすすめ買い目 ===")
            for rec in prediction.betting_recommendations:
                click.echo(f"{rec.bet_type}: {rec.combination} (オッズ: {rec.expected_odds:.1f}倍, 信頼度: {rec.confidence})")
        
    except Exception as e:
        logger.error(f"予想実行エラー: {e}")
        click.echo(f"予想実行中にエラーが発生しました: {e}", err=True)


@main.command()
def cache_info():
    """キャッシュ情報を表示"""
    info = cache.get_cache_info()
    click.echo("=== キャッシュ情報 ===")
    click.echo(f"総エントリ数: {info.get('total_entries', 0)}")
    click.echo(f"有効エントリ数: {info.get('valid_entries', 0)}")
    click.echo(f"期限切れエントリ数: {info.get('expired_entries', 0)}")


@main.command()
@click.confirmation_option(prompt='全キャッシュを削除しますか？')
def clear_cache():
    """全キャッシュを削除"""
    cache.clear_all()
    click.echo("キャッシュを削除しました。")


@main.command()
def cleanup():
    """期限切れキャッシュを削除"""
    cache.clear_expired()
    click.echo("期限切れキャッシュを削除しました。")


@main.command()
def test():
    """サンプルデータでテスト実行"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        from data.models import create_sample_race
        from prediction.predictor import KeirinPredictor
        
        # サンプルレース作成
        sample_race = create_sample_race()
        predictor = KeirinPredictor()
        
        click.echo("サンプルレースで予想テスト中...")
        prediction = predictor.predict_race(sample_race)
        
        click.echo("\n=== テスト結果 ===")
        click.echo(f"レース: {sample_race.race_info.venue} {sample_race.race_info.race_number}R")
        
        for i, rider_num in enumerate(prediction.rankings[:3], 1):
            rider = sample_race.get_rider_by_number(rider_num)
            score = prediction.scores[rider_num]
            click.echo(f"{i}位: {rider_num}番 {rider.name} (スコア: {score.total_score:.1f})")
        
        click.echo(f"信頼度: {prediction.confidence:.1%}")
        click.echo("テスト完了！")
        
    except Exception as e:
        logger.error(f"テスト実行エラー: {e}")
        click.echo(f"テスト実行中にエラーが発生しました: {e}", err=True)


if __name__ == "__main__":
    main()