#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
競艇予想アプリケーション メインエントリーポイント
"""
import sys
import os
import logging
import click
from pathlib import Path

# Windows環境での文字化け対策
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from interface.cli import KyoteiCLI
from config.settings import ensure_directories, APP_NAME, APP_VERSION, load_settings, save_settings
from utils.cache import cache
from utils.performance import start_performance_monitoring, stop_performance_monitoring, get_performance_summary
from utils.logger import setup_logger # setup_loggerをインポート


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='バージョン情報を表示')
@click.option('--debug', is_flag=True, help='デバッグモードで実行')
@click.pass_context
def main(ctx, version, debug):
    """競艇予想CLI アプリケーション"""
    
    if version:
        click.echo(f"{APP_NAME} v{APP_VERSION}")
        return
    
    # コマンドが指定されていない場合はCLIを起動
    if ctx.invoked_subcommand is None:
        logger = None
        try:
            ensure_directories()
            load_settings() # 設定をロード
            
            # デバッグモードが有効な場合はLOG_CONFIGのdebug_modeをTrueに設定
            if debug:
                from config.settings import LOG_CONFIG # LOG_CONFIGを一時的にインポート
                LOG_CONFIG["debug_mode"] = True
            
            # ログ設定を簡略化
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('kyotei.log', encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
            logger = logging.getLogger(__name__)
            logger.info(f"{APP_NAME} v{APP_VERSION} 起動")
            
            # 外部ライブラリのログレベルを調整
            logging.getLogger("requests").setLevel(logging.WARNING)
            logging.getLogger("urllib3").setLevel(logging.WARNING)
            
            # パフォーマンス監視開始
            start_performance_monitoring()
            logger.info("パフォーマンス監視を開始しました")
            
            # CLIアプリケーション起動
            app = KyoteiCLI()
            app.run()
            
            logger.info("アプリケーション終了")
            
        except KeyboardInterrupt:
            click.echo("\n終了しました。" )
        except Exception as e:
            if logger:
                logger.error(f"エラーが発生しました: {e}")
            click.echo(f"エラーが発生しました: {e}", err=True)
            if debug:
                raise
        finally:
            # パフォーマンス監視停止
            try:
                stop_performance_monitoring()
                # 最終パフォーマンス要約を表示
                summary = get_performance_summary()
                if logger:
                    logger.info(f"パフォーマンス要約:\n{summary}")
            except Exception as e:
                if logger:
                    logger.error(f"パフォーマンス監視停止エラー: {e}")
            save_settings() # 設定を保存



@main.command()
@click.argument('race_id', required=False)
def predict(race_id):
    """特定レースの予想を実行"""
    logger = logging.getLogger(__name__)
    
    if not race_id:
        click.echo("レースIDが必要です。例: python kyotei.py predict 20241205_平塚_01")
        return
    
    try:
        from data.fetcher import KyoteiDataFetcher
        from prediction.predictor import KyoteiPredictor
        
        fetcher = KyoteiDataFetcher()
        predictor = KyoteiPredictor()
        
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
            
        for i, racer_num in enumerate(prediction.rankings[:3], 1):
            racer = race_detail.get_racer_by_number(racer_num)
            if racer:
                score = prediction.scores[racer_num]
                click.echo(f"{i}位: {racer_num}番 {racer.name} (スコア: {score.total_score:.1f})")
            else:
                click.echo(f"{i}位: {racer_num}番 (選手情報なし)")
        
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
def real_test():
    """実データ取得テスト """
    logger = logging.getLogger(__name__)
    
    try:
        from data.fetcher import KyoteiDataFetcher
        
        # データ取得テスト
        fetcher = KyoteiDataFetcher()
        click.echo("実データ取得中...")
        
        races = fetcher.get_today_races()
        
        if races:
            click.echo(f"\n✅ 実データ取得成功: {len(races)}件")
            
            click.echo("\n=== 取得レース情報 ===")
            for i, race in enumerate(races[:10], 1):  # 最初の10件表示
                click.echo(f"{i}. {race.venue} {race.race_number}R - {race.start_time.strftime('%H:%M')} ({race.status})")
            
            if len(races) > 10:
                click.echo(f"... 他 {len(races) - 10}件")
        else:
            click.echo("❌ データが取得できませんでした")
            
    except Exception as e:
        logger.error(f"実データテストエラー: {e}")
        click.echo(f"エラー: {e}", err=True)


@main.command()
def test():
    """サンプルデータでテスト実行"""
    logger = logging.getLogger(__name__)
    
    try:
        from data.models import create_sample_race
        from prediction.predictor import KyoteiPredictor
        
        # パフォーマンス監視開始
        start_performance_monitoring()
        
        # サンプルレース作成
        sample_race = create_sample_race()
        predictor = KyoteiPredictor()
        
        click.echo("サンプルレースで予想テスト中...")
        prediction = predictor.predict_race(sample_race)
        
        click.echo("\n=== テスト結果 ===")
        click.echo(f"レース: {sample_race.race_info.venue} {sample_race.race_info.race_number}R")
        
        for i, racer_num in enumerate(prediction.rankings[:3], 1):
            racer = sample_race.get_racer_by_number(racer_num)
            score = prediction.scores[racer_num]
            click.echo(f"{i}位: {racer_num}番 {racer.name} (スコア: {score.total_score:.1f})")
        
        click.echo(f"信頼度: {prediction.confidence:.1%}")
        
        # パフォーマンス情報表示
        import time
        time.sleep(2)  # メトリクス収集のため少し待機
        summary = get_performance_summary()
        click.echo(f"\n=== パフォーマンス情報 ===\n{summary}")
        
        click.echo("テスト完了！")
        
    except Exception as e:
        logger.error(f"テスト実行エラー: {e}")
        click.echo(f"テスト実行中にエラーが発生しました: {e}", err=True)
    finally:
        stop_performance_monitoring()


@main.command()
def performance():
    """パフォーマンス情報を表示"""
    try:
        from utils.performance import performance_monitor, ResourceMonitor
        
        # システム情報
        system_info = ResourceMonitor.get_system_info()
        click.echo("=== システム情報 ===")
        click.echo(f"CPU: {system_info.get('cpu', {}).get('count', 0)}コア ({system_info.get('cpu', {}).get('usage_percent', 0):.1f}%)")
        click.echo(f"メモリ: {system_info.get('memory', {}).get('used_mb', 0):.1f}MB / {system_info.get('memory', {}).get('total_mb', 0):.1f}MB")
        click.echo(f"ディスク: {system_info.get('disk', {}).get('used_gb', 0):.1f}GB / {system_info.get('disk', {}).get('total_gb', 0):.1f}GB")
        
        # キャッシュ情報
        cache_info = cache.get_cache_info()
        click.echo("\n=== キャッシュ情報 ===")
        click.echo(f"総エントリ数: {cache_info.get('total_entries', 0)}")
        click.echo(f"有効エントリ数: {cache_info.get('valid_entries', 0)}")
        click.echo(f"ヒット率: {cache_info.get('hit_rate', 0):.1%}")
        click.echo(f"L1キャッシュ: {cache_info.get('l1_cache_entries', 0)}件")
        
        # パフォーマンスレポート
        if hasattr(performance_monitor, 'get_performance_report'):
            report = performance_monitor.get_performance_report(minutes=1)
            if "error" not in report:
                click.echo("\n=== パフォーマンスレポート ===")
                click.echo(f"サンプル数: {report.get('sample_count', 0)}件")
                if report.get('operation_stats'):
                    click.echo("操作別統計:")
                    for op, stats in report['operation_stats'].items():
                        click.echo(f"  {op}: {stats['avg_ms']:.1f}ms (実行{stats['count']}回)")
        
        # リソースヘルスチェック
        health = ResourceMonitor.check_resource_limits()
        click.echo("\n=== リソースヘルスチェック ===")
        click.echo(f"CPU: {'✅' if health.get('cpu_healthy', False) else '⚠️'} 正常" if health.get('cpu_healthy', False) else "CPU: ⚠️ 高負荷")
        click.echo(f"メモリ: {'✅' if health.get('memory_healthy', False) else '⚠️'} 正常" if health.get('memory_healthy', False) else "メモリ: ⚠️ 高使用率")
        click.echo(f"ディスク: {'✅' if health.get('disk_healthy', False) else '⚠️'} 正常" if health.get('disk_healthy', False) else "ディスク: ⚠️ 容量不足")
        click.echo(f"総合: {'✅ システム正常' if health.get('overall_healthy', False) else '⚠️ 注意が必要'}")
        
    except Exception as e:
        click.echo(f"パフォーマンス情報取得エラー: {e}", err=True)


if __name__ == "__main__":
    main()
