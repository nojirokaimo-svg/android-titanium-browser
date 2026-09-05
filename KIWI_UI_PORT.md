# Titanium-Kiwi Sol v2

Titanium 152.0.7977.64へKiwi風UIを段階移植するための、固定版パッチとarm64ビルド構成です。

## 現在実装している範囲

- 3点メニュー上部の5操作行を維持
- その直後に、現行Titaniumの拡張機能をカラーアイコン・バッジ付きで列挙
- 拡張機能行から既存の権限判定・popup経路を使って実行
- フラットな「拡張機能」行から `chrome://extensions` を開く
- 通常メニューのアイコン表示と、Kiwiに近い小さい角丸popup
- Chromiumの大きな下部メニュー機能とサブメニューを既定で無効化
- Kiwiと同じ考え方の基本Night mode ON/OFF（UIを暗色へ切替えてAuto Darkを有効化）
- 英語・日本語の追加文字列

まだ完全移植ではありません。Kiwiの6種類のNight mode、設定画面全体、ツールバー設定、タブ表示方式、新規タブ・履歴等の全画面調整は後続工程です。APKをビルドしていない状態を「完成」とは扱いません。

## 固定しているソース

- Titanium: `80ffcdf1cebe51cddc593f571a6f26c3374aea2e`
- Vanadium: `150a27e23302cc265baf8a7fb7c0f0112bddf2fd`
- Chromium: `506c834ecceaa943c5f41e6cfe7f68acb5c45346` (`152.0.7977.64`)

`kiwi_port/apply.py`は、Titaniumのパッチ適用後に対象ファイルのSHA-256が一致するか確認します。一致しない版や部分適用状態には変更を加えません。同じ完成状態へ再実行した場合は、そのまま正常終了します。

## GitHub Actionsでの試験ビルド

このフォルダの中身をGitHubリポジトリのルートへ入れ、Actionsの **Build Titanium-Kiwi core** を手動実行します。自動更新、定期実行、Release公開は行いません。成功すると `Titanium-Kiwi-core-152-arm64` artifactにAPKとSHA-256が入ります。

テスト版のパッケージ名は `io.github.nojirokaimo.titaniumkiwi` です。通常のTitaniumと共存できます。Chromiumのビルドターゲットが生成するテスト署名APKを使用するため、正式配布用ではありません。

GitHubホストrunnerは容量・6時間制限に達する可能性があります。Chromium公式資料は100GB以上の空きを要求します。失敗した場合はfailure artifactの`args.gn`やログを確認し、容量不足なら100GB以上のself-hosted Linux runnerへ切り替えます。

## ローカルLinuxでの実行

```bash
chmod +x build_kiwi_ui_arm64.sh
./build_kiwi_ui_arm64.sh
```

Windows単体ではChromium Androidの公式ビルド環境になりません。Windows PCを使う場合も、GitHub ActionsまたはLinux runner上で実行します。

## ファイル

- `kiwi_port/kiwi-ui-core.patch`: 実装差分
- `kiwi_port/manifest.json`: 固定版、適用前後ハッシュ、実装範囲
- `kiwi_port/apply.py`: 事前検査付き適用ツール
- `build_kiwi_ui_arm64.sh`: 固定版取得からarm64 APK検証まで
- `.github/workflows/build.yml`: 手動ビルドworkflow
- `DESIGN.md`: 全体設計とSolへの工程分割

## 検証済み / 未検証

検証済み:

- 変更Java 7ファイルの構文解析
- `git diff --check`
- cleanな選択ソースへのパッチ適用、適用後ハッシュ、再実行
- Python構文、shell構文、JSON構文

未検証:

- GN依存解決とAndroid Javaの型コンパイル
- Chromium/Titaniumの全ビルド
- APK生成・署名検証・端末起動
- 実際の拡張機能popup、シークレット、Night mode、回転・IME

ビルドエラーは後続のSol工程で処理します。レンダラーへKiwiの6プリセットを実装する段階は、先にAstraで設計を確定します。
