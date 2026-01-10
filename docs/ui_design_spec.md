# UI/UX 設計規範 (Design Specification)
## 大樹聽中行政自動化系統

---

## 1. 色彩系統 (Color System)

### 主色調
| 用途 | 名稱 | HEX | Flet 常數 |
|------|------|-----|-----------|
| 主要操作 | Primary | `#2196F3` | `Colors.BLUE` |
| 成功 | Success | `#4CAF50` | `Colors.GREEN` |
| 警告 | Warning | `#FF9800` | `Colors.ORANGE` |
| 錯誤 | Error | `#F44336` | `Colors.RED` |
| 資訊 | Info | `#00BCD4` | `Colors.CYAN` |

### 背景色
| 用途 | HEX | Flet 常數 |
|------|-----|-----------|
| 主背景 | `#121212` | `Colors.GREY_900` |
| 卡片背景 | `#1E1E1E` | `Colors.GREY_850` |
| 頂欄背景 | `#1A1A1A` | `Colors.GREY_900` |
| 分隔線 | `#333333` | `Colors.GREY_800` |

### 文字色
| 用途 | HEX | Flet 常數 |
|------|-----|-----------|
| 主要文字 | `#FFFFFF` | `Colors.WHITE` |
| 次要文字 | `#B0B0B0` | `Colors.GREY_400` |
| 提示文字 | `#757575` | `Colors.GREY_600` |
| 禁用文字 | `#555555` | `Colors.GREY_700` |

---

## 2. 間距系統 (Spacing System)

基礎單位：**8px**

| 代號 | 數值 | 用途 |
|------|------|------|
| XS | 4px | 圖示與文字間距 |
| S | 8px | 元素內小間距 |
| M | 16px | 元素間標準間距 |
| L | 24px | 區塊間距 |
| XL | 32px | 頁面邊距 |

### 卡片樣式
- 內邊距 (padding): 20px
- 圓角 (border_radius): 12px
- 陰影: 內建 Card 陰影

---

## 3. 字型系統 (Typography)

| 用途 | 大小 | 粗細 |
|------|------|------|
| 頁面標題 | 24px | Bold |
| 卡片標題 | 18px | Bold |
| 區塊標題 | 16px | Bold |
| 正文 | 14px | Normal |
| 輔助說明 | 12px | Normal |
| 標籤 | 11px | Normal |

---

## 4. 按鈕樣式 (Button Styles)

### 主要按鈕 (Primary)
- 背景: `Colors.BLUE`
- 文字: `Colors.WHITE`
- 圓角: 8px
- 高度: 48px
- 用於: 開始處理、確認、儲存

### 次要按鈕 (Secondary)
- 背景: `Colors.GREY_800`
- 文字: `Colors.WHITE`
- 邊框: 1px `Colors.GREY_600`
- 用於: 取消、返回

### 危險按鈕 (Danger)
- 背景: `Colors.RED`
- 文字: `Colors.WHITE`
- 用於: 刪除、停止

### 成功按鈕 (Success)
- 背景: `Colors.GREEN`
- 文字: `Colors.WHITE`
- 用於: 綁定成功、完成

---

## 5. 狀態指示器 (Status Indicators)

### 監控狀態
| 狀態 | 圖示 | 顏色 | 動畫 |
|------|------|------|------|
| 未啟動 | `STOP_CIRCLE` | Grey | 無 |
| 監控中 | `PLAY_CIRCLE` | Green | 脈動閃爍 |
| 處理中 | `SYNC` | Blue | 旋轉 |
| 錯誤 | `ERROR` | Red | 無 |

### 綁定狀態徽章
| 狀態 | 文字 | 顏色 |
|------|------|------|
| 已綁定 | ✅ 已綁定 | Green |
| 未綁定 | ⚠️ 未設定 | Orange |
| 錯誤 | ❌ 錯誤 | Red |

---

## 6. 元件定義 (Components)

### 6.1 可摺疊區塊 (Collapsible Section)
- 標題欄高度: 56px
- 標題欄背景: `Colors.GREY_850`
- 展開動畫: 300ms ease

### 6.2 首次使用檢查卡片
- 檢查項目列表
- 未完成項目顯示「前往設定」按鈕
- 完成所有必要項目後啟用「開始使用」

### 6.3 錯誤對話框
- 問題描述 + 建議解決方案
- 「前往修復」按鈕

---

## 7. 互動規則 (Interaction Rules)

### 防呆機制
1. 未設定帳號時，「開始處理」按鈕禁用並顯示提示
2. 危險操作需二次確認
3. 必填欄位即時驗證

### 回饋機制
1. 按鈕點擊後 200ms 內需有視覺回饋
2. 載入操作需顯示進度指示器
3. 操作完成後顯示成功/失敗訊息 3 秒

---

*Version: 1.0*
*Last Updated: 2026-01-09*
