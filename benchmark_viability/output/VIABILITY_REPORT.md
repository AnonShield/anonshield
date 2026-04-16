# Viability Test Report: XFUND-PT Ground Truth Analysis

**Decision: GO**

**Reason:** Ranking inversion confirmed: 2 classical↔VLM pair(s) change order. VLMs improve +0.1143 more than classical engines when format penalty is removed.


## 1. Engine Comparison

| Engine | Type | CER_raw | CER_norm | CER_sorted | Token_F1 | Δ(raw→sort) | N |
|--------|------|---------|----------|------------|----------|-------------|---|
| doctr | classical | 0.2986 | 0.2809 | 0.1041 | 0.7985 | +0.1944 | 100 |
| easyocr | classical | 0.3267 | 0.2908 | 0.1564 | 0.7524 | +0.1703 | 100 |
| glm_ocr | VLM | 0.3193 | 0.2875 | 0.0926 | 0.9414 | +0.2267 | 93 |
| lighton_ocr | VLM | 0.6653 | 0.5051 | 0.3693 | 0.8674 | +0.2960 | 100 |
| rapidocr | classical | 0.3766 | 0.3524 | 0.4591 | 0.5702 | -0.0825 | 100 |
| surya | classical | 0.3148 | 0.2925 | 0.0418 | 0.9667 | +0.2730 | 100 |
| tesseract | classical | 0.3511 | 0.3130 | 0.1711 | 0.7466 | +0.1800 | 100 |

## 2. Format Penalty by Engine Family

- **VLM avg improvement** (raw→sorted): +0.2613
- **Classical avg improvement** (raw→sorted): +0.1470
- **Difference**: +0.1143

## 3. Rankings

| Rank | CER_raw | CER_sorted | Token_F1 |
|------|---------|------------|----------|
| 1 | doctr | surya | surya |
| 2 | surya | glm_ocr | glm_ocr |
| 3 | glm_ocr | doctr | lighton_ocr |
| 4 | easyocr | easyocr | doctr |
| 5 | tesseract | tesseract | easyocr |
| 6 | rapidocr | lighton_ocr | tesseract |
| 7 | lighton_ocr | rapidocr | rapidocr |

## 4. Classical↔VLM Inversions

Found **2** ranking inversion(s):

- **doctr** (classical) vs **glm_ocr** (VLM)
- **rapidocr** (classical) vs **lighton_ocr** (VLM)

## 5. Key Insight

The XFUND-PT ground truth concatenates form items in annotation order (questions and answers as separate items), producing a deconstructed text. VLMs read forms as a human would — structured, with labels inline (e.g., `Nome: Pedro C Santos`). Classical OCR engines produce fragmented text blocks closer to the GT's deconstructed format.

Standard CER measures edit distance between these two formats, conflating **layout fidelity** with **content accuracy**. CER_sorted removes the ordering penalty, isolating content errors.

