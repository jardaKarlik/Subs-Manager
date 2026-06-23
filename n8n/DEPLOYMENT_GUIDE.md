# n8n Wallet Workflow Fix - Deployment Guide

## Issue Fixed
**JSON Query Parameters formatting error** in the wallet workflow that caused: 
```
"[object Object]" is not valid JSON
```

## Affected Workflow
- **Workflow ID**: `OSgCQsBB52TNhmrg`
- **Workflow Name**: `wallet`
- **Node to Update**: "Wallet API Request" (HTTP Request node)

## Manual Deployment Steps

1. **Go to your n8n instance**
   ```
   https://n8n-production-36e3d.up.railway.app
   ```

2. **Open the "wallet" workflow**
   - Click on Workflows in the sidebar
   - Find and click "wallet"

3. **Edit the "Wallet API Request" node**
   - Double-click the "Wallet API Request" (HTTP Request node)
   - Look for the "Query Parameters" section

4. **Change the Query Parameter Format**
   
   **FROM (Current - BROKEN):**
   ```
   Specify Query → JSON
   jsonQuery: {
     "recordDate": "gte.{{ $today.plus({months: -3}).toISO() }}",
     "limit": 200,
     "offset": 0
   }
   ```
   
   **TO (Fixed):**
   ```
   Specify Query → Key-Value
   
   Add these parameters:
   - Name: recordDate
     Value: gte.{{ $today.plus({months: -3}).toISO() }}
   
   - Name: limit
     Value: 200
   
   - Name: offset
     Value: 0
   ```

5. **Save the workflow**
   - Click "Save" button
   - The workflow should now be error-free

## What Changed
- **Before**: Used `specifyQuery: "json"` with a JSON object (causes serialization to "[object Object]")
- **After**: Uses `specifyQuery: "keyValue"` with individual parameter key-value pairs (proper format)

## Verification
After deploying:
1. Execute the workflow (click "Test")
2. Check that it successfully fetches wallet records
3. Verify no JSON errors in execution logs

## Files in This Directory
- `OSgCQsBB52TNhmrg.json` - ✅ Fixed wallet workflow export
- `d5eGc6GDBqXrRYPr.json` - My workflow 2
- `qFTCjtwkY2RZGY8w.json` - M2 Firecrawl - Case 3
- `uU4swMRoF2nvJPsy.json` - My workflow
- `n8nac-config.json` - n8n sync configuration
