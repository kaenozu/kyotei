"""
競輪予想CLI インターフェース
"""
import logging
from typing import List, Optional
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.live import Live

from data.models import RaceInfo, RaceDetail, PredictionResult, BetRecommendation
from data.fetcher import KeirinDataFetcher
from prediction.predictor import KeirinPredictor
from config.settings import APP_NAME, APP_VERSION, DISPLAY_CONFIG


class KeirinCLI:
    """競輪予想CLI メインインターフェース"""

    def __init__(self):
        self.console = Console()
        self.fetcher = KeirinDataFetcher()
        self.predictor = KeirinPredictor()
        self.logger = logging.getLogger(__name__)

    def run(self):
        """メインアプリケーションループ"""
        self.console.clear()
        self._show_welcome()
        
        while True:
            try:
                choice = self._show_main_menu()
                
                if choice == "1":
                    self._handle_today_races()
                elif choice == "2":
                    self._handle_tomorrow_races()
                elif choice == "3":
                    self._handle_venue_search()
                elif choice == "4":
                    self._handle_prediction_history()
                elif choice == "5":
                    self._handle_settings()
                elif choice == "6":
                    self._handle_help()
                elif choice == "7":
                    self._show_goodbye()
                    break
                else:
                    self.console.print("[red]無効な選択です。[/red]")
                    
            except KeyboardInterrupt:
                self.console.print("\n[yellow]終了しています...[/yellow]")
                break
            except Exception as e:
                self.logger.error(f"予期しないエラー: {e}")
                self.console.print(f"[red]エラーが発生しました: {e}[/red]")

    def _show_welcome(self):
        """ウェルカムメッセージ表示"""
        welcome_panel = Panel(
            Text(f"🚴 {APP_NAME} v{APP_VERSION}", style="bold blue", justify="center"),
            subtitle="競輪予想システムへようこそ",
            style="blue"
        )
        self.console.print(welcome_panel)
        self.console.print()

    def _show_main_menu(self) -> str:
        """メインメニュー表示（強化版）"""
        # 現在時刻とステータス表示
        now = datetime.now()
        status_panel = Panel(
            f"🗓️  {now.strftime('%Y年%m月%d日 %H:%M')}  |  📊 キャッシュ稼働中  |  🔄 データ自動更新",
            style="dim"
        )
        self.console.print(status_panel)
        self.console.print()
        
        # 強化されたメニュー
        menu_table = Table(show_header=False, box=None, expand=False, pad_edge=False)
        menu_table.add_column(style="bold cyan", width=4)
        menu_table.add_column(style="white", width=20)
        menu_table.add_column(style="dim", width=30)
        
        menu_table.add_row("1.", "📅 本日のレース一覧", "今日開催中のレースを表示")
        menu_table.add_row("2.", "📈 明日のレース一覧", "明日開催予定のレースを表示")
        menu_table.add_row("3.", "🔍 開催場検索", "特定の競輪場からレースを検索")
        menu_table.add_row("4.", "📊 予想履歴", "過去の予想結果を確認")
        menu_table.add_row("5.", "⚙️  設定・管理", "アプリケーション設定とキャッシュ管理")
        menu_table.add_row("6.", "❓ ヘルプ", "使い方とコマンド一覧")
        menu_table.add_row("7.", "❌ 終了", "アプリケーションを終了")
        
        menu_panel = Panel(
            menu_table,
            title="🚴 競輪予想システム - メインメニュー",
            title_align="center",
            border_style="blue"
        )
        
        self.console.print(menu_panel)
        self.console.print()
        
        return Prompt.ask(
            "[bold cyan]選択してください (1-7)[/bold cyan]",
            choices=["1", "2", "3", "4", "5", "6", "7"],
            default="1"
        )

    def _handle_today_races(self):
        """本日のレース処理"""
        self.console.clear()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("本日のレース情報を取得中...", total=None)
            races = self.fetcher.get_today_races()
            progress.remove_task(task)
        
        if not races:
            self.console.print("[red]レース情報の取得に失敗しました。[/red]")
            Prompt.ask("[dim]Enterキーで戻る[/dim]", default="")
            return
        
        self._show_race_list(races, "本日のレース一覧")
        self._interactive_race_selection(races)

    def _handle_tomorrow_races(self):
        """明日のレース処理"""
        self.console.clear()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("明日のレース情報を取得中...", total=None)
            races = self.fetcher.get_tomorrow_races()
            progress.remove_task(task)
        
        if not races:
            self.console.print("[red]明日のレース情報の取得に失敗しました。[/red]")
            Prompt.ask("[dim]Enterキーで戻る[/dim]", default="")
            return
        
        self._show_race_list(races, "明日のレース一覧")
        self._interactive_race_selection(races)

    def _handle_venue_search(self):
        """開催場検索処理"""
        self.console.clear()
        
        # 開催場リストを表示
        venues_table = Table(title="🏟️ 競輪場一覧")
        venues_table.add_column("No.", style="cyan", width=4)
        venues_table.add_column("競輪場", style="yellow", width=12)
        venues_table.add_column("距離", style="green", width=8)
        venues_table.add_column("バンク", style="magenta", width=8)
        venues_table.add_column("特徴", style="blue", width=15)
        
        from config.settings import VENUES
        venue_list = list(VENUES.items())[:10]  # 表示を10件に制限
        
        for i, (venue_name, info) in enumerate(venue_list, 1):
            distance = f"{info.get('distance', 400)}m"
            banking = f"{info.get('banking', 31.5)}°"
            features = "標準バンク"  # 実際の特徴は設定ファイルから取得
            
            venues_table.add_row(
                str(i),
                venue_name,
                distance,
                banking,
                features
            )
        
        self.console.print(venues_table)
        self.console.print()
        
        # 開催場選択
        venue_choice = Prompt.ask(
            "[bold cyan]検索したい競輪場番号を入力してください (0: 戻る)[/bold cyan]",
            choices=[str(i) for i in range(len(venue_list) + 1)],
            default="0"
        )
        
        if venue_choice == "0":
            return
        
        selected_venue = venue_list[int(venue_choice) - 1][0]
        self._search_venue_races(selected_venue)

    def _search_venue_races(self, venue: str):
        """指定開催場のレース検索"""
        self.console.clear()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(f"{venue}のレース情報を検索中...", total=None)
            races = self.fetcher.get_races_by_venue(venue)
            progress.remove_task(task)
        
        if not races:
            self.console.print(f"[red]{venue}のレース情報が見つかりませんでした。[/red]")
            Prompt.ask("[dim]Enterキーで戻る[/dim]", default="")
            return
        
        self._show_race_list(races, f"{venue}のレース一覧")
        self._interactive_race_selection(races)

    def _handle_prediction_history(self):
        """予想履歴処理"""
        self.console.clear()
        
        history_panel = Panel(
            "📊 予想履歴機能は次回アップデートで実装予定です\n\n"
            "実装予定機能:\n"
            "• 過去の予想結果の保存・表示\n"
            "• 的中率・回収率の統計\n"
            "• 予想精度の分析\n"
            "• お気に入り開催場の成績",
            title="予想履歴",
            border_style="yellow"
        )
        self.console.print(history_panel)
        Prompt.ask("[dim]Enterキーで戻る[/dim]", default="")

    def _handle_help(self):
        """ヘルプ処理"""
        self.console.clear()
        
        help_table = Table(title="📖 ヘルプ - 使い方ガイド")
        help_table.add_column("機能", style="cyan", width=15)
        help_table.add_column("説明", style="white", width=35)
        help_table.add_column("操作方法", style="yellow", width=25)
        
        help_table.add_row(
            "本日のレース",
            "当日開催中のレース一覧を表示",
            "メニューから「1」を選択"
        )
        help_table.add_row(
            "明日のレース",
            "翌日開催予定のレース一覧を表示",
            "メニューから「2」を選択"
        )
        help_table.add_row(
            "開催場検索",
            "特定の競輪場のレースを検索",
            "メニューから「3」を選択"
        )
        help_table.add_row(
            "予想実行",
            "選択したレースの予想を実行",
            "レース一覧から番号を選択"
        )
        help_table.add_row(
            "キャッシュ管理",
            "データの確認・削除",
            "設定メニューから操作"
        )
        
        self.console.print(help_table)
        self.console.print()
        
        # コマンドライン版のヘルプ
        cmd_panel = Panel(
            "💻 コマンドライン版の使い方:\n\n"
            "• python main.py test          - サンプルデータでテスト\n"
            "• python main.py predict [ID] - 特定レースの予想\n"
            "• python main.py cache-info   - キャッシュ情報表示\n"
            "• python main.py clear-cache  - キャッシュクリア\n"
            "• python main.py --version    - バージョン表示",
            title="コマンドライン版",
            border_style="green"
        )
        self.console.print(cmd_panel)
        
        Prompt.ask("[dim]Enterキーで戻る[/dim]", default="")

    def _handle_settings(self):
        """設定処理（強化版）"""
        self.console.clear()
        
        while True:
            # 設定メニュー
            settings_menu = Table(show_header=False, box=None, expand=False)
            settings_menu.add_column(style="cyan", width=3)
            settings_menu.add_column(style="white", width=25)
            settings_menu.add_column(style="dim", width=30)
            
            settings_menu.add_row("1.", "📊 キャッシュ情報表示", "現在のキャッシュ状況を確認")
            settings_menu.add_row("2.", "🗑️  キャッシュクリア", "全キャッシュデータを削除")
            settings_menu.add_row("3.", "🧹 期限切れキャッシュ削除", "期限切れデータのみ削除")
            settings_menu.add_row("4.", "⚙️  システム設定表示", "現在の設定値を表示")
            settings_menu.add_row("5.", "🔄 データソース状態", "データ取得先の状態確認")
            settings_menu.add_row("0.", "⬅️  メインメニューに戻る", "")
            
            settings_panel = Panel(
                settings_menu,
                title="⚙️  設定・管理メニュー",
                border_style="yellow"
            )
            
            self.console.print(settings_panel)
            self.console.print()
            
            choice = Prompt.ask(
                "[bold yellow]選択してください (0-5)[/bold yellow]",
                choices=["0", "1", "2", "3", "4", "5"],
                default="0"
            )
            
            if choice == "0":
                break
            elif choice == "1":
                self._show_cache_info()
            elif choice == "2":
                self._clear_all_cache()
            elif choice == "3":
                self._clear_expired_cache()
            elif choice == "4":
                self._show_system_settings()
            elif choice == "5":
                self._show_data_source_status()

    def _show_cache_info(self):
        """キャッシュ情報の詳細表示"""
        from utils.cache import cache
        info = cache.get_cache_info()
        
        cache_panel = Panel(
            f"📊 総エントリ数: {info.get('total_entries', 0)}\n"
            f"✅ 有効エントリ数: {info.get('valid_entries', 0)}\n"
            f"⏰ 期限切れエントリ数: {info.get('expired_entries', 0)}\n\n"
            f"💾 キャッシュファイル: cache/cache.db",
            title="キャッシュ情報",
            border_style="green"
        )
        self.console.print(cache_panel)
        Prompt.ask("[dim]Enterキーで続行[/dim]", default="")

    def _clear_all_cache(self):
        """全キャッシュクリア"""
        if Confirm.ask("🗑️  全キャッシュを削除しますか？"):
            from utils.cache import cache
            cache.clear_all()
            self.console.print("[green]✅ 全キャッシュを削除しました。[/green]")
        else:
            self.console.print("[yellow]キャンセルしました。[/yellow]")
        Prompt.ask("[dim]Enterキーで続行[/dim]", default="")

    def _clear_expired_cache(self):
        """期限切れキャッシュクリア"""
        from utils.cache import cache
        cache.clear_expired()
        self.console.print("[green]✅ 期限切れキャッシュを削除しました。[/green]")
        Prompt.ask("[dim]Enterキーで続行[/dim]", default="")

    def _show_system_settings(self):
        """システム設定表示"""
        from config.settings import PREDICTION_WEIGHTS, SCRAPING_CONFIG, CACHE_DURATION
        
        # 予想アルゴリズム設定
        weights_table = Table(title="🎯 予想アルゴリズム重み設定")
        weights_table.add_column("評価項目", style="cyan")
        weights_table.add_column("重み", style="yellow")
        weights_table.add_column("説明", style="white")
        
        weights_table.add_row("選手能力", f"{PREDICTION_WEIGHTS['rider_ability']:.1%}", "級班・勝率・年齢")
        weights_table.add_row("近況フォーム", f"{PREDICTION_WEIGHTS['recent_form']:.1%}", "直近成績・トレンド")
        weights_table.add_row("バンク相性", f"{PREDICTION_WEIGHTS['track_compatibility']:.1%}", "開催場での成績")
        weights_table.add_row("ライン戦略", f"{PREDICTION_WEIGHTS['line_strategy']:.1%}", "ライン形成・役割")
        weights_table.add_row("外部要因", f"{PREDICTION_WEIGHTS['external_factors']:.1%}", "天候・オッズ・風")
        
        self.console.print(weights_table)
        self.console.print()
        
        # スクレイピング設定
        scraping_panel = Panel(
            f"⏱️  レート制限: {SCRAPING_CONFIG['rate_limit']}秒間隔\n"
            f"⏰ タイムアウト: {SCRAPING_CONFIG['timeout']}秒\n"
            f"🔄 最大リトライ: {SCRAPING_CONFIG['max_retries']}回",
            title="🌐 データ取得設定",
            border_style="blue"
        )
        self.console.print(scraping_panel)
        Prompt.ask("[dim]Enterキーで続行[/dim]", default="")

    def _show_data_source_status(self):
        """データソース状態表示"""
        from config.settings import DATA_SOURCES
        
        source_table = Table(title="🌐 データソース状態")
        source_table.add_column("ソース", style="cyan")
        source_table.add_column("URL", style="yellow")
        source_table.add_column("状態", style="green")
        
        for name, url in DATA_SOURCES.items():
            status = "🟢 設定済み" if url else "🔴 未設定"
            source_table.add_row(name, url, status)
        
        self.console.print(source_table)
        Prompt.ask("[dim]Enterキーで続行[/dim]", default="")

    def _show_race_list(self, races: List[RaceInfo], title: str):
        """レース一覧をテーブル表示"""
        table = Table(title=f"📋 {title}")
        table.add_column("No.", style="cyan", width=4)
        table.add_column("開催場", style="yellow", width=8)
        table.add_column("R", style="white", width=3)
        table.add_column("発走時刻", style="green", width=8)
        table.add_column("グレード", style="magenta", width=8)
        table.add_column("賞金", style="red", width=8)
        table.add_column("状態", style="blue", width=8)
        
        for i, race in enumerate(races[:DISPLAY_CONFIG['max_races_per_page']], 1):
            # グレードによる色分け
            grade_color = self._get_grade_color(race.grade.value)
            
            # レース状態の判定
            status = self._get_race_status(race.start_time)
            status_color = "green" if status == "発売中" else "gray"
            
            table.add_row(
                str(i),
                race.venue,
                str(race.race_number),
                race.start_time.strftime("%H:%M"),
                Text(race.grade.value, style=grade_color),
                f"{race.prize_money:,}万",
                Text(status, style=status_color)
            )
        
        self.console.print(table)
        self.console.print()

    def _interactive_race_selection(self, races: List[RaceInfo]):
        """インタラクティブなレース選択"""
        while True:
            choice = Prompt.ask(
                "\n[bold cyan]予想したいレース番号を入力してください (0: 戻る)[/bold cyan]",
                choices=[str(i) for i in range(len(races) + 1)],
                default="0"
            )
            
            if choice == "0":
                break
            
            selected_race = races[int(choice) - 1]
            
            # 予想実行確認
            if Confirm.ask(f"\n{selected_race.venue}{selected_race.race_number}Rの予想を実行しますか？"):
                self._execute_prediction(selected_race)
                
                # 次の操作選択
                next_choice = Prompt.ask(
                    "\n[bold green]次の操作を選択してください[/bold green]",
                    choices=["1", "2", "3"],
                    default="1"
                )
                
                if next_choice == "1":  # 他のレースを見る
                    self.console.clear()
                    self._show_race_list(races, "本日のレース一覧")
                    continue
                elif next_choice == "2":  # メインメニューに戻る
                    break
                else:  # 終了
                    self._show_goodbye()
                    exit()

    def _execute_prediction(self, race_info: RaceInfo):
        """予想実行"""
        self.console.clear()
        
        # レース詳細取得
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("レース詳細情報を取得中...", total=None)
            race_detail = self.fetcher.get_race_details(race_info.race_id)
            progress.remove_task(task)
            
            if not race_detail:
                self.console.print("[red]レース詳細の取得に失敗しました。[/red]")
                return
            
            task = progress.add_task("予想計算中...", total=None)
            prediction = self.predictor.predict_race(race_detail)
            progress.remove_task(task)
        
        # 予想結果表示
        self._show_prediction_result(prediction, race_detail)

    def _show_prediction_result(self, prediction: PredictionResult, race: RaceDetail):
        """予想結果の詳細表示"""
        self.console.clear()
        
        # レース情報ヘッダー
        race_info = Panel(
            f"🏟️ {race.race_info.venue} {race.race_info.race_number}R  "
            f"🕐 {race.race_info.start_time.strftime('%H:%M')}  "
            f"🏆 {race.race_info.grade.value}  💰 {race.race_info.prize_money:,}万円",
            title="レース情報",
            style="blue"
        )
        self.console.print(race_info)
        self.console.print()
        
        # 選手予想テーブル
        riders_table = Table(title="🔮 予想結果")
        riders_table.add_column("車番", style="cyan", width=4)
        riders_table.add_column("選手名", style="yellow", width=12)
        riders_table.add_column("年齢", style="white", width=4)
        riders_table.add_column("級班", style="magenta", width=4)
        riders_table.add_column("勝率", style="green", width=6)
        riders_table.add_column("連対率", style="green", width=8)
        riders_table.add_column("予想順位", style="red", width=8)
        riders_table.add_column("推奨度", style="bold red", width=6)
        
        for rank, rider_num in enumerate(prediction.rankings, 1):
            rider = race.get_rider_by_number(rider_num)
            if not rider:
                continue
            
            score = prediction.scores[rider_num]
            
            # 推奨度による★表示
            stars = self._get_recommendation_stars(score.total_score)
            recommendation = self._get_recommendation_grade(score.total_score)
            
            win_rate = rider.stats.win_rate if rider.stats else 0.0
            place_rate = rider.stats.place_rate if rider.stats else 0.0
            
            riders_table.add_row(
                str(rider.number),
                rider.name,
                str(rider.age),
                rider.class_rank.value,
                f"{win_rate:.2f}",
                f"{place_rate:.2f}",
                f"{rank}位 {stars}",
                Text(recommendation, style=self._get_recommendation_color(recommendation))
            )
        
        self.console.print(riders_table)
        self.console.print()
        
        # 買い目推奨表示
        if prediction.betting_recommendations:
            self._show_betting_recommendations(prediction.betting_recommendations)
        
        # 信頼度表示
        confidence_panel = Panel(
            f"予想信頼度: {prediction.confidence:.1%}",
            title="信頼度",
            style="green" if prediction.confidence > 0.7 else "yellow"
        )
        self.console.print(confidence_panel)
        
        Prompt.ask("\n[dim]Enterキーで続行[/dim]", default="")

    def _show_betting_recommendations(self, recommendations: List[BetRecommendation]):
        """買い目推奨を表示"""
        betting_table = Table(title="💡 おすすめ買い目", box=None)
        betting_table.add_column("券種", style="cyan", width=10)
        betting_table.add_column("買い目", style="yellow", width=15)
        betting_table.add_column("予想オッズ", style="green", width=10)
        betting_table.add_column("信頼度", style="red", width=8)
        betting_table.add_column("期待値", style="magenta", width=8)
        
        for rec in recommendations:
            confidence_color = {
                'S': 'bold red',
                'A': 'red',
                'B': 'yellow',
                'C': 'white'
            }.get(rec.confidence, 'white')
            
            betting_table.add_row(
                rec.bet_type,
                rec.combination,
                f"{rec.expected_odds:.1f}倍",
                Text(rec.confidence, style=confidence_color),
                f"{rec.expected_value:+.1f}%"
            )
        
        self.console.print(betting_table)
        self.console.print()

    def _show_settings(self):
        """設定画面表示"""
        settings_table = Table(title="⚙️ システム設定")
        settings_table.add_column("項目", style="cyan", width=20)
        settings_table.add_column("現在値", style="yellow", width=15)
        settings_table.add_column("説明", style="white", width=30)
        
        settings_table.add_row("予想アルゴリズム", "総合型", "選手能力重視 / 近況重視 / 総合型")
        settings_table.add_row("データ更新間隔", "30分", "自動データ更新の間隔")
        settings_table.add_row("表示レース数", f"{DISPLAY_CONFIG['max_races_per_page']}件", "一覧で表示する最大レース数")
        settings_table.add_row("推奨度表示", "★5段階", "★5段階 / S-D評価 / 数値")
        
        self.console.print(settings_table)

    def _show_goodbye(self):
        """終了メッセージ"""
        goodbye_panel = Panel(
            Text("ご利用ありがとうございました！", style="bold blue", justify="center"),
            style="blue"
        )
        self.console.print("\n")
        self.console.print(goodbye_panel)

    def _get_grade_color(self, grade: str) -> str:
        """グレードによる色を取得"""
        color_map = {
            "GP": "bold red",
            "G1": "red",
            "G2": "magenta",
            "G3": "blue",
            "F1": "green",
            "F2": "white"
        }
        return color_map.get(grade, "white")

    def _get_race_status(self, start_time: datetime) -> str:
        """レース状態を判定"""
        now = datetime.now()
        if start_time > now:
            return "発売中"
        else:
            return "終了"

    def _get_recommendation_stars(self, score: float) -> str:
        """スコアから★表示を生成"""
        if score >= 90:
            return "★★★★★"
        elif score >= 80:
            return "★★★★"
        elif score >= 70:
            return "★★★"
        elif score >= 60:
            return "★★"
        else:
            return "★"

    def _get_recommendation_grade(self, score: float) -> str:
        """スコアから推奨度グレードを取得"""
        if score >= 90:
            return "S"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        else:
            return "D"

    def _get_recommendation_color(self, grade: str) -> str:
        """推奨度による色を取得"""
        color_map = {
            "S": "bold red",
            "A": "red",
            "B": "yellow",
            "C": "white",
            "D": "dim white"
        }
        return color_map.get(grade, "white")