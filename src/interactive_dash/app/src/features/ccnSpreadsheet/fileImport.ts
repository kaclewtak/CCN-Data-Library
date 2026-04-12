import * as XLSX from 'xlsx'

import type { IMutField, IRow } from '@kanaries/graphic-walker/interfaces'

import { SPREADSHEET_FILE_PICKER_TYPES } from './fileTransfer'
import type { IImportedSpreadsheetSheet, ISpreadsheetFileHandle, ISpreadsheetSnapshot } from './types'
import { createBlankSheet, inferField, makeBlankRow, makeUniqueFieldId } from './utils'

type TFilePickerWindow = Window & {
    showOpenFilePicker?: (options?: Record<string, unknown>) => Promise<ISpreadsheetFileHandle[]>
}

export interface IParsedImportedSpreadsheetFile {
    fileName: string
    source: IImportedSpreadsheetSheet['source']
    sheets: IImportedSpreadsheetSheet[]
}

export const IMPORT_FILE_ACCEPT = '.json,.csv,.xls,.xlsx,.xlsm'

function stripFileExtension(fileName: string): string {
    return fileName.replace(/\.[^.]+$/, '')
}

function readFileAsText(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader()

        reader.onload = () => resolve(String(reader.result ?? ''))
        reader.onerror = () => reject(reader.error ?? new Error('The selected file could not be read.'))
        reader.readAsText(file)
    })
}

function readFileAsArrayBuffer(file: File): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader()

        reader.onload = () => resolve(reader.result as ArrayBuffer)
        reader.onerror = () => reject(reader.error ?? new Error('The selected file could not be read.'))
        reader.readAsArrayBuffer(file)
    })
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function normalizeCellValue(value: unknown): unknown {
    if (value instanceof Date) {
        return value.toISOString()
    }

    return value ?? null
}

function buildSnapshotFromObjectRecords(records: Record<string, unknown>[]): ISpreadsheetSnapshot {
    if (records.length === 0) {
        return createBlankSheet()
    }

    const keyOrder: string[] = []
    records.forEach((record) => {
        Object.keys(record).forEach((key) => {
            if (!keyOrder.includes(key)) {
                keyOrder.push(key)
            }
        })
    })

    const fields: IMutField[] = []
    keyOrder.forEach((key) => {
        const fieldId = makeUniqueFieldId(key, fields)
        const values = records.map((record) => normalizeCellValue(record[key]))
        fields.push(inferField(fieldId, key, values))
    })

    const rows = records.map((record) =>
        fields.reduce<IRow>((row, field, fieldIndex) => {
            row[field.fid] = normalizeCellValue(record[keyOrder[fieldIndex]])
            return row
        }, {}),
    )

    return { rows, fields }
}

function buildSnapshotFromStructuredJson(value: Record<string, unknown>): ISpreadsheetSnapshot | null {
    if (!Array.isArray(value.rows) || !Array.isArray(value.fields)) {
        return null
    }

    const rawFields = value.fields.filter(isRecord)
    if (rawFields.length === 0) {
        return createBlankSheet()
    }

    const fields: IMutField[] = []
    rawFields.forEach((rawField, fieldIndex) => {
        const rawName = typeof rawField.name === 'string' && rawField.name.trim().length > 0
            ? rawField.name.trim()
            : typeof rawField.fid === 'string' && rawField.fid.trim().length > 0
                ? rawField.fid.trim()
                : `Column ${fieldIndex + 1}`
        const fieldId = makeUniqueFieldId(typeof rawField.fid === 'string' && rawField.fid.trim().length > 0 ? rawField.fid : rawName, fields)
        const fallbackField = inferField(fieldId, rawName, [])

        fields.push({
            ...fallbackField,
            ...rawField,
            fid: fieldId,
            name: rawName,
            offset: 0,
        } as IMutField)
    })

    const rows = value.rows.length === 0
        ? [makeBlankRow(fields)]
        : value.rows.map((rawRow) => {
            if (!isRecord(rawRow)) {
                return makeBlankRow(fields)
            }

            return fields.reduce<IRow>((row, field, fieldIndex) => {
                const rawField = rawFields[fieldIndex]
                const fallbackFieldName = field.name ?? field.fid
                const sourceValue = rawRow[field.fid]
                    ?? (typeof rawField.fid === 'string' ? rawRow[rawField.fid] : undefined)
                    ?? rawRow[fallbackFieldName]

                row[field.fid] = normalizeCellValue(sourceValue)
                return row
            }, {})
        })

    const normalizedFields = fields.map((field) => {
        if (field.semanticType && field.analyticType) {
            return field
        }

        return {
            ...inferField(field.fid, field.name ?? field.fid, rows.map((row) => row[field.fid])),
            ...field,
        } as IMutField
    })

    return {
        rows,
        fields: normalizedFields,
    }
}

function buildSnapshotFromMatrix(matrix: unknown[][]): ISpreadsheetSnapshot {
    const nonEmptyRows = matrix.filter((row) => row.some((value) => value != null && String(value).trim().length > 0))
    if (nonEmptyRows.length === 0) {
        return createBlankSheet()
    }

    const headerRow = nonEmptyRows[0]
    const valueRows = nonEmptyRows.slice(1)
    const columnCount = Math.max(headerRow.length, ...valueRows.map((row) => row.length), 1)
    const fields: IMutField[] = []

    Array.from({ length: columnCount }, (_, columnIndex) => {
        const rawHeader = headerRow[columnIndex]
        const fieldName = rawHeader != null && String(rawHeader).trim().length > 0 ? String(rawHeader).trim() : `Column ${columnIndex + 1}`
        const fieldId = makeUniqueFieldId(fieldName, fields)
        const values = valueRows.map((row) => normalizeCellValue(row[columnIndex]))
        fields.push(inferField(fieldId, fieldName, values))
    })

    const rows = valueRows.length === 0
        ? [makeBlankRow(fields)]
        : valueRows.map((row) =>
            fields.reduce<IRow>((record, field, columnIndex) => {
                record[field.fid] = normalizeCellValue(row[columnIndex])
                return record
            }, {}),
        )

    return { rows, fields }
}

function buildImportedSheet(
    fileName: string,
    source: IImportedSpreadsheetSheet['source'],
    name: string,
    snapshot: ISpreadsheetSnapshot,
    worksheetName?: string,
    fileHandle?: ISpreadsheetFileHandle,
): IImportedSpreadsheetSheet {
    return {
        fileName,
        name,
        source,
        worksheetName,
        fileHandle,
        rows: snapshot.rows,
        fields: snapshot.fields,
    }
}

async function parseJsonFile(file: File, fileHandle?: ISpreadsheetFileHandle): Promise<IParsedImportedSpreadsheetFile> {
    const rawText = await readFileAsText(file)
    const parsedValue = JSON.parse(rawText) as unknown
    const defaultName = stripFileExtension(file.name)

    if (isRecord(parsedValue)) {
        const structuredSnapshot = buildSnapshotFromStructuredJson(parsedValue)
        if (structuredSnapshot) {
            const sheetName = typeof parsedValue.name === 'string' && parsedValue.name.trim().length > 0 ? parsedValue.name.trim() : defaultName

            return {
                fileName: file.name,
                source: 'json',
                sheets: [buildImportedSheet(file.name, 'json', sheetName, structuredSnapshot, undefined, fileHandle)],
            }
        }
    }

    if (Array.isArray(parsedValue) && parsedValue.every(isRecord)) {
        return {
            fileName: file.name,
            source: 'json',
            sheets: [buildImportedSheet(file.name, 'json', defaultName, buildSnapshotFromObjectRecords(parsedValue), undefined, fileHandle)],
        }
    }

    throw new Error('JSON imports must be a saved sheet object or an array of records.')
}

async function parseWorkbookFile(
    file: File,
    source: 'csv' | 'excel',
    fileHandle?: ISpreadsheetFileHandle,
): Promise<IParsedImportedSpreadsheetFile> {
    const baseName = stripFileExtension(file.name)
    const workbook = XLSX.read(await readFileAsArrayBuffer(file), {
        type: 'array',
        cellDates: true,
        raw: true,
    })

    const sheets = workbook.SheetNames.map((sheetName) => {
        const worksheet = workbook.Sheets[sheetName]
        const matrix = XLSX.utils.sheet_to_json<unknown[]>(worksheet, {
            header: 1,
            raw: true,
            defval: null,
            blankrows: false,
        })
        const snapshot = buildSnapshotFromMatrix(matrix)
        const importedName = source === 'excel' && workbook.SheetNames.length > 1 ? `${baseName} - ${sheetName}` : baseName

        return buildImportedSheet(file.name, source, importedName, snapshot, sheetName, fileHandle)
    })

    if (sheets.length === 0) {
        throw new Error('The selected file did not contain any readable sheets.')
    }

    return {
        fileName: file.name,
        source,
        sheets,
    }
}

export function supportsSpreadsheetOpenPicker(): boolean {
    return typeof window !== 'undefined' && typeof (window as TFilePickerWindow).showOpenFilePicker === 'function'
}

export async function pickAndParseImportedSpreadsheetFile(): Promise<IParsedImportedSpreadsheetFile | null> {
    const pickerWindow = window as TFilePickerWindow
    if (typeof pickerWindow.showOpenFilePicker !== 'function') {
        return null
    }

    try {
        const [fileHandle] = await pickerWindow.showOpenFilePicker({
            id: 'ccn-spreadsheet-files',
            excludeAcceptAllOption: true,
            multiple: false,
            types: SPREADSHEET_FILE_PICKER_TYPES,
        })
        if (!fileHandle) {
            return null
        }

        return parseImportedSpreadsheetFile(await fileHandle.getFile(), fileHandle)
    } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
            return null
        }

        throw error
    }
}

export async function parseImportedSpreadsheetFile(
    file: File,
    fileHandle?: ISpreadsheetFileHandle,
): Promise<IParsedImportedSpreadsheetFile> {
    const extension = file.name.split('.').pop()?.toLowerCase()

    if (extension === 'json') {
        return parseJsonFile(file, fileHandle)
    }

    if (extension === 'csv') {
        return parseWorkbookFile(file, 'csv', fileHandle)
    }

    if (extension === 'xls' || extension === 'xlsx' || extension === 'xlsm') {
        return parseWorkbookFile(file, 'excel', fileHandle)
    }

    throw new Error('Unsupported file type. Choose a JSON, CSV, or Excel workbook.')
}