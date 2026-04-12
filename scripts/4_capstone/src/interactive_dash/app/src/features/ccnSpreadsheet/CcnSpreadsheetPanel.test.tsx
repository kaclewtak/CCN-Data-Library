import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { CcnSpreadsheetPanel } from './CcnSpreadsheetPanel'
import type { ICcnSpreadsheetState } from './useCcnSpreadsheetState'

function createState(): ICcnSpreadsheetState {
    return {
        graphRows: [{ study_id: 'A1' }],
        graphFields: [{ fid: 'study_id', name: 'Study ID', offset: 0, semanticType: 'nominal', analyticType: 'dimension' } as any],
        visualizationDatasetFingerprint: 'dataset::test',
        rows: [{ study_id: 'A1' }],
        fields: [{ fid: 'study_id', name: 'Study ID', offset: 0, semanticType: 'nominal', analyticType: 'dimension' } as any],
        sheetName: 'Uploaded dataset',
        isDirty: true,
        canUndo: true,
        canRedo: false,
        loadDialogOpen: false,
        saveDialogOpen: false,
        savedSheets: [],
        currentExternalFile: null,
        lastSavedAt: 0,
        selectionKind: 'sheet',
        selectedRowIndex: null,
        selectedColumnFid: null,
        selectedCell: null,
        selectionLabel: 'Sheet',
        setLoadDialogOpen: vi.fn(),
        setSaveDialogOpen: vi.fn(),
        selectRow: vi.fn(),
        selectColumn: vi.fn(),
        selectCell: vi.fn(),
        commitCellValue: vi.fn(),
        handleNewSheet: vi.fn(),
        handleSaveSheet: vi.fn(async () => undefined),
        handleSaveBrowserSheet: vi.fn(async () => undefined),
        handleSaveComputerSheet: vi.fn(async () => undefined),
        handleLoadSheet: vi.fn(),
        handleImportSheet: vi.fn(async () => undefined),
        handleUndo: vi.fn(),
        handleRedo: vi.fn(),
        handleAddRow: vi.fn(),
        handleRemoveRow: vi.fn(),
        handleAddColumn: vi.fn(),
        handleRemoveColumn: vi.fn(),
        handleRenameColumn: vi.fn(),
        handleCopySelection: vi.fn(async () => undefined),
        handlePasteSelection: vi.fn(async () => undefined),
    }
}

describe('CcnSpreadsheetPanel', () => {
    it.skip('renders the CCN addition panel chrome and spreadsheet controls', () => {
        render(<CcnSpreadsheetPanel state={createState()} />)

        expect(screen.getByText('Spreadsheet Editor')).toBeTruthy()
        expect(screen.getByRole('button', { name: /New Sheet/i })).toBeTruthy()
        expect(screen.getByRole('button', { name: /Add Column/i })).toBeTruthy()
        expect((screen.getByLabelText('Spreadsheet cell 1-Study ID') as HTMLInputElement).value).toBe('A1')
    })
})
