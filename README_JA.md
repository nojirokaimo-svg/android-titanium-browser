# Titanium-Kiwi Sol v2

Titaniumの現行Chromiumと拡張機能基盤を保ち、Kiwi風UIを機能別patchとして再適用できるarm64ビルドキットです。固定版ビルドと、将来のTitanium upstream追従の両方に対応します。

## 実装済み範囲

- 3点メニュー上部の5操作行
- 拡張機能のカラーアイコン・バッジ付き行と既存権限/popup経路での実行
- フラットな「拡張機能」管理行
- 通常メニューのアイコンとKiwiに近いコンパクトpopup
- Chromiumの大きな下部メニューとサブメニューを既定で無効化
- 基本Night mode ON/OFF（UI暗色＋Auto Dark）
- 英語・日本語リソース

完全移植ではありません。Kiwiの6種類のNight mode、設定画面全体、ツールバー設定、旧タブ表示方式、新規タブ・履歴等の全画面調整は未実装です。6種類のNight modeはChromium 152のレンダラー設定伝播と旧Kiwiの方式が非互換なため、Astraで設計を確定してから実装します。

## patch構成

`kiwi_port/patches/series.json`が適用順、機能名、対象ファイル、patch SHA-256を管理します。

| 順序 | 機能 | 主な責務 |
|---|---|---|
| `010-resources.patch` | resources | メニューID、英語・日本語ラベル、GN登録 |
| `020-app-menu-actions.patch` | app-menu-actions | 拡張機能行、実行経路、基本Night mode |
| `030-menu-presentation.patch` | menu-presentation | popup外観、下部メニュー・サブメニュー制御 |

拡張機能とNight modeは同じActivity/メニュー生成箇所を変更するため、競合しやすいファイルを二重patchにせず、一つの依存単位にしています。

固定対象はTitanium `80ffcdf1cebe51cddc593f571a6f26c3374aea2e`、Vanadium `150a27e23302cc265baf8a7fb7c0f0112bddf2fd`、Chromium `506c834ecceaa943c5f41e6cfe7f68acb5c45346` (`152.0.7977.64`)です。`manifest.json`には固定版の適用前後ハッシュを残しています。

## 固定版APKビルド

Actionsの **Build Titanium-Kiwi core** を実行します。GitHub-hosted runnerの6時間制限を避けるため、1段階210分で安全停止し、`out/Default`をActions cacheへ保存して最大5段階で継続します。前段のobjectを復元するので完了済みコンパイルはやり直しません。

成功artifactは `Titanium-Kiwi-core-<version>-arm64` で、APKと `SHA256SUMS.txt` を含みます。テスト版package名は `io.github.nojirokaimo.titaniumkiwi`、Chromiumのテスト署名です。

ローカルLinuxでは次を実行します。

```bash
./build_kiwi_ui_arm64.sh
```

## Titanium upstream更新

### GitHub Actions

Actionsの **Update Titanium upstream and rebuild Kiwi UI** を手動実行します。`titanium_ref`にbranch/tag/commitを指定でき、空欄ならupstream既定branchのHEADを使います。

workflowは次を自動実行します。

1. 新しいTitanium commit、Vanadium submodule、Chromium version/tag SHAを固定
2. Titanium/Vanadium patch適用後のChromiumへKiwi機能patchをbest-effort適用
3. 競合がなければ、固定版と同じ210分×最大5段階のcache継続ビルド
4. 競合時はビルドせず、機能別レポート、JSON、`.rej`をfailure artifactへ保存

このworkflowはupstreamを検証用のdetached checkoutへ取得します。作業branchを強制merge/force-pushしないため、既存成果や進行中ビルドを壊しません。成功した固定SHAを確認後、必要なら通常のGit操作でforkへmergeします。

### ローカル更新確認

```bash
./update_titanium_upstream.sh --ref main
```

refを省略すると既定branchのHEADを使用します。作業場所は既定で `upstream-update-work/`、レポートは `output/kiwi-patch-report.md` と同名JSONです。これは使い捨てworktreeとして扱います。

## 競合時の復旧

`apply.py --best-effort`は、適用できる独立機能とclean hunkを先に適用し、競合hunkだけを対象ファイル隣の `.rej` に残します。レポートには `feature id → 競合ファイル` が出ます。

1. failure artifactの `kiwi-patch-report.md/.json` と `.rej` を確認
2. レポートにある機能・ファイルだけを新APIへ合わせて修正
3. `.rej`を削除し、Chromium側のコンパイル/対象テストを確認
4. 下記手順で機能patchを再生成
5. 更新workflowを再実行

途中状態からやり直す場合は、**使い捨ての更新worktree内だけ**で `git reset --hard <新しいChromium基準SHA>` と未追跡 `.rej` の削除を行います。Kiwi修正を保持した開発worktreeや本リポジトリでresetしないでください。

厳密適用は次です。固定版で一つでも機能が適用不能なら変更せず停止します。

```bash
python3 kiwi_port/apply.py /path/to/chromium/src
```

更新版の部分適用とレポート生成は次です。競合がある場合の終了コードは `2` です。

```bash
python3 kiwi_port/apply.py /path/to/chromium/src \
  --best-effort --report output/kiwi-patch-report.md
```

## patch再生成

基準commitからKiwi修正を加えたChromium git worktreeを用意し、次を実行します。

```bash
python3 kiwi_port/regenerate_patches.py /path/to/modified/chromium/src --base HEAD
```

`regenerate_patches.py`の `FEATURES` がファイルを機能単位へ割り当てます。ファイルを追加した場合は該当featureの一覧へ追加してから再生成してください。生成後は必ず以下を確認します。

```bash
python3 -m py_compile kiwi_port/apply.py kiwi_port/regenerate_patches.py
python3 kiwi_port/apply.py /path/to/clean/test-worktree
python3 kiwi_port/apply.py /path/to/clean/test-worktree
git diff --check
```

1回目で全featureが適用され、2回目がalready-appliedで正常終了すること、`series.json`のSHA-256が更新されることを確認します。

## 主要ファイル

- `kiwi_port/patches/`: 機能別patchとseries metadata
- `kiwi_port/apply.py`: strict/best-effort適用、競合レポート
- `kiwi_port/regenerate_patches.py`: 機能patch再生成
- `update_titanium_upstream.sh`: upstream版の解決とローカル適用確認
- `build_kiwi_ui_arm64.sh`: 取得、patch、GN、arm64 APK生成
- `.github/actions/kiwi-build-stage/`: 分割・cache継続ビルド共通処理
- `.github/workflows/kiwi-ui-build.yml`: 固定版ビルド
- `.github/workflows/update-upstream.yml`: upstream更新＋再適用＋同じ分割ビルド
- `DESIGN.md`: 全体設計とAstra判断境界

APK生成・端末動作が確認できるまでは完成扱いにしません。通常のimport/API/Rリソース/patch競合/ビルドエラーはSolで修正し、6種類のNight mode等のレンダラー設計境界だけAstraへ戻します。
