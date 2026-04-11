import type { IMutField, IRow } from '@kanaries/graphic-walker/interfaces'

import type {
    ICCNSharedDatasetBridgeConfig,
    IImportedSpreadsheetSheet,
    IPersistedSheet,
    ISharedDatasetSyncPayload,
    ISpreadsheetExternalFile,
    ISpreadsheetSnapshot,
} from './types'

export interface ISharedDatasetIdentity {
    datasetFingerprint: string
    datasetLabel: string
}

export const DEFAULT_SHARED_DATASET_MESSAGE_TYPE = 'ccn:shared-dataset-sync'

function stableSerialize(value: unknown): string {
    if (value == null) {
        return 'null'
    }

    if (Array.isArray(value)) {
        return `[${value.map((item) => stableSerialize(item)).join(',')}]`
    }

    if (typeof value === 'object') {
        const entries = Object.entries(value as Record<string, unknown>).sort(([left], [right]) => left.localeCompare(right))
        return `{${entries.map(([key, item]) => `${JSON.stringify(key)}:${stableSerialize(item)}`).join(',')}}`
    }

    return JSON.stringify(value)
}

function hashString(input: string): string {
    let hash = 2166136261

    for (let index = 0; index < input.length; index += 1) {
        hash ^= input.charCodeAt(index)
        hash = Math.imul(hash, 16777619)
    }

    return (hash >>> 0).toString(16).padStart(8, '0')
}

function normalizeField(field: IMutField) {
    return {
        fid: field.fid,
        name: field.name ?? field.fid,
        semanticType: field.semanticType ?? null,
        analyticType: field.analyticType ?? null,
    }
}

function normalizeRows(rows: IRow[], fields: IMutField[]): unknown[][] {
    return rows.map((row) => fields.map((field) => row[field.fid] ?? null))
}

function externalFilePayload(currentExternalFile: ISpreadsheetExternalFile | null | undefined) {
    if (!currentExternalFile) {
        return {}
    }

    return {
        fileName: currentExternalFile.fileName,
        source: currentExternalFile.source,
        worksheetName: currentExternalFile.worksheetName,
    }
}

export function buildDatasetFingerprint(snapshot: ISpreadsheetSnapshot): string {
    const serialized = stableSerialize({
        fields: snapshot.fields.map((field) => normalizeField(field)),
        rows: normalizeRows(snapshot.rows, snapshot.fields),
    })
    return `dataset::${hashString(serialized)}`
}

export function buildImportedDatasetIdentity(sheet: IImportedSpreadsheetSheet): ISharedDatasetIdentity {
    return {
        datasetFingerprint: buildDatasetFingerprint(sheet),
        datasetLabel: sheet.name,
    }
}

export function buildPersistedDatasetIdentity(
    sheet: Pick<IPersistedSheet, 'datasetFingerprint' | 'datasetLabel' | 'name'>,
): ISharedDatasetIdentity {
    return {
        datasetFingerprint: sheet.datasetFingerprint,
        datasetLabel: sheet.datasetLabel ?? sheet.name,
    }
}

export function resolveVisualizationDatasetFingerprint(args: {
    activeDatasetIdentity?: ISharedDatasetIdentity | null
    defaultDatasetFingerprint?: string | null
}): string {
    return args.activeDatasetIdentity?.datasetFingerprint ?? args.defaultDatasetFingerprint ?? 'bootstrap'
}

export function createSharedDatasetSyncPayload(args: {
    bridgeConfig: ICCNSharedDatasetBridgeConfig
    sequence: number
    datasetIdentity: ISharedDatasetIdentity
    sheetName: string
    snapshot: ISpreadsheetSnapshot
    currentExternalFile?: ISpreadsheetExternalFile | null
}): ISharedDatasetSyncPayload {
    return {
        type: args.bridgeConfig.messageType ?? DEFAULT_SHARED_DATASET_MESSAGE_TYPE,
        bridgeId: args.bridgeConfig.bridgeId,
        sequence: args.sequence,
        hasUploadedData: true,
        datasetFingerprint: args.datasetIdentity.datasetFingerprint,
        datasetLabel: args.datasetIdentity.datasetLabel,
        sheetName: args.sheetName,
        rows: args.snapshot.rows,
        fields: args.snapshot.fields,
        ...externalFilePayload(args.currentExternalFile),
    }
}

export function postSharedDatasetSyncPayload(
    payload: ISharedDatasetSyncPayload,
    bridgeConfig: ICCNSharedDatasetBridgeConfig,
): void {
    if (typeof window === 'undefined' || !bridgeConfig.enabled) {
        return
    }

    if (!window.parent || window.parent === window) {
        return
    }

    window.parent.postMessage(payload, bridgeConfig.targetOrigin ?? '*')
}