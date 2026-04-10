import * as XLSX from 'xlsx'

import { describe, expect, it } from 'vitest'

import { parseImportedSpreadsheetFile } from './fileImport'

describe('ccn spreadsheet file import', () => {
    it('parses a structured JSON spreadsheet export', async () => {
        const file = new File(
            [JSON.stringify({
                name: 'Saved Soil Sheet',
                rows: [{ study_id: 'A1', depth_cm: 12 }],
                fields: [
                    { fid: 'study_id', name: 'Study ID', semanticType: 'nominal', analyticType: 'dimension' },
                    { fid: 'depth_cm', name: 'Depth (cm)', semanticType: 'quantitative', analyticType: 'measure' },
                ],
            })],
            'saved-sheet.json',
            { type: 'application/json' },
        )

        const result = await parseImportedSpreadsheetFile(file)

        expect(result.source).toBe('json')
        expect(result.sheets).toHaveLength(1)
        expect(result.sheets[0].name).toBe('Saved Soil Sheet')
        expect(result.sheets[0].rows[0].depth_cm).toBe(12)
    })

    it('parses multi-sheet Excel workbooks into separate choices', async () => {
        const workbook = XLSX.utils.book_new()
        XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet([['Study ID'], ['A1']]), 'Sheet One')
        XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet([['Study ID'], ['B2']]), 'Sheet Two')

        const file = new File(
            [XLSX.write(workbook, { bookType: 'xlsx', type: 'array' })],
            'multi-sheet.xlsx',
            { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
        )

        const result = await parseImportedSpreadsheetFile(file)

        expect(result.source).toBe('excel')
        expect(result.sheets).toHaveLength(2)
        expect(result.sheets.map((sheet) => sheet.worksheetName)).toEqual(['Sheet One', 'Sheet Two'])
        expect(result.sheets[1].rows[0].study_id).toBe('B2')
    })
})