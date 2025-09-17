# Confidence Scoring System

## Overview

The Financial PDF Extraction system uses a sophisticated confidence scoring mechanism to assess the reliability of extracted financial attributes. This document explains how confidence scores are calculated and how to interpret them.

## Confidence Score Components

Each extracted attribute receives a confidence score (0-100%) based on four weighted factors:

### 1. Text Clarity (25% weight)
**Measures**: How clear and readable is the source text from the PDF

**Scoring Criteria**:
- **1.0 (100%)**: Perfect, clear text with no ambiguity
- **0.8-0.9 (80-90%)**: Minor formatting issues or slight ambiguity
- **0.6-0.7 (60-70%)**: Some OCR errors or unclear formatting
- **0.4-0.5 (40-50%)**: Significant text quality issues
- **0.0-0.3 (0-30%)**: Very poor text quality or unreadable

**Examples**:
- High clarity: "Total Revenue: $1,500,000"
- Medium clarity: "Total Revenue: $1,500,OOO" (OCR error with O instead of 0)
- Low clarity: "T0tal Rev3nue: $1,5OO,OOO" (multiple OCR errors)

### 2. Exact Match (30% weight)
**Measures**: How well the found text matches the expected attribute description

**Scoring Criteria**:
- **1.0 (100%)**: Perfect match with expected attribute name/label
- **0.8-0.9 (80-90%)**: Close match with minor variations in terminology
- **0.6-0.7 (60-70%)**: Reasonable match but requires interpretation
- **0.4-0.5 (40-50%)**: Weak match, significant interpretation needed
- **0.0-0.3 (0-30%)**: Very weak or no clear match

**Examples**:
- Perfect match: Looking for "Total Revenue" and finding "Total Revenue"
- Good match: Looking for "Total Revenue" and finding "Total Sales"
- Weak match: Looking for "Total Revenue" and finding "Income from Operations"

### 3. Context Match (25% weight)
**Measures**: Whether the value is found in the appropriate document section/context

**Scoring Criteria**:
- **1.0 (100%)**: Found in perfect context (e.g., income statement for revenue)
- **0.8-0.9 (80-90%)**: Found in appropriate section with minor context issues
- **0.6-0.7 (60-70%)**: Found in reasonable context but not ideal location
- **0.4-0.5 (40-50%)**: Found in questionable context
- **0.0-0.3 (0-30%)**: Found in wrong context or no clear context

**Examples**:
- Perfect context: Revenue found in "Consolidated Statements of Income"
- Good context: Revenue found in "Financial Summary" section
- Poor context: Revenue found in footnotes or unrelated section

### 4. Format Validity (20% weight)
**Measures**: Whether the extracted value is in the expected format

**Scoring Criteria**:
- **1.0 (100%)**: Perfect format (e.g., proper number format for currency)
- **0.8-0.9 (80-90%)**: Minor format issues but clearly interpretable
- **0.6-0.7 (60-70%)**: Some format issues requiring normalization
- **0.4-0.5 (40-50%)**: Significant format problems
- **0.0-0.3 (0-30%)**: Invalid or unrecognizable format

**Examples**:
- Perfect format: "1500000" for currency attribute
- Good format: "$1,500,000" (needs symbol removal)
- Poor format: "1.5M" or "One and a half million"

## Final Confidence Calculation

The overall confidence score is calculated using the weighted formula:

```
Confidence = (Text Clarity × 0.25) + (Exact Match × 0.30) + (Context Match × 0.25) + (Format Validity × 0.20)
```

### Example Calculation

For a "Total Revenue" extraction:
- Text Clarity: 0.95 (very clear text)
- Exact Match: 0.90 (found "Total Sales" instead of "Total Revenue")
- Context Match: 0.98 (found in income statement)
- Format Validity: 0.85 (had currency symbol that needed removal)

**Calculation**:
```
Confidence = (0.95 × 0.25) + (0.90 × 0.30) + (0.98 × 0.25) + (0.85 × 0.20)
           = 0.2375 + 0.27 + 0.245 + 0.17
           = 0.9225 (92.25%)
```

## Quality Interpretation

### High Quality (80-100%) 🟢
- **Reliability**: Very reliable extraction
- **Action**: Minimal review needed
- **Use Case**: Can be used directly in analysis
- **Characteristics**: Clear text, exact matches, proper context, correct format

### Medium Quality (50-79%) 🟡
- **Reliability**: Good extraction with some uncertainty
- **Action**: Verification recommended
- **Use Case**: Suitable for analysis with awareness of limitations
- **Characteristics**: Minor issues in one or more components

### Low Quality (0-49%) 🔴
- **Reliability**: Questionable extraction
- **Action**: Manual review and validation required
- **Use Case**: Should not be used without verification
- **Characteristics**: Significant issues in multiple components

## Confidence Score Applications

### 1. Data Quality Assessment
- Filter results by confidence threshold
- Identify documents requiring manual review
- Prioritize validation efforts

### 2. Automated Processing
- Set confidence thresholds for automated workflows
- Route low-confidence extractions to human reviewers
- Generate quality reports

### 3. Reporting and Analytics
- Include confidence indicators in reports
- Weight analysis based on confidence scores
- Provide transparency to end users

## Excel Report Integration

The confidence scoring system is fully integrated into the Excel reports:

### Data Quality Report Sheet
- **Overall confidence metrics** for each PDF
- **Component breakdown** (text clarity, exact match, context match, format validity)
- **Attribute-level analysis** showing confidence patterns across different financial metrics
- **Detailed explanation** of the scoring methodology

### Visual Indicators
- **Color coding**: Green (high), Yellow (medium), Red (low confidence)
- **Conditional formatting**: Automatically highlights low-confidence values
- **Charts and graphs**: Visual representation of confidence distributions

## Best Practices

### For Users
1. **Review low-confidence extractions** before using in analysis
2. **Understand the components** that contribute to confidence scores
3. **Use confidence thresholds** appropriate for your use case
4. **Validate critical financial metrics** regardless of confidence score

### For System Administrators
1. **Monitor confidence trends** to identify systematic issues
2. **Adjust thresholds** based on organizational risk tolerance
3. **Provide training** on confidence score interpretation
4. **Regular calibration** of the scoring system based on feedback

## Troubleshooting Low Confidence Scores

### Common Issues and Solutions

**Low Text Clarity**:
- Issue: Poor PDF quality, scanned documents
- Solution: Improve PDF quality, use higher resolution scans

**Low Exact Match**:
- Issue: Non-standard terminology in financial statements
- Solution: Update attribute descriptions, add synonyms

**Low Context Match**:
- Issue: Unusual document structure
- Solution: Review document layout, adjust extraction logic

**Low Format Validity**:
- Issue: Non-standard number formats
- Solution: Enhance format recognition patterns

## API Integration

The confidence scores are available through the API response:

```json
{
  "extracted_attributes": {
    "Total Revenue": {
      "value": "1500000",
      "confidence": 0.92,
      "confidence_breakdown": {
        "text_clarity": 0.95,
        "exact_match": 0.90,
        "context_match": 0.98,
        "format_validity": 0.85
      },
      "source_text": "Total Revenue: $1,500,000",
      "extraction_reasoning": "Found exact match in income statement with clear formatting"
    }
  }
}
```

This comprehensive confidence scoring system ensures transparency, reliability, and actionable insights for financial data extraction workflows.
