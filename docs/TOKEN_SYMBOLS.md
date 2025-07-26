# 常用代幣符號參考 (TOKEN_SYMBOLS.md)

本文件記錄了在 Bitfinex 資金市場 (Funding Market) 中常用的代幣符號，並提供了一些重要的使用慣例。

## 1. 資金幣種符號慣例

在 Bitfinex API 中，用於資金市場的幣種符號通常會加上前綴 `f`。例如，美元 `USD` 在資金市場中的符號是 `fUSD`。在配置 `.env` 文件中的 `LENDING_CURRENCY` 時，您應該使用**不帶 `f` 前綴的標準符號** (例如 `USD`, `BTC`, `UST`)，程式會在需要時自動添加 `f` 前綴。

## 2. 常見資金幣種符號

以下是一些常見的資金幣種及其在 Bitfinex API 中的對應符號。請在 `.env` 文件中使用「標準符號」欄中的值。

| 貨幣名稱           | 標準符號 (用於 `.env`) | API 資金符號 (f-symbol) |
| ------------------ | ---------------------- | ----------------------- |
| **美元**           | `USD`                  | `fUSD`                  |
| **泰達幣 (Tether)**| `UST`                  | `fUST`                  |
| **比特幣**         | `BTC`                  | `fBTC`                  |
| **以太坊**         | `ETH`                  | `fETH`                  |
| **歐元**           | `EUR`                  | `fEUR`                  |
| **日元**           | `JPY`                  | `fJPY`                  |

**重要提示：** Bitfinex 平台上的 Tether (泰達幣) 使用 `UST` 作為其符號，而非 `USDT` 或 `USDt`。這是一個常見的混淆點，請務必在配置中設定 `LENDING_CURRENCY=UST` 來交易泰達幣。

## 3. 支援的資金幣種列表

以下是截至文檔更新時，在 Bitfinex 上找到的部分支援的資金幣種符號 (f-symbol) 列表。如果您需要使用列表外的幣種，請先在 Bitfinex 官網確認其可用性。

- `fADA`
- `fALG`
- `fAPE`
- `fAPT`
- `fATO`
- `fAVAX`
- `fBCHN`
- `fBTC`
- `fCOMP`
- `fDAI`
- `fDOGE`
- `fDOT`
- `fDSH`
- `fEGLD`
- `fETC`
- `fETH`
- `fETHW`
- `fEUR`
- `fFIL`
- `fGBP`
- `fIOT`
- `fJPY`
- `fLEO`
- `fLINK`
- `fLTC`
- `fMATIC`
- `fMKR`
- `fNEO`
- `fSHIB`
- `fSOL`
- `fSUI`
- `fSUSHI`
- `fTRX`
- `fUNI`
- `fUSD`
- `fUST`
- `fXAUT` (Tether Gold)
- `fXLM`
- `fXMR`
- `fXRP`
- `fZEC`
- `fZRX`

## 4. 測試幣種

Bitfinex 還提供用於測試的代幣，它們通常以 `fTEST` 開頭，例如 `fTESTUSD`, `fTESTBTC`。這些幣種不具有真實價值，可用於測試環境。
