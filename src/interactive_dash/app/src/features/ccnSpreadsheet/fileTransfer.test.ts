import * as XLSX from 'xlsx'

import { describe, expect, it } from 'vitest'

import { createSpreadsheetFileExport } from './fileTransfer'

function readBlobAsText(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader()

        reader.onload = () => resolve(String(reader.result ?? ''))
        reader.onerror = () => reject(reader.error ?? new Error('The blob could not be read.'))
        reader.readAsText(blob)
    })
}

function readBlobAsArrayBuffer(blob: Blob): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader()

        reader.onload = () => resolve(reader.result as ArrayBuffer)
        reader.onerror = () => reject(reader.error ?? new Error('The blob could not be read.'))
        reader.readAsArrayBuffer(blob)
    })
}

const snapshot = {
    rows: [
        { study_id: 'A1', depth_cm: 12 },
        { study_id: 'B2', depth_cm: 34 },
    ],
    fields: [
        { fid: 'study_id', name: 'Study ID', offset: 0, semanticType: 'nominal', analyticType: 'dimension' } as any,
        { fid: 'depth_cm', name: 'Depth (cm)', offset: 0, semanticType: 'quantitative', analyticType: 'measure' } as any,
    ],
}

describe('ccn spreadsheet file transfer', () => {
    it('creates a structured JSON export', async () => {
        const fileExport = createSpreadsheetFileExport(snapshot, 'Saved Soil Sheet', 'json')
        const parsed = JSON.parse(await readBlobAsText(fileExport.content)) as {
            name: string
            rows: Array<{ depth_cm: number }>
            fields: Array<{ name: string }>
        }

        expect(fileExport.fileName).toBe('Saved Soil Sheet.json')
        expect(parsed.name).toBe('Saved Soil Sheet')
        expect(parsed.rows[1].depth_cm).toBe(34)
        expect(parsed.fields[0].name).toBe('Study ID')
    })

    it('creates a CSV export with headers and values', async () => {
        const fileExport = createSpreadsheetFileExport(snapshot, 'Saved Soil Sheet', 'csv')
        const csvText = await readBlobAsText(fileExport.content)

        expect(fileExport.fileName).toBe('Saved Soil Sheet.csv')
        expect(csvText).toContain('Study ID,Depth (cm)')
        expect(csvText).toContain('A1,12')
    })

    it('creates an Excel export with a worksheet named for the sheet', async () => {
        const fileExport = createSpreadsheetFileExport(snapshot, 'Saved Soil Sheet', 'excel')
        const workbook = XLSX.read(await readBlobAsArrayBuffer(fileExport.content), { type: 'array' })
        const worksheet = workbook.Sheets[workbook.SheetNames[0]]
        const matrix = XLSX.utils.sheet_to_json<string[]>(worksheet, { header: 1, raw: false })

        expect(fileExport.fileName).toBe('Saved Soil Sheet.xlsx')
        expect(workbook.SheetNames).toEqual(['Saved Soil Sheet'])
        expect(matrix[1]).toEqual(['A1', '12'])
    })
})