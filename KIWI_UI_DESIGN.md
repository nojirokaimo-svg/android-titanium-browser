# Kiwi UI → Titanium 移植設計・Sol引継ぎ

作成日: 2026-09-05。状態: 設計段階。APK未生成、Androidコンパイル・端末動作未検証。今回の指示に従い実装変更を停止した。本書はモデル名の実行証明ではない。

## 1. 結論と調査範囲

Titaniumの現行Chromiumと拡張機能基盤を維持し、その上にKiwiの画面構成・操作・設定を再実装する。旧KiwiのJava/C++をディレクトリ単位で上書きする方法は採用しない。メニュー生成方式、拡張機能の所有関係、タブ一覧、レンダラーの暗色化設定に大きな世代差がある。

全体構造を対象に、公開Kiwiアーカイブのファイル一覧と独自設定の参照を横断検索し、Titaniumのビルド・パッチ・サブモジュール・拡張機能同梱処理を確認した。Chromiumは全ツリーのファイル索引とAndroid UI等の部分チェックアウトを使用。主要な呼出経路を読んだが、Chromium全ファイルの全行を精読したわけではなく、全依存取得や全パッチ適用も未実施。以下では確認済み事項と提案・未確定事項を区別する。

参照点:

| 対象 | 固定参照 | 用途 |
|---|---|---|
| Titanium | v152.0.7977.64 / 80ffcdf1cebe51cddc593f571a6f26c3374aea2e | 今回の移植ベース |
| Chromium | 152.0.7977.64 / 506c834ecceaa943c5f41e6cfe7f68acb5c45346 | 現行API確認 |
| Vanadium | 150a27e23302cc265baf8a7fb7c0f0112bddf2fd | Titanium指定のサブモジュール |
| Kiwi | src.next-14310011181.zip / 同名リリースタグ | 旧UI・挙動の参照 |
| 旧試作品 | Titanium-Kiwi-Port-v1.4 | 過去失敗の分析のみ |

以前共有されたKiwi/Titaniumスクリーンショットも取得・目視済み。ファイル名だけで判定せず、実際の画面を基準にする。Kiwiと名付けられた画像の一部にはTitaniumの拡張機能画面が写っていた。

Kiwiアーカイブには古いバージョン定数が混在する。リリース表示・ユーザーエージェント・定数のいずれか一つから実際のエンジン版を断定しない。また、main_preferences.xmlから参照するToolbarSettings、NightModeSettingsのクラス定義が取得済みアーカイブには見当たらない。原典の完全性と最終APKとの一致は未確定である。欠落部は公開履歴または最終APKとの照合対象とし、想像で「移植済み」にしない。

## 2. 「完全移植」の受入範囲

完成条件は黒いメニューが出ることではなく、対象画面と操作の対応表を埋めること。以下の段階完了を全体完成と呼ばない。

| UI領域 | 必要な挙動・外観 | 今回の状態 |
|---|---|---|
| 通常メニュー | 上部5操作、アイコン付き縦メニュー、順序、区切り、寸法、スクロール | 原典と現行生成経路を確認、試作あり |
| 拡張機能行 | 名前・カラーアイコン・バッジ・クリック・権限・シークレット・表示順 | 現行接続方式を設計、未実機確認 |
| 拡張機能管理 | 管理画面への直接導線、一覧、詳細、設定、追加・削除 | 既存WebUIを基盤として外観調整 |
| ツールバー | 上下配置、URL欄、メニュー・タブ・ショートカット、IMEとの関係 | 現行上下配置機構を確認 |
| タブ一覧 | グリッド、配色、カード寸法、閉じる・復元・グループ | 既存グリッドを基盤にする設計 |
| タブ表示方式の設定 | Kiwiのdefault/original/horizontal/classic/list/grid | 旧モード全ての現行同等物は未確定 |
| 設定画面 | カテゴリー順、アイコン、テーマ、タブ、ツールバー、アクセシビリティ | 原典XMLと設定キーを確認 |
| ナイトモード | グローバルON/OFF、サイト例外、6プリセット、画像・文字の変換 | ON/OFF試作あり。6種類は追加設計が必要 |
| その他の画面 | 新規タブ、履歴、ブックマーク、ダウンロード、共有・長押し、権限ダイアログ、DevTools、終了 | 全体完成前に画面別差分調査が必要 |

初期テスト対象はarm64のAndroidスマートフォン。通常/シークレット、明/暗、縦/横、大文字設定を含める。タブレット・分割画面を壊さない。Kiwiスクリーンショットの画素数をそのままdp値と見なさず、基準端末の密度・文字倍率・ナビゲーション方式をそろえて比較する。

## 3. アーキテクチャと変更境界

ビルドの関係は Chromium固定版 → Titanium仕様で選別・名称置換したVanadiumパッチ → gclient依存・サブプロジェクトパッチ・同梱拡張 → Titanium patch.sh → Kiwi UIパッチ → GN生成 → コンパイル → 署名。

UIは現行のTab/Profile/WebContentsとCoordinatorを使用する。旧Kiwiの拡張機能エンジン・タブ永続化・プロファイル管理を持ち込まない。新規機能は小さなポリシー/設定クラスに分け、ChromeTabbedActivityや共通色ユーティリティへの巨大な条件分岐を避ける。

提案する責務分離（クラス名は新規設計名であり、既存実装と混同しない）:

| 新規責務 | 入力 | 出力/所有関係 |
|---|---|---|
| KiwiMenuPolicy | 画面種別、Tab、設定、利用可能機能 | 行の順序と表示条件。実行やJNIを所有しない |
| KiwiExtensionMenuAdapter | 既存ExtensionsToolbarCoordinator | メニュー行のスナップショットと実行要求。独自native bridgeを作らない |
| KiwiAppearanceSettings | 登録済み設定キー | テーマ、メニュー順序、タブ外観。Activityの寿命を所有しない |
| KiwiNightModeController | UIテーマ、サイト例外、プリセット | 現行の暗色化状態と、別途設計するレンダラー設定の整合 |

初期値は参照画面に合わせて上部ツールバー・拡張機能を上方に表示。Kiwi原典ではshow_extensions_firstの既定値がfalseなので、原典既定値とユーザーの画面状態を区別する。初期値の変更は明記する。

## 4. 変更箇所と依存関係

以下のパスは各ソースルートからの相対パス。末尾のクラス名だけを検索して別モジュールを修正しない。

### 4.1 メニュー

Kiwi側: `chrome/android/java/src/org/chromium/chrome/browser/app/appmenu/AppMenuPropertiesDelegateImpl.java` のgetMenuItems / prepareExtensionMenu。旧実装はXMLのMenuItemからPropertyModelへ変換し、show_extensions_firstに応じて5アイコン行の直後へ拡張行を追加する。

Titanium側の主変更先:

- `chrome/android/java/src/org/chromium/chrome/browser/tabbed_mode/TabbedAppMenuPropertiesDelegate.java`
- `chrome/android/java/src/org/chromium/chrome/browser/ChromeTabbedActivity.java`
- `chrome/browser/ui/android/appmenu/internal/java/src/org/chromium/chrome/browser/ui/appmenu/AppMenu.java`
- 同appmenuモジュールのAppMenuHandlerImpl、AppMenuItemUtils、ViewBinderとリソース
- `chrome/android/chrome_java_resources.gni`、必要なら対象BUILD.gn

設計: 現行ModelListの構築点で順序を組み立て、通常/概要/空タブレットのメニューを区別する。一般行のアイコンは残す。進む・ブックマーク・ダウンロード・情報・再読込は現行IDとハンドラーを再利用し、戻るボタン等のフラグで行数が変わる条件を検証する。

拡張機能管理のフラットな行は `manage_extensions_menu_id` を使う専用ビルダーを追加し、表示名と拡張アイコンを指定する。現行buildManageExtensionsItemはサブメニュー有効をassertし、アイコンを表示しないため、そのまま流用できない。

メニューを閉じてからgetBundleForMenuItemが呼ばれる経路がある。行→拡張IDの対応をonMenuDismissedで破棄しない。次回構築/破棄時に解除し、選択時はタブ・プロファイル・拡張機能の生存を再確認する。

### 4.2 拡張機能とポップアップ

主変更先:

- `chrome/browser/ui/android/toolbar/java/src/org/chromium/chrome/browser/toolbar/extensions/ExtensionsToolbarCoordinator.java`
- 同ディレクトリ `ExtensionsToolbarCoordinatorImpl.java`、`ExtensionActionListCoordinator.java`、`ExtensionActionListMediator.java`、`ExtensionActionPopup.java`
- `chrome/browser/ui/android/extensions/java/src/org/chromium/chrome/browser/ui/extensions/ExtensionsToolbarBridge.java`
- `chrome/browser/ui/android/extensions/extensions_toolbar_android.cc`
- `chrome/browser/resources/extensions/` の管理WebUI

確認済み経路: getAllActionIds / getPinnedActionIds → getAction(id, WebContents)・現行アイコン取得 → メニュー行 → executeUserAction(id, InvocationSource.MENU_ENTRY) → ExtensionsToolbarAndroid → 既存toolbar_view_model。古いExtensionActionsBridgeは現行で移行途中の補助クラスなので、名前だけを見てそこへ列挙機能を追加しない。

列挙の設計: pinnedの順序を保ち、未掲載の全actionを重複なく続ける案。ただしKiwiとの厳密な順序一致は最終APKで比較して決める。アクションを持たない拡張機能の扱いも確認対象。WebContentsが無い場合は管理導線を残し、実行行は生成しない。名前・アクセシブル名・アイコン・バッジはnative側の結果を使い、無効状態を見た目だけで解除しない。

行のデータはID、表示名、アクセシブル名、アイコン、選択時のタブIDを保持。別窓/プロファイル切替後に古い行から実行しないよう、Coordinatorインスタンスまたは世代番号も照合する。カラーアイコンはtintしない。フォールバックの単色アイコンだけテーマ色を適用する。

既存BridgeはActionListDelegate/MenuDelegateを所有する。新しいBridgeで登録を上書きするとポップアップ等を壊すため、既存Coordinator経由に限定する。表示中のアンインストール・バッジ更新はObserverで更新するか、そのメニューを閉じる。登録解除まで含めて実装する。

Titaniumは既に未ピン留め時の代替アンカーとスマートフォンのポップアップ拡大をpatch.shで変更している。Kiwi行から未ピン留め拡張を起動する際、この処理に依存する。メニュー消失後のアンカー有効性、IME表示、回転、連打、戻る操作、複数ウィンドウを実機確認する。native hostを作り直す必要が生じた場合はAstraへ設計を戻す。

管理ページは既存chrome://extensionsを再利用し、追加・削除・権限・詳細の処理を保持する。Titaniumのviewportとカード幅96%変更を基準にする。旧WebUI全体を移すと現行APIとの不一致を増やす。

### 4.3 ツールバー・上下配置

Kiwiのenable_bottom_toolbarはChromeActivity、TabbedRootUiCoordinator、ToolbarPhone、TopToolbarSceneLayer、タブグループ等に散在している。座標だけの反転では不十分。

現行の変更先は `chrome/browser/ui/android/toolbar/java/src/org/chromium/chrome/browser/toolbar/ToolbarPositionController.java`、同toolbar下の`settings/AddressBarSettingsFragment.java`、`top/ToolbarPhone.java`、レイアウト、`chrome/android/java/src/org/chromium/chrome/browser/toolbar/ToolbarManager.java`。

現行ToolbarPositionControllerは上下遷移、キーボード、BottomControlsStacker、BottomSheetControllerを扱う。この機構にKiwiの設定導線を接続する。TitaniumのAndroidBottomBarフラグと「URL欄を下に置く設定」は別の責務として扱う。前者を無効化するだけで上下設定が完成したとはしない。

native `chrome/browser/chrome_browser_field_trials.cc` とJava `chrome/browser/flags/android/java/src/org/chromium/chrome/browser/flags/ChromeFeatureList.java` の既定値をそろえ、アップデート後のキャッシュ値も検証する。is_desktop_androidをfalseにしてUIを戻す案は拡張機能の前提を崩すため採用しない。

### 4.4 配色と設定画面

Kiwi参照: `chrome/android/java/res/xml/main_preferences.xml`、`nightmode_preferences.xml`、`RadioButtonGroupNightModePreference.java`、`RadioButtonGroupTabSwitcherPreference.java`。

現行変更先: `chrome/android/java/src/org/chromium/chrome/browser/settings/MainSettings.java`、設定XML、設定検索登録、各機能の設定Fragment、`components/browser_ui/styles/android/`。

Kiwi専用色を定義し、メニュー・ツールバー・設定・タブの使用箇所へ段階適用する。共通SemanticColorUtilsの全surfaceを一律黒へ変える試作は、ダイアログ・シークレット・コントラストへの影響が広すぎるため採用前に分割する。サイトのtheme-colorとUIの黒固定の優先順位も明示する。

新規キーは登録機構に追加する。メニュー順序はアプリ設定、サイト暗色化例外は現行ContentSettingsに置く。設定値変更はObserverを通じて反映し、古いActivity参照を保持しない。Java・XML・文字列だけでなくGNソース一覧、リソース依存、設定検索索引、翻訳を同じ変更単位に含める。値を保存するだけで画面に効かない設定項目は受入不可。

### 4.5 タブ一覧

両系統の主な参照先は `chrome/android/features/tab_ui/java/src/org/chromium/chrome/browser/tasks/tab_management/`。Kiwiではactive_tabswitcherがCoordinator・Mediator・FeatureUtilities・ViewBinderへ広がっている。

Chromium152のTabListCoordinatorはGRID/STRIP中心で、コンパクト幅のグリッドは既に2列。まずTabUiThemeProvider、TabGridViewBinder、カードXML/dimensで参照画面へ寄せる。TabModel・TabGroup・保存/復元ロジックを維持する。全幅2列への固定は横画面や大画面で不適切なので既存適応処理を基準にする。

旧original/horizontal/classic/listを設定名だけ追加して同じGRIDへ割り当てない。各モードの操作要件と現行機構の対応を確認し、旧レイアウトの復活が必要なら別設計にする。旧タブスタックやコンポジターまで戻す必要がある場合はAstra担当。

### 4.6 ナイトモード：未確定の重要設計

確認済みのKiwi経路:

1. RadioButtonGroupNightModePreferenceがactive_nightmodeを保存。
2. `chrome/browser/ui/android/night_mode/java/src/org/chromium/chrome/browser/night_mode/WebContentsDarkModeController.java` のupdateDarkModeStringSettingsがnight_mode_settings文字列を生成。
3. `base/android/java/src/org/chromium/base/SysUtils.java` と `base/android/sys_utils.cc` に取得用JNIがある。
4. `third_party/blink/renderer/platform/graphics/dark_mode_settings_builder.cc` がdark-mode-settingsスイッチを解析。

ただし取得済み原典ではJNI値からスイッチへ渡す呼出元を確定できていない。この接続を確認済みと扱わない。

| Kiwi選択肢 | 確認できたContrastPercent | ImageGrayScalePercent | 備考 |
|---|---:|---:|---|
| default | 0 | 0.15 | amoledと同じ文字列生成 |
| amoled | 0 | 0.15 | 名称だけで画像無変換とは断定不可 |
| amoled_grayscale | 0 | 1.0 | ImagePolicy等も関与 |
| gray | 0.15 | 0.15 | レンダラー適用の比較が必要 |
| gray_grayscale | 0.15 | 1.0 | 同上 |
| high_contrast | -0.15 | 0.15 | IncreaseTextContrast=1 |

現在のChromium152のdark_mode_settings_builder.ccは前景/背景の閾値を設定する形に縮小され、Kiwiの同名ファイルと互換ではない。GetCurrentDarkModeSettingsはstaticキャッシュを持つ。旧文字列を保存するだけでは6プリセットは動かない。

先行してSolが扱える部分: 現行WebContentsDarkModeControllerのglobal設定・サイト例外・UIテーマの整合、メニューON/OFF、再起動後の状態復元。AUTO_DARK_WEB_CONTENTだけでなく現在のUI夜間状態も有効条件になっている点に注意。通常/シークレットのどちらから操作しても保存方針を統一し、サイト例外を消去しない。設定画面からテーマを変更した後に「古いテーマ」を誤復元しない設計にする。

Astraで詰める部分: 現行dark_mode_settings/filter/color_filter、WebPreferences伝播と既存テストを比較し、旧演算を最小追加するのか、現行演算で同等結果を出せるのか決定する。必要な設定型・プロセス間伝播・キャッシュ更新・再起動要否まで定義する。プロセス共通の起動スイッチは即時切替と複数プロファイルに制約があるため、実装前に判断する。旧Blinkファイルの丸ごと置換やページ全体へのCSS filterで代用しない。写真、透明画像、SVG、canvas、動画、iframe、既に暗いサイトで基準Kiwiと比較する。

## 5. 着手済み試作の監査

`port-source`は選択した14ファイルの基準状態から作った小規模な検証用gitツリー。全Chromiumソースでもビルド可能なTitaniumでもない。13既存ファイルの差分と2新規リソースがあり、完全移植ではない。

| 項目 | 判定/次の処置 |
|---|---|
| 現行拡張Coordinator経由の実行 | 方針を採用。ライフサイクル・プロファイル・権限を追加検証 |
| メニューdismiss後もID対応を保持 | 採用。次回構築とdestroyで解除する |
| buildManageExtensionsItemの直呼び | 要修正。サブメニュー前提assertとアイコン非表示が不適合 |
| アイコンの一律ICON_NO_TINT | 要修正。単色フォールバックに限りtintを有効化 |
| Night mode切替 | PoC。6種類は未実装、テーマ復元・全タブ反映は要検証 |
| 共通surfaceの一括変更 | 分割して再検討。影響範囲が広い |
| 新規リソースのGN登録 | 実施済み。ただし未追跡ファイルを差分出力から落とさない |
| Java構文解析 | 7ファイルで成功したのみ。型解決・GN・Androidコンパイルは未実施 |

開発用implement_port.pyには、その後の手修正が反映されていない。再実行して正とみなさない。prepare_reference.pyの部分パッチ適用もフルビルドの代用ではない。

以前のv1.4には、拡張行未実装、古いメニューAPI、一般行アイコンを消す方向の変更、新規リソース登録不足があった。旧キットを基盤に積み増さず、実ソースに対する新しい独立パッチを作る。

## 6. Sol用の移植手順

| 順番 | 作業 | 完了条件 |
|---|---|---|
| S0 | 固定版無改変Titaniumのビルド環境を確立 | arm64 APKが生成され、起動・ページ表示・拡張機能起動が成功 |
| S1 | 基準スクリーンショットと画面・操作対応表を固定 | 各画面の通常/暗色・設定値・密度を記録。不足は明記 |
| S2 | メニュー構築と拡張行アダプター | 実ID/バッジ表示、未ピン留めpopup、管理画面、シークレットを検証 |
| S3 | テーマと設定画面 | 登録・保存・反映・検索・日本語表示と再起動を検証 |
| S4 | ツールバーの配置・ボタン | IME、回転、スクロール、下部シート、URL入力を検証 |
| S5 | グリッドタブ外観 | 選択/閉じる/復元/グループ/再起動でタブが維持される |
| S6 | Night mode基本ON/OFF | 全タブへの整合、サイト例外、テーマ復元が成立 |
| A1→S7 | Astraのレンダラー設計後に6プリセット実装 | 実Kiwiとの画像比較と現行レンダラーテストが成立 |
| A2→S8 | 必要な旧タブモードの追加設計・実装 | 設定の全選択肢に対応した実動作がある |
| S9 | その他画面と操作の差分を埋める | 2章の全対象に合格記録または未対応の明示 |
| S10 | 統合レビュー、署名、APK引渡し | SHA256・基準コミット・テスト結果・既知問題を添付 |

各工程は別コミット/パッチとし、パッチ適用前提を検査する。文字列置換が0件でも成功扱いにする処理を避ける。適用前ハッシュ/対象版不一致は変更前に停止し、再適用は検出する。部分成功のままコンパイルへ進めない。

Solへの開始指示: 「本書S0から着手。port-sourceを完成コードとして採用しない。まず固定無改変版のビルドを確認し、次にS2を独立パッチにする。型エラーやリソースエラーはSolで処理し、A1/A2またはnative所有関係変更が必要な時だけ設計判断を戻す。」

## 7. ビルドと依存の注意点

Titanium上流のbuild.shを確認した結果:

- Vanadiumパッチを選別し、VANADIUM/Vanadium/vanadiumをTitanium用に置換してgit amする。除外パターンを過去キットの簡略版へ置き換えない。
- gclientのサブプロジェクトパッチ、フィルターリスト、同梱Titanium拡張の取得が必要。最後の拡張取得はlatest URLなので、再現性確保にはリリースとSHA256も固定する。フィルターリストも取得日時・ハッシュを残す。
- Chromiumのfetch先参照がchromium_$VERSIONなのにcheckoutが$VERSIONになっている。新規環境での成立をS0で確認し、必要なら実際に取得した固定参照へ修正する。
- 上流はarm32、arm64、bundleを順次生成する。初回はarm64 APK一つに限定し、GN引数はtarget_cpu=arm64、is_desktop_android=trueを保つ。
- 上流workflowにはVanadium更新、push、定期実行、公開Releaseがある。試験用は固定入力のworkflow_dispatchとartifact出力にし、ビルド中に基準版が動かないようにする。
- 上流の既定runnerはself-hosted。通常のubuntu-latestで容量・時間が足りるとは未確認。Chromium公式資料は最低100GB空きを要求しており、今回の作業環境のディスク約32GBではフルビルドに不足する。実用容量は生成物・キャッシュ込みで事前計測する。
- 試験APKは別package名と継続利用する試験署名鍵を使用する案。既存Titaniumへ上書き更新できるとは約束しない。鍵を毎回破棄して更新不能にしない。鍵をソース/ログへ含めない。

GitHub接続でプロフィール取得は成功。一方、取得できたリポジトリ一覧は空で、以前のユーザー名指定検索も失敗した。既存リポジトリやActions runnerの利用可否は未確認。接続成功をビルド環境確保と同一視しない。

## 8. 検証計画とレビュー

まず既存AppMenu/Toolbarの単体・描画テストにケースを追加し、UIが動く環境で実行する。主要ケースは拡張0件/複数/アイコン欠落、タブ無し、メニュー中のタブ移動/削除、拡張の無効化/削除、通常→シークレット、未ピン留めpopup。見た目だけを固定文字列検索でテストして済ませない。

統合試験では通常閲覧、戻る/進む、URL入力、ダウンロード、タブ復元、各拡張のpopupとoptions、Web Store導線を確認。共有画像に写っていたuBlock Origin、Violentmonkey等を優先するが、各拡張の互換性は実測する。UI移植で対応APIが増えるとはしない。

描画比較は同じ端末条件・同じ設定・同じページを使う。フォント、寸法、余白、アイコン、ポップアップ領域、キーボード重なりを評価する。ナイトモードはUIとページ変換を別々に判定する。

レビューは原則Sol。実装した変更のAPI整合・GN依存・null/lifecycle・設定更新・テスト結果・対象外画面への影響を見る。Astraは以下の場合に限定する:

1. 6プリセットのレンダラー/プロセス間設定設計（現時点で必要）。
2. 旧タブモードの復活が現行TabModel/コンポジターへ及ぶ場合。
3. 未ピン留め拡張popupが既存Bridgeの所有関係では成立しない場合。
4. Vanadium/TitaniumとKiwi UIの要求がプロファイル・描画・ウィンドウの境界で衝突し、局所修正で解けない場合。

import、API引数、Rリソース、翻訳、単純なパッチ衝突、通常のビルドエラーはSolの範囲。設計の選択肢と影響が出た時点で難所を報告し、全作業をAstraへ戻さない。

## 9. 参照元

- [Titanium固定リリース](https://github.com/jqssun/android-titanium-browser/releases/tag/v152.0.7977.64)
- [Titanium固定ソース](https://github.com/jqssun/android-titanium-browser/tree/80ffcdf1cebe51cddc593f571a6f26c3374aea2e)
- [Kiwi参照リリース](https://github.com/kiwibrowser/src.next/releases/tag/14310011181)
- [Kiwi公開ソース](https://github.com/kiwibrowser/src.next)
- [Chromium152ソース](https://github.com/chromium/chromium/tree/152.0.7977.64)
- [Chromium Androidビルド要件](https://github.com/chromium/chromium/blob/152.0.7977.64/docs/android_build_instructions.md)

本書のコードに関する根拠は、上記固定版の取得済みファイルおよび明記したパスのソース確認。提案クラスと工程は設計案。実装完了・ビルド成功・端末互換性はまだ主張しない。
