import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type { IMutField, IRow } from '@kanaries/graphic-walker/interfaces'

import commonStore from '@/store/common'

import { saveSpreadsheetToComputer } from './fileTransfer'
import { getAutosaveSheetId, listSheetsForFingerprint, saveSheetRecord } from './persistence'
import type {
    ICCNSpreadsheetConfig,
    IImportedSpreadsheetSheet,
    IPersistedSheet,
    ISpreadsheetExternalFile,
    ISpreadsheetSelection,
    ISpreadsheetSnapshot,
    TSpreadsheetSaveFormat,
} from './types'
import {
    DEFAULT_AUTOSAVE_DEBOUNCE_MS,
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_SYNC_DEBOUNCE_MS,
    applyPaste,
    cloneFields,
    cloneRows,
    cloneSnapshot,
    columnToTsv,
    columnToValues,
    createBlankSheet,
    insertBlankColumn,
    insertBlankRow,
    insertColumns,
    insertRows,
    matrixToInsertedColumns,
    parseDelimitedText,
    removeColumn,
    removeRow,
    renameColumn,
    rowToTsv,
    rowToValues,
    sheetToTsv,
    updateCellValue,
} from './utils'
import type { IInsertedColumnData } from './utils'

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

type TSpreadsheetClipboard =
    | {
        kind: 'row'
        text: string
        rows: unknown[][]
    }
    | {
        kind: 'column'
        text: string
        columns: IInsertedColumnData[]
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
    saveDialogOpen: boolean
    savedSheets: IPersistedSheet[]
    currentExternalFile: ISpreadsheetExternalFile | null
    lastSavedAt: number | null
    selectionKind: ISpreadsheetSelection['kind']
    selectedRowIndex: number | null
    selectedColumnFid: string | null
    selectedCell: ISpreadsheetSelection['cell']
    selectionLabel: string
    setLoadDialogOpen: (open: boolean) => void
    setSaveDialogOpen: (open: boolean) => void
    selectRow: (rowIndex: number) => void
    selectColumn: (columnFid: string) => void
    selectCell: (rowIndex: number, columnFid: string) => void
    commitCellValue: (rowIndex: number, columnFid: string, rawValue: string) => void
    handleNewSheet: () => void
    handleSaveSheet: () => Promise<void>
    handleSaveBrowserSheet: (name: string) => Promise<void>
    handleSaveComputerSheet: (format: TSpreadsheetSaveFormat) => Promise<void>
    handleLoadSheet: (sheet: IPersistedSheet) => void
    handleImportSheet: (sheet: IImportedSpreadsheetSheet) => Promise<void>
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
    kind: 'sheet',
    rowIndex: null,
    columnFid: null,
    cell: null,
}

const NEW_SHEET_NAME_PATTERN = /^NewSheet(?:\[(\d+)\]|(\d+))$/i

function createBaseSheetName(config?: ICCNSpreadsheetConfig): string {
    return config?.datasetLabel?.trim() || 'Uploaded dataset'
}

function getActiveRowIndex(selection: ISpreadsheetSelection): number | null {
    if (selection.kind === 'row') {
        return selection.rowIndex
    }

    if (selection.kind === 'cell') {
        return selection.cell?.rowIndex ?? null
    }

    return null
}

function getActiveColumnId(selection: ISpreadsheetSelection): string | null {
    if (selection.kind === 'column') {
        return selection.columnFid
    }

    if (selection.kind === 'cell') {
        return selection.cell?.columnFid ?? null
    }

    return null
}

function getColumnIndex(fields: IMutField[], columnFid: string | null): number {
    if (!columnFid) {
        return -1
    }

    return fields.findIndex((field) => field.fid === columnFid)
}

function getNextGeneratedSheetName(names: string[]): string {
    const nextIndex = names.reduce((maxIndex, name) => {
        const match = NEW_SHEET_NAME_PATTERN.exec(name.trim())
        if (!match) {
            return maxIndex
        }

        const parsedIndex = Number(match[1] ?? match[2])
        return Number.isFinite(parsedIndex) ? Math.max(maxIndex, parsedIndex) : maxIndex
    }, 0)

    return `NewSheet[${nextIndex + 1}]`
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
    const [saveDialogOpen, setSaveDialogOpen] = useState(false)
    const [savedSheets, setSavedSheets] = useState<IPersistedSheet[]>([])
    const [currentExternalFile, setCurrentExternalFile] = useState<ISpreadsheetExternalFile | null>(null)
    const [lastSavedAt, setLastSavedAt] = useState<number | null>(null)
    const [selection, setSelection] = useState<ISpreadsheetSelection>(EMPTY_SELECTION)
    const [historyVersion, setHistoryVersion] = useState(0)
    const [persistenceReady, setPersistenceReady] = useState(false)
    const historyRef = useRef<ISpreadsheetSnapshot[]>([cloneSnapshot(baseSnapshotRef.current)])
    const historyIndexRef = useRef(0)
    const changeVersionRef = useRef(0)
    const clipboardRef = useRef<TSpreadsheetClipboard | null>(null)

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

            changeVersionRef.current += 1
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

    const persistAutosaveSnapshot = useCallback(
        async (snapshot: ISpreadsheetSnapshot, nextSheetName: string, updatedAt = Date.now()) => {
            if (!options.enabled || !options.config?.datasetFingerprint) {
                return null
            }

            await saveSheetRecord({
                id: getAutosaveSheetId(options.config.datasetFingerprint),
                kind: 'autosave',
                name: nextSheetName,
                datasetFingerprint: options.config.datasetFingerprint,
                datasetLabel: options.config.datasetLabel,
                updatedAt,
                rows: cloneRows(snapshot.rows),
                fields: cloneFields(snapshot.fields),
            })

            return updatedAt
        },
        [options.config, options.enabled],
    )

    useEffect(() => {
        setCurrentExternalFile(null)
        setSaveDialogOpen(false)

        if (!options.enabled || !options.config?.datasetFingerprint) {
            setPersistenceReady(true)
            return
        }

        setPersistenceReady(false)
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
                        dirty: false,
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

        void hydratePersistence()

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

        const snapshotVersion = changeVersionRef.current
        const timeoutId = window.setTimeout(async () => {
            const updatedAt = Date.now()
            await persistAutosaveSnapshot(currentSnapshot, sheetName, updatedAt)
            await refreshSavedSheets()

            if (changeVersionRef.current === snapshotVersion) {
                setLastSavedAt(updatedAt)
                setIsDirty(false)
            }
        }, options.config?.autosaveDebounceMs ?? DEFAULT_AUTOSAVE_DEBOUNCE_MS)

        return () => window.clearTimeout(timeoutId)
    }, [
        currentSnapshot,
        isDirty,
        options.config,
        options.enabled,
        persistAutosaveSnapshot,
        persistenceReady,
        refreshSavedSheets,
        sheetName,
    ])

    const selectRow = useCallback((rowIndex: number) => {
        setSelection({
            kind: 'row',
            rowIndex,
            columnFid: null,
            cell: null,
        })
    }, [])

    const selectColumn = useCallback((columnFid: string) => {
        setSelection({
            kind: 'column',
            rowIndex: null,
            columnFid,
            cell: null,
        })
    }, [])

    const selectCell = useCallback((rowIndex: number, columnFid: string) => {
        setSelection({
            kind: 'cell',
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
        const nextSheetName = getNextGeneratedSheetName([...savedSheets.map((sheet) => sheet.name), sheetName])
        const blankSnapshot = createBlankSheet()

        clipboardRef.current = null
        setCurrentExternalFile(null)
        setSelection(EMPTY_SELECTION)
        commitSnapshot(blankSnapshot, {
            dirty: true,
            historyMode: 'replace',
            nextSheetName: nextSheetName,
        })
        commonStore.setNotification(
            {
                type: 'info',
                title: 'CCN Addition',
                message: `Created ${nextSheetName}.`,
            },
            3500,
        )
    }, [commitSnapshot, savedSheets, sheetName])

    const persistManualSheet = useCallback(async (requestedName: string) => {
        if (!options.enabled || !options.config?.datasetFingerprint) {
            return null
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
            return null
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
        await persistAutosaveSnapshot(currentSnapshot, normalizedName, updatedAt)
        await refreshSavedSheets()
        setSheetName(normalizedName)
        setIsDirty(false)
        setLastSavedAt(updatedAt)

        return {
            normalizedName,
            updatedAt,
        }
    }, [currentSnapshot, options.config, options.enabled, persistAutosaveSnapshot, refreshSavedSheets, savedSheets])

    const handleSaveSheet = useCallback(async () => {
        setSaveDialogOpen(true)
    }, [])

    const handleSaveBrowserSheet = useCallback(async (requestedName: string) => {
        const persistedSheet = await persistManualSheet(requestedName)
        if (!persistedSheet) {
            return
        }

        setSaveDialogOpen(false)
        commonStore.setNotification(
            {
                type: 'success',
                title: 'CCN Addition',
                message: `Saved ${persistedSheet.normalizedName}.`,
            },
            3500,
        )
    }, [persistManualSheet])

    const handleSaveComputerSheet = useCallback(async (format: TSpreadsheetSaveFormat) => {
        const savedFile = await saveSpreadsheetToComputer({
            snapshot: currentSnapshot,
            sheetName,
            format,
            currentFile: currentExternalFile,
        })

        if (!savedFile) {
            return
        }

        const updatedAt = Date.now()

        if (options.enabled && options.config?.datasetFingerprint) {
            await persistAutosaveSnapshot(currentSnapshot, sheetName, updatedAt)
            await refreshSavedSheets()
        }

        setCurrentExternalFile(savedFile.externalFile)
        setIsDirty(false)
        setLastSavedAt(updatedAt)
        setSaveDialogOpen(false)
        commonStore.setNotification(
            {
                type: 'success',
                title: 'CCN Addition',
                message: savedFile.method === 'file-system-access'
                    ? `Saved ${savedFile.externalFile.fileName}.`
                    : `Downloaded ${savedFile.externalFile.fileName}.`,
            },
            3500,
        )
    }, [currentExternalFile, currentSnapshot, options.config, options.enabled, persistAutosaveSnapshot, refreshSavedSheets, sheetName])

    const handleLoadSheet = useCallback(
        (sheet: IPersistedSheet) => {
            clipboardRef.current = null
            commitSnapshot(
                {
                    rows: sheet.rows,
                    fields: sheet.fields,
                },
                {
                    dirty: false,
                    historyMode: 'replace',
                    lastSavedAt: sheet.updatedAt,
                    nextSheetName: sheet.name,
                },
            )
            setCurrentExternalFile(null)
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

    const handleImportSheet = useCallback(
        async (sheet: IImportedSpreadsheetSheet) => {
            const updatedAt = Date.now()

            if (options.enabled && options.config?.datasetFingerprint) {
                const existingSheet = savedSheets.find((savedSheet) => savedSheet.kind === 'manual' && savedSheet.name === sheet.name)
                await saveSheetRecord({
                    id: existingSheet?.id ?? `manual::${options.config.datasetFingerprint}::${sheet.name.toLowerCase().replace(/\s+/g, '_')}`,
                    kind: 'manual',
                    name: sheet.name,
                    datasetFingerprint: options.config.datasetFingerprint,
                    datasetLabel: options.config.datasetLabel,
                    updatedAt,
                    rows: cloneRows(sheet.rows),
                    fields: cloneFields(sheet.fields),
                })
                await persistAutosaveSnapshot(sheet, sheet.name, updatedAt)
                await refreshSavedSheets()
            }

            clipboardRef.current = null
            commitSnapshot(
                { rows: sheet.rows, fields: sheet.fields },
                {
                    dirty: false,
                    historyMode: 'replace',
                    lastSavedAt: updatedAt,
                    nextSheetName: sheet.name,
                },
            )
            setCurrentExternalFile({
                fileName: sheet.fileName,
                source: sheet.source,
                worksheetName: sheet.worksheetName,
                fileHandle: sheet.fileHandle ?? null,
            })
            setSelection(EMPTY_SELECTION)
            setLoadDialogOpen(false)
            commonStore.setNotification(
                {
                    type: 'success',
                    title: 'CCN Addition',
                    message: `Imported ${sheet.name}.`,
                },
                3500,
            )
        },
        [commitSnapshot, options.config, options.enabled, persistAutosaveSnapshot, refreshSavedSheets, savedSheets],
    )

    const handleAddRow = useCallback(() => {
        const selectedRowIndex = getActiveRowIndex(selection)
        const insertIndex = selection.kind === 'row' || selection.kind === 'cell' ? (selectedRowIndex ?? rows.length - 1) + 1 : rows.length
        const nextSnapshot = insertBlankRow(rows, fields, insertIndex)

        commitSnapshot(nextSnapshot)
        selectRow(nextSnapshot.rowIndex)
    }, [commitSnapshot, fields, rows, selectRow, selection])

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

        const rowIndex = getActiveRowIndex(selection) ?? (rows.length - 1)
        const nextSnapshot = removeRow(rows, fields, rowIndex)

        clipboardRef.current = null
        commitSnapshot(nextSnapshot)
        setSelection(EMPTY_SELECTION)
    }, [commitSnapshot, fields, rows, selection])

    const handleAddColumn = useCallback(() => {
        const requestedName = window.prompt('New column name', `Column ${fields.length + 1}`)
        if (requestedName == null) {
            return
        }

        const activeColumnIndex = getColumnIndex(fields, getActiveColumnId(selection))
        const insertIndex = activeColumnIndex >= 0 ? activeColumnIndex + 1 : fields.length
        const nextSnapshot = insertBlankColumn(rows, fields, insertIndex, requestedName)

        commitSnapshot(nextSnapshot)
        selectColumn(nextSnapshot.field.fid)
        notifyStructureChange('Added a column. Existing charts may need a quick review if they depend on column ordering or field names.')
    }, [commitSnapshot, fields, notifyStructureChange, rows, selectColumn, selection])

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

        const columnFid = getActiveColumnId(selection)
        if (!columnFid) {
            commonStore.setNotification(
                {
                    type: 'warning',
                    title: 'CCN Addition',
                    message: 'Select a column header or cell before removing a column.',
                },
                4000,
            )
            return
        }

        clipboardRef.current = null
        commitSnapshot(removeColumn(rows, fields, columnFid))
        setSelection(EMPTY_SELECTION)
        notifyStructureChange('Removed a column. Existing charts may need to be adjusted if that field was in use.')
    }, [commitSnapshot, fields, notifyStructureChange, rows, selection])

    const handleRenameColumn = useCallback(() => {
        const columnFid = getActiveColumnId(selection)
        const field = fields.find((item) => item.fid === columnFid)

        if (!field) {
            commonStore.setNotification(
                {
                    type: 'warning',
                    title: 'CCN Addition',
                    message: 'Select a column header or cell before renaming a column.',
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
        clipboardRef.current = null

        if (selection.kind === 'cell' && selection.cell) {
            valueToCopy = String(rows[selection.cell.rowIndex]?.[selection.cell.columnFid] ?? '')
        } else if (selection.kind === 'row' && selection.rowIndex != null) {
            valueToCopy = rowToTsv(rows[selection.rowIndex], fields)
            clipboardRef.current = {
                kind: 'row',
                text: valueToCopy,
                rows: [rowToValues(rows[selection.rowIndex], fields)],
            }
        } else if (selection.kind === 'column' && selection.columnFid) {
            const field = fields.find((item) => item.fid === selection.columnFid)
            if (field) {
                valueToCopy = columnToTsv(rows, field)
                clipboardRef.current = {
                    kind: 'column',
                    text: valueToCopy,
                    columns: [
                        {
                            name: field.name ?? field.fid,
                            values: columnToValues(rows, field),
                            field,
                        },
                    ],
                }
            }
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

        const structuredClipboard = clipboardRef.current != null && clipboardRef.current.text === clipboardText ? clipboardRef.current : null

        if (selection.kind === 'row' && selection.rowIndex != null) {
            const nextSnapshot = structuredClipboard?.kind === 'row'
                ? insertRows(rows, fields, selection.rowIndex, structuredClipboard.rows)
                : insertRows(rows, fields, selection.rowIndex, parseDelimitedText(clipboardText))

            commitSnapshot(nextSnapshot)
            selectRow(selection.rowIndex)

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

            return
        }

        if (selection.kind === 'column' && selection.columnFid) {
            const insertIndex = getColumnIndex(fields, selection.columnFid)
            if (insertIndex < 0) {
                return
            }

            const nextSnapshot = structuredClipboard?.kind === 'column'
                ? insertColumns(rows, fields, insertIndex, structuredClipboard.columns)
                : insertColumns(rows, fields, insertIndex, matrixToInsertedColumns(parseDelimitedText(clipboardText), fields.length))

            commitSnapshot(nextSnapshot)
            if (nextSnapshot.insertedFieldIds.length > 0) {
                selectColumn(nextSnapshot.insertedFieldIds[0])
            }
            return
        }

        const activeRowIndex = getActiveRowIndex(selection) ?? 0
        const activeColumnIndex = Math.max(0, getColumnIndex(fields, getActiveColumnId(selection)))
        const nextSnapshot = applyPaste(rows, fields, activeRowIndex, activeColumnIndex, clipboardText)

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
    }, [commitSnapshot, fields, rows, selectRow, selectColumn, selection])

    const selectionLabel = useMemo(() => {
        if (selection.kind === 'cell' && selection.cell) {
            const field = fields.find((item) => item.fid === selection.cell?.columnFid)
            return `Cell R${selection.cell.rowIndex + 1}, ${field?.name ?? selection.cell.columnFid}`
        }

        if (selection.kind === 'row' && selection.rowIndex != null) {
            return `Row ${selection.rowIndex + 1}`
        }

        if (selection.kind === 'column' && selection.columnFid) {
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
        saveDialogOpen,
        savedSheets,
        currentExternalFile,
        lastSavedAt,
        selectionKind: selection.kind,
        selectedRowIndex: selection.kind === 'row' ? selection.rowIndex : null,
        selectedColumnFid: selection.kind === 'column' ? selection.columnFid : null,
        selectedCell: selection.kind === 'cell' ? selection.cell : null,
        selectionLabel,
        setLoadDialogOpen,
        setSaveDialogOpen,
        selectRow,
        selectColumn,
        selectCell,
        commitCellValue,
        handleNewSheet,
        handleSaveSheet,
        handleSaveBrowserSheet,
        handleSaveComputerSheet,
        handleLoadSheet,
        handleImportSheet,
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
