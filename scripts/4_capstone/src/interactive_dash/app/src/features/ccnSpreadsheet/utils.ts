import type { IMutField, IRow } from '@kanaries/graphic-walker/interfaces'

import type { ISpreadsheetSnapshot } from './types'

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}/

export const DEFAULT_AUTOSAVE_DEBOUNCE_MS = 2500
export const DEFAULT_HISTORY_LIMIT = 50
export const DEFAULT_SYNC_DEBOUNCE_MS = 350

export function cloneRows(rows: IRow[]): IRow[] {
    return rows.map((row) => ({ ...row }))
}

export function cloneFields(fields: IMutField[]): IMutField[] {
    return fields.map((field) => ({ ...field }))
}

export function cloneSnapshot(snapshot: ISpreadsheetSnapshot): ISpreadsheetSnapshot {
    return {
        rows: cloneRows(snapshot.rows),
        fields: cloneFields(snapshot.fields),
    }
}

export function displayCellValue(value: unknown): string {
    if (value == null) {
        return ''
    }
    if (value instanceof Date) {
        return value.toISOString()
    }
    return String(value)
}

export function serializeCellValue(value: unknown): string {
    if (value == null) {
        return 'null'
    }
    if (typeof value === 'object') {
        return JSON.stringify(value)
    }
    return String(value)
}

export function makeBlankRow(fields: IMutField[]): IRow {
    return fields.reduce<IRow>((row, field) => {
        row[field.fid] = null
        return row
    }, {})
}

export function makeUniqueFieldId(preferredName: string, fields: IMutField[]): string {
    const existingIds = new Set(fields.map((field) => field.fid))
    const baseId = preferredName
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '') || 'column'

    let candidate = baseId
    let index = 1

    while (existingIds.has(candidate)) {
        candidate = `${baseId}_${index}`
        index += 1
    }

    return candidate
}

function inferValueKind(values: unknown[]): 'number' | 'date' | 'string' {
    for (const value of values) {
        if (value == null || value === '') {
            continue
        }
        if (typeof value === 'number') {
            return 'number'
        }
        if (typeof value === 'string') {
            const trimmed = value.trim()
            if (trimmed.length === 0) {
                continue
            }
            if (DATE_PATTERN.test(trimmed) && !Number.isNaN(Date.parse(trimmed))) {
                return 'date'
            }
            if (!Number.isNaN(Number(trimmed)) && trimmed !== '') {
                return 'number'
            }
            return 'string'
        }
        if (value instanceof Date) {
            return 'date'
        }
        return 'string'
    }

    return 'string'
}

export function inferField(fieldId: string, fieldName: string, values: unknown[]): IMutField {
    const kind = inferValueKind(values)

    if (kind === 'number') {
        return {
            fid: fieldId,
            name: fieldName,
            offset: 0,
            semanticType: 'quantitative',
            analyticType: 'measure',
        } as IMutField
    }

    if (kind === 'date') {
        return {
            fid: fieldId,
            name: fieldName,
            offset: 0,
            semanticType: 'temporal',
            analyticType: 'dimension',
        } as IMutField
    }

    return {
        fid: fieldId,
        name: fieldName,
        offset: 0,
        semanticType: 'nominal',
        analyticType: 'dimension',
    } as IMutField
}

export function rebuildField(field: IMutField, rows: IRow[]): IMutField {
    const values = rows.map((row) => row[field.fid])
    return {
        ...field,
        ...inferField(field.fid, field.name ?? field.fid, values),
    }
}

export function rebuildFields(rows: IRow[], fields: IMutField[]): IMutField[] {
    return fields.map((field) => rebuildField(field, rows))
}

export function coerceEditedValue(rawValue: string, referenceValue: unknown, field: IMutField): unknown {
    const trimmed = rawValue.trim()

    if (trimmed.length === 0) {
        return null
    }

    if (typeof referenceValue === 'boolean') {
        return trimmed.toLowerCase() === 'true'
    }

    if (typeof referenceValue === 'number' || field.semanticType === 'quantitative' || field.analyticType === 'measure') {
        const numericValue = Number(trimmed)
        return Number.isFinite(numericValue) ? numericValue : rawValue
    }

    if (referenceValue instanceof Date || field.semanticType === 'temporal') {
        const timestamp = Date.parse(trimmed)
        return Number.isNaN(timestamp) ? rawValue : new Date(timestamp).toISOString()
    }

    if (trimmed.toLowerCase() === 'true') {
        return true
    }

    if (trimmed.toLowerCase() === 'false') {
        return false
    }

    return rawValue
}

export function updateCellValue(
    rows: IRow[],
    fields: IMutField[],
    rowIndex: number,
    columnFid: string,
    rawValue: string,
): ISpreadsheetSnapshot {
    const column = fields.find((field) => field.fid === columnFid)

    if (!column || rowIndex < 0 || rowIndex >= rows.length) {
        return {
            rows: cloneRows(rows),
            fields: cloneFields(fields),
        }
    }

    const nextRows = cloneRows(rows)
    const currentRow = nextRows[rowIndex]
    nextRows[rowIndex] = {
        ...currentRow,
        [columnFid]: coerceEditedValue(rawValue, currentRow[columnFid], column),
    }

    const nextFields = fields.map((field) => {
        if (field.fid !== columnFid) {
            return { ...field }
        }

        return rebuildField(field, nextRows)
    })

    return {
        rows: nextRows,
        fields: nextFields,
    }
}

export function addBlankRow(rows: IRow[], fields: IMutField[]): ISpreadsheetSnapshot {
    return {
        rows: [...cloneRows(rows), makeBlankRow(fields)],
        fields: cloneFields(fields),
    }
}

export function removeRow(rows: IRow[], fields: IMutField[], rowIndex: number): ISpreadsheetSnapshot {
    if (rowIndex < 0 || rowIndex >= rows.length) {
        return {
            rows: cloneRows(rows),
            fields: cloneFields(fields),
        }
    }

    return {
        rows: cloneRows(rows).filter((_, index) => index !== rowIndex),
        fields: cloneFields(fields),
    }
}

export function addColumn(rows: IRow[], fields: IMutField[], requestedName: string): ISpreadsheetSnapshot & { field: IMutField } {
    const fieldName = requestedName.trim() || `Column ${fields.length + 1}`
    const fieldId = makeUniqueFieldId(fieldName, fields)
    const field = inferField(fieldId, fieldName, [])
    const nextRows = rows.map((row) => ({
        ...row,
        [fieldId]: null,
    }))

    return {
        rows: nextRows,
        fields: [...cloneFields(fields), field],
        field,
    }
}

export function removeColumn(rows: IRow[], fields: IMutField[], columnFid: string): ISpreadsheetSnapshot {
    const nextFields = fields.filter((field) => field.fid !== columnFid).map((field) => ({ ...field }))
    const nextRows = rows.map((row) => {
        const nextRow = {} as IRow

        nextFields.forEach((field) => {
            nextRow[field.fid] = row[field.fid]
        })

        return nextRow
    })

    return {
        rows: nextRows,
        fields: nextFields,
    }
}

export function renameColumn(
    rows: IRow[],
    fields: IMutField[],
    columnFid: string,
    requestedName: string,
): ISpreadsheetSnapshot & { nextFieldId: string } {
    const currentField = fields.find((field) => field.fid === columnFid)
    const fieldName = requestedName.trim() || currentField?.name || columnFid
    const nextFieldId = makeUniqueFieldId(fieldName, fields.filter((field) => field.fid !== columnFid))
    const nextFields = fields.map((field) => {
        if (field.fid !== columnFid) {
            return { ...field }
        }

        return rebuildField(
            {
                ...field,
                fid: nextFieldId,
                name: fieldName,
            },
            rows.map((row) => ({
                ...row,
                [nextFieldId]: row[columnFid],
            })),
        )
    })

    const nextRows = rows.map((row) => {
        const nextRow = {} as IRow

        fields.forEach((field) => {
            const nextKey = field.fid === columnFid ? nextFieldId : field.fid
            nextRow[nextKey] = row[field.fid]
        })

        return nextRow
    })

    return {
        rows: nextRows,
        fields: nextFields,
        nextFieldId,
    }
}

export function sheetToTsv(rows: IRow[], fields: IMutField[]): string {
    const headerLine = fields.map((field) => field.name).join('\t')
    const valueLines = rows.map((row) => fields.map((field) => displayCellValue(row[field.fid])).join('\t'))

    return [headerLine, ...valueLines].join('\n')
}

export function rowToTsv(row: IRow, fields: IMutField[]): string {
    return fields.map((field) => displayCellValue(row[field.fid])).join('\t')
}

export function applyPaste(
    rows: IRow[],
    fields: IMutField[],
    startRowIndex: number,
    startColumnIndex: number,
    clipboardText: string,
): ISpreadsheetSnapshot & { truncatedColumns: boolean } {
    const lineItems = clipboardText.replace(/\r\n/g, '\n').split('\n')
    const lines = lineItems.at(-1) === '' ? lineItems.slice(0, -1) : lineItems
    const nextRows = cloneRows(rows)
    const nextFields = cloneFields(fields)
    const changedColumns = new Set<string>()
    let truncatedColumns = false

    lines.forEach((line, rowOffset) => {
        const targetRowIndex = startRowIndex + rowOffset
        const values = line.split('\t')

        while (nextRows.length <= targetRowIndex) {
            nextRows.push(makeBlankRow(nextFields))
        }

        values.forEach((value, columnOffset) => {
            const targetColumnIndex = startColumnIndex + columnOffset

            if (targetColumnIndex >= nextFields.length) {
                truncatedColumns = true
                return
            }

            const field = nextFields[targetColumnIndex]
            const currentValue = nextRows[targetRowIndex][field.fid]
            nextRows[targetRowIndex] = {
                ...nextRows[targetRowIndex],
                [field.fid]: coerceEditedValue(value, currentValue, field),
            }
            changedColumns.add(field.fid)
        })
    })

    const rebuiltFields = nextFields.map((field) => {
        if (!changedColumns.has(field.fid)) {
            return field
        }
        return rebuildField(field, nextRows)
    })

    return {
        rows: nextRows,
        fields: rebuiltFields,
        truncatedColumns,
    }
}
