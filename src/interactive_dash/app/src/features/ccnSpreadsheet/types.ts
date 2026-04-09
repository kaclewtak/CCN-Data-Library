import type { IMutField, IRow } from '@kanaries/graphic-walker/interfaces'

export interface ICCNSpreadsheetConfig {
    enabled: boolean
    datasetFingerprint: string
    datasetLabel?: string
    autosaveDebounceMs?: number
    syncDebounceMs?: number
    historyLimit?: number
}

export interface ISpreadsheetCellSelection {
    rowIndex: number
    columnFid: string
}

export interface ISpreadsheetSelection {
    rowIndex: number | null
    columnFid: string | null
    cell: ISpreadsheetCellSelection | null
}

export interface ISpreadsheetSnapshot {
    rows: IRow[]
    fields: IMutField[]
}

export interface IPersistedSheet extends ISpreadsheetSnapshot {
    id: string
    name: string
    kind: 'manual' | 'autosave'
    datasetFingerprint: string
    datasetLabel?: string
    updatedAt: number
}
