import type { IMutField, IRow } from '@kanaries/graphic-walker/interfaces'
import { describe, expect, it } from 'vitest'

import { addColumn, applyPaste, createBlankSheet, insertColumns, insertRows, renameColumn, updateCellValue } from './utils'

function makeField(fid: string, name: string, semanticType: 'nominal' | 'quantitative' = 'nominal'): IMutField {
    return {
        fid,
        name,
        offset: 0,
        semanticType,
        analyticType: semanticType === 'quantitative' ? 'measure' : 'dimension',
    } as IMutField
}

describe('ccn spreadsheet utils', () => {
    it('creates a blank 1x1 sheet for new sheets', () => {
        const result = createBlankSheet()

        expect(result.fields).toHaveLength(1)
        expect(result.fields[0].name).toBe('Column 1')
        expect(result.rows).toEqual([{ column_1: null }])
    })

    it('adds a unique column with blank values', () => {
        const fields = [makeField('study_id', 'Study ID')]
        const rows = [{ study_id: 'A1' }] as IRow[]

        const result = addColumn(rows, fields, 'Study ID')

        expect(result.field.fid).toBe('study_id_1')
        expect(result.rows[0].study_id_1).toBeNull()
        expect(result.fields).toHaveLength(2)
    })

    it('renames a column without losing row data', () => {
        const fields = [makeField('study_id', 'Study ID')]
        const rows = [{ study_id: 'A1' }] as IRow[]

        const result = renameColumn(rows, fields, 'study_id', 'Core ID')

        expect(result.nextFieldId).toBe('core_id')
        expect(result.rows[0].core_id).toBe('A1')
        expect(result.fields[0].name).toBe('Core ID')
    })

    it('coerces edited numeric values using the existing field type', () => {
        const fields = [makeField('depth_cm', 'Depth (cm)', 'quantitative')]
        const rows = [{ depth_cm: 10 }] as IRow[]

        const result = updateCellValue(rows, fields, 0, 'depth_cm', '42')

        expect(result.rows[0].depth_cm).toBe(42)
        expect(result.fields[0].semanticType).toBe('quantitative')
    })

    it('inserts pasted rows at the selected row index', () => {
        const fields = [makeField('study_id', 'Study ID'), makeField('depth_cm', 'Depth (cm)', 'quantitative')]
        const rows = [{ study_id: 'A1', depth_cm: 5 }, { study_id: 'C3', depth_cm: 18 }] as IRow[]

        const result = insertRows(rows, fields, 1, [['B2', '12']])

        expect(result.insertedRowCount).toBe(1)
        expect(result.rows).toEqual([
            { study_id: 'A1', depth_cm: 5 },
            { study_id: 'B2', depth_cm: 12 },
            { study_id: 'C3', depth_cm: 18 },
        ])
    })

    it('inserts copied columns at the selected column index', () => {
        const fields = [makeField('study_id', 'Study ID'), makeField('depth_cm', 'Depth (cm)', 'quantitative')]
        const rows = [{ study_id: 'A1', depth_cm: 5 }] as IRow[]

        const result = insertColumns(rows, fields, 1, [{ name: 'Salinity', values: [30] }])

        expect(result.insertedFieldIds).toHaveLength(1)
        expect(result.fields[1].name).toBe('Salinity')
        expect(result.rows[0][result.insertedFieldIds[0]]).toBe(30)
    })

    it('pastes tabular clipboard content and truncates overflow columns', () => {
        const fields = [makeField('study_id', 'Study ID'), makeField('depth_cm', 'Depth (cm)', 'quantitative')]
        const rows = [{ study_id: 'A1', depth_cm: 5 }] as IRow[]

        const result = applyPaste(rows, fields, 0, 0, 'B2\t12\textra\nC3\t18')

        expect(result.rows).toHaveLength(2)
        expect(result.rows[0].study_id).toBe('B2')
        expect(result.rows[1].depth_cm).toBe(18)
        expect(result.truncatedColumns).toBe(true)
    })
})
