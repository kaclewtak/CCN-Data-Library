import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import type { IPersistedSheet } from './types'
import { getAutosaveSheetId, listSheetsForFingerprint, saveSheetRecord } from './persistence'

const SHEET_A: IPersistedSheet = {
    id: 'manual::alpha',
    kind: 'manual',
    name: 'Alpha',
    datasetFingerprint: 'fp-1',
    datasetLabel: 'Uploaded dataset',
    updatedAt: 1,
    rows: [{ study_id: 'A1' }],
    fields: [{ fid: 'study_id', name: 'Study ID', offset: 0, semanticType: 'nominal', analyticType: 'dimension' } as any],
}

const SHEET_B: IPersistedSheet = {
    id: getAutosaveSheetId('fp-1'),
    kind: 'autosave',
    name: 'Alpha Autosave',
    datasetFingerprint: 'fp-1',
    datasetLabel: 'Uploaded dataset',
    updatedAt: 2,
    rows: [{ study_id: 'A2' }],
    fields: [{ fid: 'study_id', name: 'Study ID', offset: 0, semanticType: 'nominal', analyticType: 'dimension' } as any],
}

describe('ccn spreadsheet persistence fallback', () => {
    beforeEach(() => {
        window.localStorage.clear()
    })

    afterEach(() => {
        window.localStorage.clear()
    })

    it('stores and retrieves sheets grouped by fingerprint', async () => {
        await saveSheetRecord(SHEET_A)
        await saveSheetRecord(SHEET_B)

        const sheets = await listSheetsForFingerprint('fp-1')

        expect(sheets).toHaveLength(2)
        expect(sheets[0].updatedAt).toBeGreaterThan(sheets[1].updatedAt)
        expect(sheets.map((sheet) => sheet.kind)).toEqual(['autosave', 'manual'])
    })
})
