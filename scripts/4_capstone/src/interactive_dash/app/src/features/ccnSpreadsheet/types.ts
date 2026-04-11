import type { IMutField, IRow } from '@kanaries/graphic-walker/interfaces'

export interface ICCNSpreadsheetConfig {
    enabled: boolean
    datasetFingerprint: string
    datasetLabel?: string
    autosaveDebounceMs?: number
    syncDebounceMs?: number
    historyLimit?: number
}

export interface ICCNSharedDatasetBridgeConfig {
    enabled?: boolean
    bridgeId: string
    targetOrigin?: string
    messageType?: string
}

export interface ISpreadsheetCellSelection {
    rowIndex: number
    columnFid: string
}

export type TSpreadsheetSelectionKind = 'sheet' | 'row' | 'column' | 'cell'

export interface ISpreadsheetSelection {
    kind: TSpreadsheetSelectionKind
    rowIndex: number | null
    columnFid: string | null
    cell: ISpreadsheetCellSelection | null
}

export interface ISpreadsheetSnapshot {
    rows: IRow[]
    fields: IMutField[]
}

export type TSpreadsheetFileSource = 'json' | 'csv' | 'excel'
export type TSpreadsheetSaveFormat = TSpreadsheetFileSource

export interface ISpreadsheetFileHandle {
    name: string
    getFile: () => Promise<File>
    createWritable: () => Promise<{
        write: (data: Blob | ArrayBuffer | Uint8Array | string) => Promise<void>
        close: () => Promise<void>
    }>
}

export interface ISpreadsheetExternalFile {
    fileName: string
    source: TSpreadsheetFileSource
    worksheetName?: string
    fileHandle?: ISpreadsheetFileHandle | null
}

export interface IPersistedSheet extends ISpreadsheetSnapshot {
    id: string
    name: string
    kind: 'manual' | 'autosave'
    datasetFingerprint: string
    datasetLabel?: string
    updatedAt: number
}

export interface IImportedSpreadsheetSheet extends ISpreadsheetSnapshot, ISpreadsheetExternalFile {
    name: string
}

export interface ISharedDatasetSyncPayload extends ISpreadsheetSnapshot {
    type: string
    bridgeId: string
    sequence: number
    hasUploadedData: boolean
    datasetFingerprint: string
    datasetLabel: string
    sheetName: string
    fileName?: string
    source?: TSpreadsheetFileSource
    worksheetName?: string
}
