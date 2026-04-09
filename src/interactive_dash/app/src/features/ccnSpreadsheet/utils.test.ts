import type { IMutField, IRow } from '@kanaries/graphic-walker/interfaces'
import { describe, expect, it } from 'vitest'

import { addColumn, applyPaste, renameColumn, updateCellValue } from './utils'

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
