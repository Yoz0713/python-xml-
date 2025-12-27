# NOAH 聽力評估 XML 解析技術文件

> 本文件詳細記錄 Hearing Assessment Fitting Review 系統中的 XML 解析邏輯，供其他 AI 或開發者參考實作。

---

## 目錄

1. [概述](#概述)
2. [XML 格式結構](#xml-格式結構)
3. [資料結構定義](#資料結構定義)
4. [解析架構流程](#解析架構流程)
5. [核心函數詳解](#核心函數詳解)
6. [XML 標籤對應表](#xml-標籤對應表)
7. [特殊處理邏輯](#特殊處理邏輯)
8. [Python 實作建議](#python-實作建議)

---

## 概述

本系統解析的是 **NOAH 格式** 的聽力評估 XML 檔案。NOAH 是聽力產業的標準資料交換格式，由 HIMSA（Hearing Instrument Manufacturers' Software Association）制定。

### 支援的資料類型

| 類型 | TypeOfData 關鍵字 | 說明 |
|------|-------------------|------|
| **純音聽力圖** | `audiogram` | 氣導/骨導閾值測試 |
| **語音聽力** | `audiogram` | SRT、SDS、MCL、UCL |
| **中耳分析** | `impedance` | 鼓室圖、Type 判定 |
| **助聽器選擇** | `hearing instrument selection` | 設備型號、序號 |

---

## XML 格式結構

### 基本結構

```xml
<?xml version="1.0" encoding="utf-8"?>
<NOAH_Patients_Export xmlns:pt="...">
  <Patient>
    <FirstName>王</FirstName>
    <LastName>小明</LastName>
    <NOAHPatientNumber>12345</NOAHPatientNumber>
    <DateofBirth>1980-01-15</DateofBirth>
    <Gender>Male</Gender>
  </Patient>
  
  <Actions>
    <Action>
      <TypeOfData>Audiogram</TypeOfData>
      <ActionDate>2024-03-15T10:30:00</ActionDate>
      <Description>Pure Tone Audiometry</Description>
      <PublicData>
        <!-- 測試資料 -->
      </PublicData>
    </Action>
    <!-- 更多 Action... -->
  </Actions>
</NOAH_Patients_Export>
```

### Namespace 問題

NOAH XML 常帶有 namespace 前綴（如 `<pt:Patient>`），需在解析前清除：

```typescript
const cleanXML = (xml: string): string => {
    return xml
        .replace(/<[a-zA-Z0-9]+:([a-zA-Z0-9_\-]+)/g, '<$1')   // <pt:Patient> → <Patient>
        .replace(/<\/[a-zA-Z0-9]+:([a-zA-Z0-9_\-]+)>/g, '</$1>') // </pt:Patient> → </Patient>
        .replace(/\sxmlns[^"]+\"[^"]+\"/g, '')                // 移除 xmlns
        .replace(/\sxmlns:([a-zA-Z0-9]+)=\"[^\"]+\"/g, '');   // 移除 xmlns:xxx
};
```

---

## 資料結構定義

### AudioPoint（聽力點位）

```typescript
interface AudioPoint {
  frequency: number;      // 頻率 (Hz): 250, 500, 1000, 2000, 4000, 8000
  intensity: number;      // 強度 (dB HL): -10 ~ 120
  isMasked?: boolean;     // 是否有遮蔽
  isNoResponse?: boolean; // 是否無反應
}
```

### EarData（單耳資料）

```typescript
interface EarData {
  airConduction: AudioPoint[];  // 氣導閾值
  boneConduction: AudioPoint[]; // 骨導閾值
}
```

### SpeechEarData（語音聽力）

```typescript
interface SpeechEarData {
  srt?: number;  // Speech Reception Threshold 語音接收閾值 (dB)
  sds?: number;  // Speech Discrimination Score 語音辨識率 (%)
  mcl?: number;  // Most Comfortable Level 最舒適音量 (dB)
  ucl?: number;  // Uncomfortable Level 不舒適音量 (dB)
}
```

### ImpedanceData（中耳分析）

```typescript
interface TympanogramPoint {
  pressure: number;    // 壓力 (daPa): -400 ~ +200
  compliance: number;  // 順應性 (mL 或 mmho)
}

interface ImpedanceData {
  tympanogram: TympanogramPoint[];  // 鼓室圖曲線點
  peakPressure?: number;            // 峰值壓力 (daPa)
  peakCompliance?: number;          // 峰值順應性 (mL)
  canalVolume?: number;             // 外耳道容積 ECV (mL)
  gradient?: number;                // 梯度
  tympanogramType?: string;         // "Type A", "Type B", "Type C", "Type As", "Type Ad"
}
```

### PatientInfo（病患資訊）

```typescript
interface PatientInfo {
  firstName: string;
  lastName: string;
  patientNumber: string;
  gender?: string;
  birthDate?: string;  // 格式: "YYYY-MM-DD"
}
```

### HearingInstrument（助聽器）

```typescript
interface HearingInstrument {
  model: string;         // 型號名稱
  serialNumber: string;  // 序號
  earMold?: string;      // 耳模資訊
  battery?: string;      // 電池型號
  date?: string;         // 紀錄日期
  timestamp?: string;    // 完整時間戳
  side?: 'Left' | 'Right';
}
```

### HearingSession（聽力檢測記錄）

```typescript
type TestType = 'Tone' | 'Impedance' | 'Speech' | 'Unknown';

interface HearingSession {
  id: string;
  testDate: string;           // "YYYY-MM-DD"
  testType: TestType;
  description: string;
  patientInfo?: PatientInfo;
  
  // 純音聽力
  leftEar: EarData;
  rightEar: EarData;
  
  // 語音聽力
  leftSpeech?: SpeechEarData;
  rightSpeech?: SpeechEarData;
  
  // 中耳分析
  leftImpedance?: ImpedanceData;
  rightImpedance?: ImpedanceData;
  
  // 助聽器
  leftDevice?: HearingInstrument;
  rightDevice?: HearingInstrument;
}
```

---

## 解析架構流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      parseHearingXML(xmlString)                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: cleanXML()                                              │
│  - 移除所有 namespace 前綴                                        │
│  - 移除 xmlns 屬性宣告                                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: DOMParser.parseFromString(cleanedXml, "text/xml")       │
│  - 將字串轉為 DOM 文件物件                                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: parsePatientInfo(xmlDoc)                                │
│  - 從 <Patient> 節點擷取病患資訊                                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: 遍歷所有 <Action> 節點                                   │
│  for each Action:                                                │
│    - 讀取 TypeOfData, ActionDate, Description                    │
│    - 依 TypeOfData 分流處理                                       │
└─────────────────────────────────────────────────────────────────┘
          │                     │                     │
          ▼                     ▼                     ▼
   ┌────────────┐       ┌────────────┐       ┌────────────────────┐
   │ Audiogram  │       │ Impedance  │       │ HI Selection       │
   │            │       │            │       │                    │
   │ - 純音閾值  │       │ - 鼓室圖曲線│       │ - 助聽器型號       │
   │ - 氣導/骨導 │       │ - 峰值數據  │       │ - 序號、側邊       │
   │ - SRT/SDS  │       │ - Type判定  │       │                    │
   └────────────┘       └────────────┘       └────────────────────┘
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: 合併 Session                                            │
│  - 以 (日期 + 測試類型) 為 key 合併多個 Action                    │
│  - 去除重複點位，按頻率排序                                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 6: 輸出結果                                                 │
│  return {                                                        │
│    sessions: HearingSession[],                                   │
│    allDevices: HearingInstrument[],                              │
│    deviceTrialGroups: DeviceTrialGroup[]                         │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心函數詳解

### 1. getText / getFloat

基礎工具函數，從父節點取得子標籤內容：

```typescript
const getText = (parent: Element, tagName: string): string | null => {
    const node = parent.getElementsByTagName(tagName)[0];
    return node ? node.textContent : null;
};

const getFloat = (parent: Element, tagName: string): number | undefined => {
    const val = getText(parent, tagName);
    if (val) {
        const num = parseFloat(val);
        return isNaN(num) ? undefined : num;
    }
    return undefined;
};
```

### 2. 純音聽力解析

從 `<ToneThresholdAudiogram>` 區塊擷取氣導/骨導閾值：

```typescript
const toneBlocks = Array.from(action.getElementsByTagName('ToneThresholdAudiogram'));

toneBlocks.forEach(block => {
    // 判斷耳側和導型
    const output = getText(block, 'StimulusSignalOutput') || '';
    const isRight = output.toLowerCase().includes('right') || output === '1';
    const isLeft = output.toLowerCase().includes('left') || output === '2';
    const isBone = output.toLowerCase().includes('bone');
    
    // 遍歷測試點
    const points = Array.from(block.getElementsByTagName('TonePoints'));
    points.forEach(ptNode => {
        const freq = getFloat(ptNode, 'StimulusFrequency');
        const level = getFloat(ptNode, 'StimulusLevel');
        const status = getText(ptNode, 'TonePointStatus');
        
        // 遮蔽判斷：檢查實際遮蔽數據
        const maskingFreq = getFloat(ptNode, 'MaskingFrequency');
        const maskingLevel = getFloat(ptNode, 'MaskingLevel');
        const hasActualMasking = (maskingFreq !== undefined && maskingLevel !== undefined);
        
        // NoResponse 判斷
        const isNoResponse = (status === 'NoResponse');
        
        if (freq !== undefined && level !== undefined) {
            const pt: AudioPoint = {
                frequency: freq,
                intensity: level,
                isMasked: (status === 'Masked') || hasActualMasking,
                isNoResponse: isNoResponse
            };
            
            // 分配到對應陣列
            if (isRight) {
                isBone ? rightTone.boneConduction.push(pt) : rightTone.airConduction.push(pt);
            } else if (isLeft) {
                isBone ? leftTone.boneConduction.push(pt) : leftTone.airConduction.push(pt);
            }
        }
    });
});
```

### 3. 語音聽力解析

從多個區塊擷取 SRT、SDS、MCL：

```typescript
// SRT (Speech Reception Threshold)
const srtBlocks = Array.from(action.getElementsByTagName('SpeechReceptionThresholdAudiogram'));
srtBlocks.forEach(block => {
    const output = getText(block, 'StimulusSignalOutput') || '';
    const points = block.getElementsByTagName('SpeechReceptionPoints');
    for (let i = 0; i < points.length; i++) {
        const level = getFloat(points[i], 'StimulusLevel');
        if (level !== undefined) {
            if (output.includes('Right')) rightSpeech.srt = level;
            if (output.includes('Left')) leftSpeech.srt = level;
        }
    }
});

// SDS (Speech Discrimination Score) - 取最高分
const sdsBlocks = Array.from(action.getElementsByTagName('SpeechDiscriminationAudiogram'));
sdsBlocks.forEach(block => {
    const output = getText(block, 'StimulusSignalOutput') || '';
    const points = block.getElementsByTagName('SpeechDiscriminationPoints');
    let maxScore = -1;
    for (let i = 0; i < points.length; i++) {
        const score = getFloat(points[i], 'ScorePercent');
        if (score !== undefined && score > maxScore) maxScore = score;
    }
    if (maxScore > -1) {
        if (output.includes('Right')) rightSpeech.sds = maxScore;
        if (output.includes('Left')) leftSpeech.sds = maxScore;
    }
});

// MCL (Most Comfortable Level)
const mclBlocks = Array.from(action.getElementsByTagName('SpeechMostComfortableLevel'));
mclBlocks.forEach(block => {
    const output = getText(block, 'StimulusSignalOutput') || '';
    const points = block.getElementsByTagName('SpeechMostComfortablePoint');
    for (let i = 0; i < points.length; i++) {
        const level = getFloat(points[i], 'StimulusLevel');
        if (level !== undefined) {
            if (output.includes('Right')) rightSpeech.mcl = level;
            if (output.includes('Left')) leftSpeech.mcl = level;
        }
    }
});
```

### 4. 中耳分析解析（Impedance）

```typescript
if (typeOfData.toLowerCase().includes('impedance')) {
    const isRight = description.toLowerCase().includes('right');
    const isLeft = description.toLowerCase().includes('left');
    
    // 峰值順應性
    let peakComp = getFloat(action, 'MaximumCompliance')?.valueOf();
    const maxCompNode = action.getElementsByTagName('MaximumCompliance')[0];
    if (maxCompNode) {
        const valNode = maxCompNode.getElementsByTagName('ComplianceValue')[0];
        if (valNode) peakComp = getFloat(valNode, 'ArgumentCompliance1');
    }
    
    // 外耳道容積
    let canalVol = getFloat(action, 'CanalVolume')?.valueOf();
    const canalVolNode = action.getElementsByTagName('CanalVolume')[0];
    if (canalVolNode) {
        const valNode = canalVolNode.getElementsByTagName('ComplianceValue')[0];
        if (valNode) canalVol = getFloat(valNode, 'ArgumentCompliance1');
    }
    
    // 單位正規化（有些儀器用 μL，需除以 100）
    const scaleFactor = (canalVol && canalVol > 5) ? 100 : 1;
    if (peakComp !== undefined) peakComp = peakComp / scaleFactor;
    if (canalVol !== undefined) canalVol = canalVol / scaleFactor;
    
    // 鼓室圖曲線點
    const points: TympanogramPoint[] = [];
    const curvePoints = Array.from(action.getElementsByTagName('CompliancePoint'));
    curvePoints.forEach(pt => {
        const pressure = getFloat(pt, 'Pressure');
        let compliance = 0;
        const compNode = pt.getElementsByTagName('Compliance')[0];
        if (compNode) compliance = getFloat(compNode, 'ArgumentCompliance1') || 0;
        
        if (pressure !== undefined) {
            points.push({ pressure, compliance: compliance / scaleFactor });
        }
    });
    
    // 排序並找峰值壓力
    const sortedPoints = points.sort((a, b) => a.pressure - b.pressure);
    let calculatedPeakPressure: number | undefined;
    let maxC = -1;
    sortedPoints.forEach(p => {
        if (p.compliance > maxC) {
            maxC = p.compliance;
            calculatedPeakPressure = p.pressure;
        }
    });
    
    // Type 判定
    const tympanogramType = calculateTympanogramType(calculatedPeakPressure, peakComp);
}
```

### 5. Tympanogram Type 判定（Jerger 分類）

#### 5.1 臨床背景

鼓室圖（Tympanogram）是中耳功能評估的重要工具，由 Jerger 於 1970 年提出分類標準。判定依據兩個主要參數：

| 參數 | 說明 | 正常範圍 |
|------|------|----------|
| **峰值壓力** (Peak Pressure) | 鼓膜順應性最高時的外耳道壓力 | -100 ~ +100 daPa |
| **峰值順應性** (Peak Compliance) | 鼓膜最大順應性值 | 0.3 ~ 1.6 mL |

#### 5.2 Jerger 分類標準

| Type | 峰值壓力 | 峰值順應性 | 臨床意義 |
|------|----------|------------|----------|
| **Type A** | -100 ~ +100 daPa | 0.3 ~ 1.6 mL | 正常中耳功能 |
| **Type As** | -100 ~ +100 daPa | 0.1 ~ 0.3 mL | 鼓膜僵硬、聽小骨固定（如耳硬化症） |
| **Type Ad** | -100 ~ +100 daPa | > 1.6 mL | 鼓膜鬆弛、聽小骨鏈斷裂 |
| **Type B** | 無明顯峰值 | ≤ 0.1 mL | 中耳積液、鼓膜穿孔、耵聹栓塞 |
| **Type C** | < -100 daPa | 正常 | 耳咽管功能不良、負壓中耳 |

#### 5.3 判斷流程圖

```
                    ┌─────────────────────┐
                    │  輸入: peakPressure  │
                    │       peakCompliance │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ 任一參數為 undefined?│
                    └─────────┬───────────┘
                              │
                    Yes ──────┴────── No
                      │                │
                      ▼                ▼
               ┌──────────┐   ┌─────────────────────┐
               │ "Unknown"│   │ peakCompliance ≤ 0.1?│
               └──────────┘   └─────────┬───────────┘
                                        │
                              Yes ──────┴────── No
                                │                │
                                ▼                ▼
                         ┌──────────┐   ┌─────────────────────────┐
                         │ "Type B" │   │ peakPressure 在正常範圍？ │
                         └──────────┘   │   (-100 ~ +100 daPa)     │
                                        └─────────┬───────────────┘
                                                  │
                                        Yes ──────┴────── No
                                          │                │
                                          ▼                ▼
                              ┌──────────────────┐   ┌──────────┐
                              │ 判斷 A/As/Ad     │   │ "Type C" │
                              └────────┬─────────┘   └──────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
        ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
        │ comp < 0.3?     │  │ comp > 1.6?     │  │ 其他            │
        │ → "Type As"     │  │ → "Type Ad"     │  │ → "Type A"      │
        └─────────────────┘  └─────────────────┘  └─────────────────┘
```

#### 5.4 TypeScript 實作

```typescript
const calculateTympanogramType = (
    peakPressure: number | undefined, 
    peakCompliance: number | undefined
): string => {
    // Step 1: 參數驗證
    if (peakPressure === undefined || peakCompliance === undefined) {
        return 'Unknown';
    }
    
    // Step 2: Type B - 順應性極低（扁平型，無峰值）
    if (peakCompliance <= 0.1) {
        return 'Type B';
    }
    
    // Step 3: Type C - 峰值壓力偏負（耳咽管功能不良）
    if (peakPressure < -100) {
        return 'Type C';
    }
    
    // Step 4: 壓力超出正常範圍（罕見，歸類為 Type C）
    if (peakPressure > 100) {
        return 'Type C';
    }
    
    // Step 5: 壓力正常，依順應性細分
    // peakPressure 在 -100 ~ +100 daPa 範圍內
    
    // Type As: 淺峰型（順應性偏低）
    if (peakCompliance > 0.1 && peakCompliance < 0.3) {
        return 'Type As';
    }
    
    // Type Ad: 高峰型（順應性過高）
    if (peakCompliance > 1.6) {
        return 'Type Ad';
    }
    
    // Type A: 正常（順應性在 0.3 ~ 1.6 mL）
    return 'Type A';
};
```

#### 5.5 Python 實作

```python
def calculate_tympanogram_type(
    peak_pressure: float | None, 
    peak_compliance: float | None
) -> str:
    """
    根據 Jerger 分類判定鼓室圖類型
    
    Args:
        peak_pressure: 峰值壓力 (daPa)
        peak_compliance: 峰值順應性 (mL)
    
    Returns:
        'Type A', 'Type As', 'Type Ad', 'Type B', 'Type C', 或 'Unknown'
    """
    # 參數驗證
    if peak_pressure is None or peak_compliance is None:
        return 'Unknown'
    
    # Type B: 扁平型（無峰值）
    if peak_compliance <= 0.1:
        return 'Type B'
    
    # Type C: 負壓型
    if peak_pressure < -100 or peak_pressure > 100:
        return 'Type C'
    
    # 壓力正常 (-100 ~ +100 daPa)，依順應性細分
    if peak_compliance < 0.3:
        return 'Type As'  # 淺峰型
    elif peak_compliance > 1.6:
        return 'Type Ad'  # 高峰型
    else:
        return 'Type A'   # 正常型
```

#### 5.6 判定閾值摘要

```python
# 常數定義
NORMAL_PRESSURE_MIN = -100  # daPa
NORMAL_PRESSURE_MAX = 100   # daPa
COMPLIANCE_MIN_B = 0.1      # mL - Type B 上限
COMPLIANCE_MIN_A = 0.3      # mL - Type A 下限 (低於此為 As)
COMPLIANCE_MAX_A = 1.6      # mL - Type A 上限 (高於此為 Ad)
```

### 6. 助聽器選擇解析

```typescript
if (typeOfData.toLowerCase().includes('hearing instrument selection')) {
    const selectionParams = action.getElementsByTagName('HearingInstrumentSelection')[0];
    
    if (selectionParams) {
        const model = getText(selectionParams, 'InstrumentTypeName');
        const serial = getText(selectionParams, 'SerialNumber') || 'Unknown';
        
        if (model) {
            // 側邊判定：優先使用 SideCode
            let side: 'Left' | 'Right' | undefined;
            const sideCode = getText(selectionParams, 'SideCode');
            if (sideCode === '1') side = 'Left';
            else if (sideCode === '2') side = 'Right';
            
            // Fallback: 從 Description 判斷
            if (!side) {
                const descLower = description.toLowerCase();
                if (descLower.includes('right') || descLower.includes('右')) side = 'Right';
                else if (descLower.includes('left') || descLower.includes('左')) side = 'Left';
            }
            
            const instrument: HearingInstrument = {
                model,
                serialNumber: serial,
                earMold: getText(selectionParams, 'EarMoldText') || undefined,
                battery: getText(selectionParams, 'BatteryTypeCode') || undefined,
                date,
                timestamp: fullTimestamp,
                side
            };
            
            // 以分鐘級精度分組（同一分鐘內的雙耳設備會配對）
            const groupKey = fullTimestamp.includes('T')
                ? fullTimestamp.substring(0, 16)  // "2025-10-08T15:04"
                : fullTimestamp;
            
            if (!devicesMap[groupKey]) devicesMap[groupKey] = [];
            devicesMap[groupKey].push(instrument);
        }
    }
}
```

---

## XML 標籤對應表

### 病患資訊

| XML 標籤 | 欄位 | 說明 |
|----------|------|------|
| `<Patient>` | - | 病患資訊根節點 |
| `<FirstName>` | firstName | 名 |
| `<LastName>` | lastName | 姓 |
| `<NOAHPatientNumber>` | patientNumber | NOAH 病患編號 |
| `<PatientNumber>` | patientNumber | 備用病患編號 |
| `<DateofBirth>` | birthDate | 出生日期 |
| `<Gender>` | gender | 性別 |

### Action 層級

| XML 標籤 | 欄位 | 說明 |
|----------|------|------|
| `<TypeOfData>` | testType | 資料類型：Audiogram/Impedance |
| `<ActionDate>` | testDate | 測試日期時間 |
| `<Description>` | description | 測試描述 |

### 純音聽力

| XML 標籤 | 欄位 | 說明 |
|----------|------|------|
| `<ToneThresholdAudiogram>` | - | 純音閾值區塊 |
| `<StimulusSignalOutput>` | - | 輸出側/類型 (Right/Left/Bone) |
| `<TonePoints>` | - | 測試點容器 |
| `<StimulusFrequency>` | frequency | 頻率 (Hz) |
| `<StimulusLevel>` | intensity | 強度 (dB HL) |
| `<TonePointStatus>` | - | 狀態：Normal/Masked/NoResponse |
| `<MaskingFrequency>` | - | 遮蔽頻率 |
| `<MaskingLevel>` | - | 遮蔽強度 |

### 語音聽力

| XML 標籤 | 欄位 | 說明 |
|----------|------|------|
| `<SpeechReceptionThresholdAudiogram>` | - | SRT 區塊 |
| `<SpeechReceptionPoints>` | - | SRT 測試點 |
| `<SpeechDiscriminationAudiogram>` | - | SDS 區塊 |
| `<SpeechDiscriminationPoints>` | - | SDS 測試點 |
| `<ScorePercent>` | sds | 辨識率 (%) |
| `<SpeechMostComfortableLevel>` | - | MCL 區塊 |
| `<SpeechMostComfortablePoint>` | - | MCL 測試點 |
| `<StimulusLevel>` | srt/mcl | 刺激強度 (dB) |

### 中耳分析

| XML 標籤 | 欄位 | 說明 |
|----------|------|------|
| `<MaximumCompliance>` | peakCompliance | 最大順應性 |
| `<CanalVolume>` | canalVolume | 外耳道容積 |
| `<Gradient>` | gradient | 梯度 |
| `<CompliancePoint>` | - | 曲線點容器 |
| `<Pressure>` | pressure | 壓力 (daPa) |
| `<Compliance>` | - | 順應性容器 |
| `<ArgumentCompliance1>` | compliance | 順應性值 |

### 助聽器選擇

| XML 標籤 | 欄位 | 說明 |
|----------|------|------|
| `<HearingInstrumentSelection>` | - | 助聽器選擇區塊 |
| `<InstrumentTypeName>` | model | 型號名稱 |
| `<SerialNumber>` | serialNumber | 序號 |
| `<SideCode>` | side | 側邊 (1=Left, 2=Right) |
| `<EarMoldText>` | earMold | 耳模資訊 |
| `<BatteryTypeCode>` | battery | 電池型號 |

---

## 特殊處理邏輯

### 1. Session 合併策略

同一天、同類型的多個 Action 會合併為一個 Session：

```typescript
const key = `${date}|${testType}`;

if (!sessionMap[key]) {
    // 新建 Session
    sessionMap[key] = { ... };
} else {
    // 合併到現有 Session
    const s = sessionMap[key];
    s.leftEar.airConduction.push(...leftTone.airConduction);
    // ... 合併其他資料
    
    // 合併後排序
    s.leftEar.airConduction.sort((a, b) => a.frequency - b.frequency);
}
```

### 2. 雙耳設備配對

同一分鐘內記錄的設備會自動配對：

```typescript
const groupKey = fullTimestamp.substring(0, 16); // "2025-10-08T15:04"

// 配對邏輯
if (devs.length === 2 && !devs[0].side && !devs[1].side) {
    devs[0].side = 'Left';
    devs[1].side = 'Right';
}
```

### 3. 單位正規化

某些儀器的順應性值以 μL 記錄，需除以 100 轉換為 mL：

```typescript
const scaleFactor = (canalVol && canalVol > 5) ? 100 : 1;
```

---

## Python 實作建議

### 使用的套件

```python
import xml.etree.ElementTree as ET
import re
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
```

### 基本結構

```python
@dataclass
class AudioPoint:
    frequency: int
    intensity: int
    is_masked: bool = False
    is_no_response: bool = False

@dataclass
class EarData:
    air_conduction: List[AudioPoint]
    bone_conduction: List[AudioPoint]

@dataclass
class HearingSession:
    id: str
    test_date: str
    test_type: str
    left_ear: EarData
    right_ear: EarData
    # ... 其他欄位


def clean_xml(xml_string: str) -> str:
    """移除 XML namespace"""
    xml_string = re.sub(r'<[a-zA-Z0-9]+:([a-zA-Z0-9_\-]+)', r'<\1', xml_string)
    xml_string = re.sub(r'</[a-zA-Z0-9]+:([a-zA-Z0-9_\-]+)>', r'</\1>', xml_string)
    xml_string = re.sub(r'\sxmlns[^"]+\"[^"]+\"', '', xml_string)
    return xml_string


def get_text(parent: ET.Element, tag: str) -> Optional[str]:
    """取得子標籤文字"""
    node = parent.find(f'.//{tag}')
    return node.text if node is not None else None


def get_float(parent: ET.Element, tag: str) -> Optional[float]:
    """取得子標籤數值"""
    text = get_text(parent, tag)
    if text:
        try:
            return float(text)
        except ValueError:
            return None
    return None


def parse_hearing_xml(xml_string: str) -> List[HearingSession]:
    """主解析函數"""
    cleaned = clean_xml(xml_string)
    root = ET.fromstring(cleaned)
    
    sessions = {}
    
    for action in root.findall('.//Action'):
        type_of_data = get_text(action, 'TypeOfData') or ''
        action_date = get_text(action, 'ActionDate') or ''
        
        if 'audiogram' in type_of_data.lower():
            # 解析純音/語音
            pass
        elif 'impedance' in type_of_data.lower():
            # 解析中耳分析
            pass
        # ...
    
    return list(sessions.values())
```

### 關鍵注意事項

1. **Namespace 清除** - Python 的 ElementTree 對 namespace 處理較嚴格，建議先用正則清除
2. **遞迴查找** - 使用 `.//tag` 進行遞迴查找，等同於 `getElementsByTagName`
3. **空值處理** - Python 需明確處理 `None` 值
4. **日期解析** - 使用 `datetime.fromisoformat()` 解析 ISO 格式日期

---

## 附錄：完整型別定義

完整的 TypeScript 型別定義請參考原始碼：
- [types.ts](file:///c:/Users/bt-user/Desktop/hearing_system/hearing_assessment_fitting_review/src/types.ts)
- [xmlParser.ts](file:///c:/Users/bt-user/Desktop/hearing_system/hearing_assessment_fitting_review/src/services/xmlParser.ts)

---

*文件生成時間：2024-12-27*
