import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type { IMutField, IRow } from '@kanaries/graphic-walker/interfaces'

import commonStore from '@/store/common'

import { getAutosaveSheetId, listSheetsForFingerprint, saveSheetRecord } from './persistence'
import type { ICCNSpreadsheetConfig, IPersistedSheet, ISpreadsheetSelection, ISpreadsheetSnapshot } from './types'
import {
    DEFAULT_AUTOSAVE_DEBOUNCE_MS,
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_SYNC_DEBOUNCE_MS,
    addBlankRow,
    addColumn,
    applyPaste,
    cloneFields,
    cloneRows,
    cloneSnapshot,
    removeColumn,
    removeRow,
    renameColumn,
    rowToTsv,
    sheetToTsv,
    updateCellValue,
} from './utils'

interface IUseCcnSpreadsheetStateOptions {
    enabled: boolean
    config?: ICCNSpreadsheetConfig
    initialRows: IRow[]
    initialFields: IMutField[]
}

interface ICommitOptions {
    dirty?: boolean
    historyMode?: 'push' | 'replace' | 'none'
    lastSavedAt?: number | null
    nextSheetName?: string
}

export interface ICcnSpreadsheetState {
    graphRows: IRow[]
    graphFields: IMutField[]
    rows: IRow[]
    fields: IMutField[]
    sheetName: string
    isDirty: boolean
    canUndo: boolean
    canRedo: boolean
    loadDialogOpen: boolean
    savedSheets: IPersistedSheet[]
    lastSavedAt: number | null
    selectedRowIndex: number | null
    selectedColumnFid: string | null
    selectedCell: ISpreadsheetSelection['cell']
    selectionLabel: string
    setLoadDialogOpen: (open: boolean) => void
    selectRow: (rowIndex: number) => void
    selectColumn: (columnFid: string) => void
    selectCell: (rowIndex: number, columnFid: string) => void
    commitCellValue: (rowIndex: number, columnFid: string, rawValue: string) => void
    handleNewSheet: () => void
    handleSaveSheet: () => Promise<void>
    handleLoadSheet: (sheet: IPersistedSheet) => void
    handleUndo: () => void
    handleRedo: () => void
    handleAddRow: () => void
    handleRemoveRow: () => void
    handleAddColumn: () => void
    handleRemoveColumn: () => void
    handleRenameColumn: () => void
    handleCopySelection: () => Promise<void>
    handlePasteSelection: () => Promise<void>
}

const EMPTY_SELECTION: ISpreadsheetSelection = {
    rowIndex: null,
    columnFid: null,
    cell: null,
}

function createBaseSheetName(config?: ICCNSpreadsheetConfig): string {
    return config?.datasetLabel?.trim() || 'Uploaded dataset'
}

function getTargetRowIndex(selection: ISpreadsheetSelection, rowCount: number): number {
    if (selection.cell) {
        return selection.cell.rowIndex
    }

    if (selection.rowIndex != null) {
        return selection.rowIndex
    }

    return Math.max(0, rowCount - 1)
}

function getTargetColumnId(selection: ISpreadsheetSelection, fields: IMutField[]): string | null {
    if (selection.cell) {
        return selection.cell.columnFid
    }

    if (selection.columnFid) {
        return selection.columnFid
    }

    return fields.at(-1)?.fid ?? null
}

function getTargetColumnIndex(selection: ISpreadsheetSelection, fields: IMutField[]): number {
    const columnFid = getTargetColumnId(selection, fields)
    if (!columnFid) {
        return 0
    }

    const columnIndex = fields.findIndex((field) => field.fid === columnFid)
    return columnIndex >= 0 ? columnIndex : 0
}

export function useCcnSpreadsheetState(options: IUseCcnSpreadsheetStateOptions): ICcnSpreadsheetState {
    const baseSnapshotRef = useRef<ISpreadsheetSnapshot>({
        rows: cloneRows(options.initialRows),
        fields: cloneFields(options.initialFields),
    })
    const [rows, setRows] = useState<IRow[]>(() => cloneRows(baseSnapshotRef.current.rows))
    const [fields, setFields] = useState<IMutField[]>(() => cloneFields(baseSnapshotRef.current.fields))
    const [graphRows, setGraphRows] = useState<IRow[]>(() => cloneRows(baseSnapshotRef.current.rows))
    const [graphFields, setGraphFields] = useState<IMutField[]>(() => cloneFields(baseSnapshotRef.current.fields))
    const [sheetName, setSheetName] = useState(createBaseSheetName(options.config))
    const [isDirty, setIsDirty] = useState(false)
    const [loadDialogOpen, setLoadDialogOpen] = useState(false)
    const [savedSheets, setSavedSheets] = useState<IPersistedSheet[]>([])
    const [lastSavedAt, setLastSavedAt] = useState<number | null>(null)
    const [selection, setSelection] = useState<ISpreadsheetSelection>(EMPTY_SELECTION)
    const [historyVersion, setHistoryVersion] = useState(0)
    const [persistenceReady, setPersistenceReady] = useState(false)
    const historyRef = useRef<ISpreadsheetSnapshot[]>([cloneSnapshot(baseSnapshotRef.current)])
    const historyIndexRef = useRef(0)

    const currentSnapshot = useMemo<ISpreadsheetSnapshot>(
        () => ({ rows, fields }),
        [fields, rows],
    )

    const commitSnapshot = useCallback(
        (snapshot: ISpreadsheetSnapshot, commitOptions: ICommitOptions = {}) => {
            const nextSnapshot = cloneSnapshot(snapshot)
            const historyMode = commitOptions.historyMode ?? 'push'

            if (historyMode === 'replace') {
                historyRef.current = [cloneSnapshot(nextSnapshot)]
                historyIndexRef.current = 0
            } else if (historyMode === 'push') {
                const nextHistory = historyRef.current
                    .slice(0, historyIndexRef.current + 1)
                    .concat(cloneSnapshot(nextSnapshot))
                const historyLimit = options.config?.historyLimit ?? DEFAULT_HISTORY_LIMIT

                if (nextHistory.length > historyLimit) {
                    nextHistory.splice(0, nextHistory.length - historyLimit)
                }

                historyRef.current = nextHistory
                historyIndexRef.current = nextHistory.length - 1
            }

            setRows(nextSnapshot.rows)
            setFields(nextSnapshot.fields)
            setIsDirty(commitOptions.dirty ?? true)
            setLastSavedAt(commitOptions.lastSavedAt ?? null)

            if (commitOptions.nextSheetName) {
                setSheetName(commitOptions.nextSheetName)
            }

            setHistoryVersion((value) => value + 1)
        },
        [options.config?.historyLimit],
    )

    const refreshSavedSheets = useCallback(async () => {
        if (!options.enabled || !options.config?.datasetFingerprint) {
            setSavedSheets([])
            return
        }

        const nextSheets = await listSheetsForFingerprint(options.config.datasetFingerprint)
        setSavedSheets(nextSheets)
    }, [options.config?.datasetFingerprint, options.enabled])

    useEffect(() => {
        if (!options.enabled || !options.config?.datasetFingerprint) {
            setPersistenceReady(true)
            return
        }

        let cancelled = false

        const hydratePersistence = async () => {
            const nextSheets = await listSheetsForFingerprint(options.config!.datasetFingerprint)
            if (cancelled) {
                return
            }

            setSavedSheets(nextSheets)
            const autosaveSheet = nextSheets.find((sheet) => sheet.kind === 'autosave')

            if (autosaveSheet) {
                commitSnapshot(
                    { rows: autosaveSheet.rows, fields: autosaveSheet.fields },
                    {
                        dirty: true,
                        historyMode: 'replace',
                        lastSavedAt: autosaveSheet.updatedAt,
                        nextSheetName: autosaveSheet.name,
                    },
                )
                commonStore.setNotification(
                    {
                        type: 'info',
                        title: 'CCN Addition',
                        message: `Restored autosave for ${autosaveSheet.name}.`,
                    },
                    5000,
                )
            }

            setPersistenceReady(true)
        }

        hydratePersistence()

        return () => {
            cancelled = true
        }
    }, [commitSnapshot, options.config?.datasetFingerprint, options.enabled])

    useEffect(() => {
        if (!options.enabled) {
            return
        }

        const timeoutId = window.setTimeout(() => {
            setGraphRows(cloneRows(currentSnapshot.rows))
            setGraphFields(cloneFields(currentSnapshot.fields))
        }, options.config?.syncDebounceMs ?? DEFAULT_SYNC_DEBOUNCE_MS)

        return () => window.clearTimeout(timeoutId)
    }, [currentSnapshot, options.config?.syncDebounceMs, options.enabled])

    useEffect(() => {
        if (!options.enabled || !options.config?.datasetFingerprint || !persistenceReady || !isDirty) {
            return
        }

        const timeoutId = window.setTimeout(async () => {
            const updatedAt = Date.now()
            await saveSheetRecord({
                id: getAutosaveSheetId(options.config!.datasetFingerprint),
                kind: 'autosave',
                name: `${sheetName} Autosave`,
                datasetFingerprint: options.config!.datasetFingerprint,
                datasetLabel: options.config?.datasetLabel,
                updatedAt,
                rows: cloneRows(currentSnapshot.rows),
                fields: cloneFields(currentSnapshot.fields),
            })
            await refreshSavedSheets()
            setLastSavedAt(updatedAt)
        }, options.config?.autosaveDebounceMs ?? DEFAULT_AUTOSAVE_DEBOUNCE_MS)

        return () => window.clearTimeout(timeoutId)
    }, [
        currentSnapshot,
        isDirty,
        options.config,
        options.enabled,
        persistenceReady,
        refreshSavedSheets,
        sheetName,
    ])

    const selectRow = useCallback((rowIndex: number) => {
        setSelection({
            rowIndex,
            columnFid: null,
            cell: null,
        })
    }, [])

    const selectColumn = useCallback((columnFid: string) => {
        setSelection({
            rowIndex: null,
            columnFid,
            cell: null,
        })
    }, [])

    const selectCell = useCallback((rowIndex: number, columnFid: string) => {
        setSelection({
            rowIndex,
            columnFid,
            cell: { rowIndex, columnFid },
        })
    }, [])

    const notifyStructureChange = useCallback((message: string) => {
        commonStore.setNotification(
            {
                type: 'warning',
                title: 'CCN Addition',
                message,
            },
            6500,
        )
    }, [])

    const commitCellValue = useCallback(
        (rowIndex: number, columnFid: string, rawValue: string) => {
            const currentValue = rows[rowIndex]?.[columnFid]
            if (currentValue == null && rawValue.trim().length === 0) {
                return
            }

            if (String(currentValue ?? '') === rawValue) {
                return
            }

            commitSnapshot(updateCellValue(rows, fields, rowIndex, columnFid, rawValue))
        },
        [commitSnapshot, fields, rows],
    )

    const handleUndo = useCallback(() => {
        if (historyIndexRef.current === 0) {
            return
        }

        historyIndexRef.current -= 1
        const snapshot = historyRef.current[historyIndexRef.current]
        commitSnapshot(snapshot, { dirty: true, historyMode: 'none' })
    }, [commitSnapshot])

    const handleRedo = useCallback(() => {
        if (historyIndexRef.current >= historyRef.current.length - 1) {
            return
        }

        historyIndexRef.current += 1
        const snapshot = historyRef.current[historyIndexRef.current]
        commitSnapshot(snapshot, { dirty: true, historyMode: 'none' })
    }, [commitSnapshot])

    const handleNewSheet = useCallback(() => {
        if (!window.confirm('Reset the spreadsheet to the uploaded dataset?')) {
            return
        }

        setSelection(EMPTY_SELECTION)
        commitSnapshot(baseSnapshotRef.current, {
            dirty: false,
            historyMode: 'replace',
            nextSheetName: createBaseSheetName(options.config),
        })
        commonStore.setNotification(
            {
                type: 'info',
                title: 'CCN Addition',
                message: 'Reset the spreadsheet to the uploaded dataset.',
            },
            4000,
        )
    }, [commitSnapshot, options.config])

    const handleSaveSheet = useCallback(async () => {
        if (!options.enabled || !options.config?.datasetFingerprint) {
            return
        }

        const requestedName = window.prompt('Save sheet as', sheetName)
        if (requestedName == null) {
            return
        }

        const normalizedName = requestedName.trim()
        if (!normalizedName) {
            commonStore.setNotification(
                {
                    type: 'warning',
                    title: 'CCN Addition',
                    message: 'Sheet names cannot be blank.',
                },
                4000,
            )
            return
        }

        const existingSheet = savedSheets.find((sheet) => sheet.kind === 'manual' && sheet.name === normalizedName)
        const updatedAt = Date.now()

        await saveSheetRecord({
            id: existingSheet?.id ?? `manual::${options.config.datasetFingerprint}::${normalizedName.toLowerCase().replace(/\s+/g, '_')}`,
            kind: 'manual',
            name: normalizedName,
            datasetFingerprint: options.config.datasetFingerprint,
            datasetLabel: options.config.datasetLabel,
            updatedAt,
            rows: cloneRows(currentSnapshot.rows),
            fields: cloneFields(currentSnapshot.fields),
        })
        await refreshSavedSheets()
        setSheetName(normalizedName)
        setIsDirty(false)
        setLastSavedAt(updatedAt)
        commonStore.setNotification(
            {
                type: 'success',
                title: 'CCN Addition',
                message: `Saved ${normalizedName}.`,
            },
            3500,
        )
    }, [currentSnapshot, options.config, options.enabled, refreshSavedSheets, savedSheets, sheetName])

    const handleLoadSheet = useCallback(
        (sheet: IPersistedSheet) => {
            commitSnapshot(
                {
                    rows: sheet.rows,
                    fields: sheet.fields,
                },
                {
                    dirty: sheet.kind !== 'manual',
                    historyMode: 'replace',
                    lastSavedAt: sheet.updatedAt,
                    nextSheetName: sheet.name,
                },
            )
            setSelection(EMPTY_SELECTION)
            setLoadDialogOpen(false)
            commonStore.setNotification(
                {
                    type: 'info',
                    title: 'CCN Addition',
                    message: `Loaded ${sheet.name}.`,
                },
                3500,
            )
        },
        [commitSnapshot],
    )

    const handleAddRow = useCallback(() => {
        const nextSnapshot = addBlankRow(rows, fields)
        commitSnapshot(nextSnapshot)
        selectRow(nextSnapshot.rows.length - 1)
    }, [commitSnapshot, fields, rows, selectRow])

    const handleRemoveRow = useCallback(() => {
        if (rows.length === 0) {
            commonStore.setNotification(
                {
                    type: 'warning',
                    title: 'CCN Addition',
                    message: 'There are no rows to remove.',
                },
                3500,
            )
            return
        }

        const rowIndex = getTargetRowIndex(selection, rows.length)
        const nextSnapshot = removeRow(rows, fields, rowIndex)
        commitSnapshot(nextSnapshot)
        setSelection(EMPTY_SELECTION)
    }, [commitSnapshot, fields, rows, selection])

    const handleAddColumn = useCallback(() => {
        const requestedName = window.prompt('New column name', `Column ${fields.length + 1}`)
        if (requestedName == null) {
            return
        }

        const nextSnapshot = addColumn(rows, fields, requestedName)
        commitSnapshot(nextSnapshot)
        selectColumn(nextSnapshot.field.fid)
        notifyStructureChange('Added a column. Existing charts may need a quick review if they depend on column ordering or field names.')
    }, [commitSnapshot, fields, notifyStructureChange, rows, selectColumn])

    const handleRemoveColumn = useCallback(() => {
        if (fields.length <= 1) {
            commonStore.setNotification(
                {
                    type: 'warning',
                    title: 'CCN Addition',
                    message: 'The last remaining column cannot be removed.',
                },
                4000,
            )
            return
        }

        const columnFid = getTargetColumnId(selection, fields)
        if (!columnFid) {
            return
        }

        commitSnapshot(removeColumn(rows, fields, columnFid))
        setSelection(EMPTY_SELECTION)
        notifyStructureChange('Removed a column. Existing charts may need to be adjusted if that field was in use.')
    }, [commitSnapshot, fields, notifyStructureChange, rows, selection])

    const handleRenameColumn = useCallback(() => {
        const columnFid = getTargetColumnId(selection, fields)
        const field = fields.find((item) => item.fid === columnFid)

        if (!field) {
            commonStore.setNotification(
                {
                    type: 'warning',
                    title: 'CCN Addition',
                    message: 'Select a column header before renaming a column.',
                },
                4000,
            )
            return
        }

        const requestedName = window.prompt('Rename column', field.name)
        if (requestedName == null) {
            return
        }

        const nextSnapshot = renameColumn(rows, fields, field.fid, requestedName)
        commitSnapshot(nextSnapshot)
        selectColumn(nextSnapshot.nextFieldId)
        notifyStructureChange('Renamed a column. Existing charts may need to be adjusted if that field name is referenced.')
    }, [commitSnapshot, fields, notifyStructureChange, rows, selection, selectColumn])

    const handleCopySelection = useCallback(async () => {
        if (!navigator.clipboard?.writeText) {
            commonStore.setNotification(
                {
                    type: 'warning',
                    title: 'CCN Addition',
                    message: 'Clipboard access is not available in this browser context.',
                },
                4000,
            )
            return
        }

        let valueToCopy = sheetToTsv(rows, fields)

        if (selection.cell) {
            valueToCopy = String(rows[selection.cell.rowIndex]?.[selection.cell.columnFid] ?? '')
        } else if (selection.rowIndex != null) {
            valueToCopy = rowToTsv(rows[selection.rowIndex], fields)
        }

        await navigator.clipboard.writeText(valueToCopy)
        commonStore.setNotification(
            {
                type: 'success',
                title: 'CCN Addition',
                message: 'Copied the current spreadsheet selection to the clipboard.',
            },
            3000,
        )
    }, [fields, rows, selection])

    const handlePasteSelection = useCallback(async () => {
        if (!navigator.clipboard?.readText) {
            commonStore.setNotification(
                {
                    type: 'warning',
                    title: 'CCN Addition',
                    message: 'Clipboard access is not available in this browser context.',
                },
                4000,
            )
            return
        }

        const clipboardText = await navigator.clipboard.readText()
        if (!clipboardText) {
            return
        }

        const rowIndex = selection.cell?.rowIndex ?? selection.rowIndex ?? 0
        const columnIndex = getTargetColumnIndex(selection, fields)
        const nextSnapshot = applyPaste(rows, fields, rowIndex, columnIndex, clipboardText)

        commitSnapshot(nextSnapshot)

        if (nextSnapshot.truncatedColumns) {
            commonStore.setNotification(
                {
                    type: 'warning',
                    title: 'CCN Addition',
                    message: 'Pasted values that extended beyond the current columns were truncated.',
                },
                4500,
            )
        }
    }, [commitSnapshot, fields, rows, selection])

    const selectionLabel = useMemo(() => {
        if (selection.cell) {
            const field = fields.find((item) => item.fid === selection.cell?.columnFid)
            return `Cell R${selection.cell.rowIndex + 1}, ${field?.name ?? selection.cell.columnFid}`
        }

        if (selection.rowIndex != null) {
            return `Row ${selection.rowIndex + 1}`
        }

        if (selection.columnFid) {
            const field = fields.find((item) => item.fid === selection.columnFid)
            return `Column ${field?.name ?? selection.columnFid}`
        }

        return 'Sheet'
    }, [fields, selection])

    return {
        graphRows,
        graphFields,
        rows,
        fields,
        sheetName,
        isDirty,
        canUndo: historyIndexRef.current > 0,
        canRedo: historyIndexRef.current < historyRef.current.length - 1,
        loadDialogOpen,
        savedSheets,
        lastSavedAt,
        selectedRowIndex: selection.rowIndex,
        selectedColumnFid: selection.columnFid,
        selectedCell: selection.cell,
        selectionLabel,
        setLoadDialogOpen,
        selectRow,
        selectColumn,
        selectCell,
        commitCellValue,
        handleNewSheet,
        handleSaveSheet,
        handleLoadSheet,
        handleUndo,
        handleRedo,
        handleAddRow,
        handleRemoveRow,
        handleAddColumn,
        handleRemoveColumn,
        handleRenameColumn,
        handleCopySelection,
        handlePasteSelection,
    }
}
