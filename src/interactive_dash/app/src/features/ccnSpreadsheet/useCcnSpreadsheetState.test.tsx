import { describe, expect, it } from 'vitest'

import { createSheetActivationCommitOptions } from './useCcnSpreadsheetState'

describe('useCcnSpreadsheetState', () => {
    it('creates immediate graph-sync commit options for sheet activation events', () => {
        expect(createSheetActivationCommitOptions(1234567890, 'uploaded-sheet')).toEqual({
            dirty: false,
            historyMode: 'replace',
            lastSavedAt: 1234567890,
            nextSheetName: 'uploaded-sheet',
            syncGraphSnapshot: true,
        })
    })
})