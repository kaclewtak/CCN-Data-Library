import * as XLSX from 'xlsx'

import type { IMutField, IRow } from '@kanaries/graphic-walker/interfaces'

import type {
    ISpreadsheetExternalFile,
    ISpreadsheetFileHandle,
    ISpreadsheetSnapshot,
    TSpreadsheetFileSource,
    TSpreadsheetSaveFormat,
} from './types'

type TFilePickerWindow = Window & {
    showSaveFilePicker?: (options?: Record<string, unknown>) => Promise<ISpreadsheetFileHandle>
}

interface ISpreadsheetSaveFormatOption {
    format: TSpreadsheetSaveFormat
    label: string
    description: string
}

interface ISpreadsheetFormatMetadata {
    extension: string
    label: string
    mimeType: string
    pickerType: Record<string, unknown>
}

export interface ISpreadsheetFileExport {
    fileName: string
    mimeType: string
    content: Blob
}

export interface ISaveSpreadsheetToComputerOptions {
    snapshot: ISpreadsheetSnapshot
    sheetName: string
    format: TSpreadsheetSaveFormat
    currentFile?: ISpreadsheetExternalFile | null
}

export interface ISaveSpreadsheetToComputerResult {
    externalFile: ISpreadsheetExternalFile
    method: 'file-system-access' | 'download'
}

const FILE_PICKER_ID = 'ccn-spreadsheet-files'

const FORMAT_METADATA: Record<TSpreadsheetSaveFormat, ISpreadsheetFormatMetadata> = {
    json: {
        extension: 'json',
        label: 'JSON',
        mimeType: 'application/json',
        pickerType: {
            description: 'JSON spreadsheet export',
            accept: {
                'application/json': ['.json'],
            },
        },
    },
    csv: {
        extension: 'csv',
        label: 'CSV',
        mimeType: 'text/csv',
        pickerType: {
            description: 'CSV spreadsheet export',
            accept: {
                'text/csv': ['.csv'],
            },
        },
    },
    excel: {
        extension: 'xlsx',
        label: 'Excel',
        mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        pickerType: {
            description: 'Excel workbook export',
            accept: {
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
            },
        },
    },
}

export const SPREADSHEET_FILE_PICKER_TYPES = Object.values(FORMAT_METADATA).map((metadata) => metadata.pickerType)

export const SPREADSHEET_SAVE_FORMATS: ISpreadsheetSaveFormatOption[] = [
    {
        format: 'json',
        label: 'JSON',
        description: 'Preserve rows and field metadata in a structured export.',
    },
    {
        format: 'csv',
        label: 'CSV',
        description: 'Export a plain table with headers and values.',
    },
    {
        format: 'excel',
        label: 'Excel',
        description: 'Write the current sheet into a single-sheet workbook.',
    },
]

function sanitizeFileStem(name: string): string {
    return name
        .trim()
        .replace(/[<>:"/\\|?*\x00-\x1f]+/g, '_')
        .replace(/\s+/g, ' ')
        .trim() || 'Spreadsheet'
}

function stripFileExtension(fileName: string): string {
    return fileName.replace(/\.[^.]+$/, '')
}

function sanitizeWorksheetName(name: string): string {
    const cleanedName = name.replace(/[\\/?*\[\]:]/g, ' ').trim()
    return (cleanedName || 'Sheet1').slice(0, 31)
}

function normalizeExportValue(value: unknown): string | number | boolean | null {
    if (value == null) {
        return null
    }

    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
        return value
    }

    if (value instanceof Date) {
        return value.toISOString()
    }

    if (typeof value === 'object') {
        return JSON.stringify(value)
    }

    return String(value)
}

function snapshotToMatrix(snapshot: ISpreadsheetSnapshot): Array<Array<string | number | boolean | null>> {
    const headerRow = snapshot.fields.map((field) => field.name ?? field.fid)
    const valueRows = snapshot.rows.map((row) => snapshot.fields.map((field) => normalizeExportValue(row[field.fid])))

    return [headerRow, ...valueRows]
}

function toStructuredJson(snapshot: ISpreadsheetSnapshot, sheetName: string): { name: string; rows: IRow[]; fields: IMutField[] } {
    return {
        name: sheetName,
        rows: snapshot.rows.map((row) => ({ ...row })),
        fields: snapshot.fields.map((field) => ({ ...field })),
    }
}

function resolveSuggestedFileName(
    sheetName: string,
    format: TSpreadsheetSaveFormat,
    currentFile?: ISpreadsheetExternalFile | null,
): string {
    if (currentFile?.source === format && currentFile.fileName.trim().length > 0 && format !== 'excel') {
        return currentFile.fileName
    }

    const safeStem = format === 'excel' && currentFile?.source === 'excel' && currentFile.fileName.trim().length > 0
        ? stripFileExtension(currentFile.fileName)
        : sanitizeFileStem(sheetName)

    return `${safeStem}.${FORMAT_METADATA[format].extension}`
}

async function writeExportToHandle(handle: ISpreadsheetFileHandle, fileExport: ISpreadsheetFileExport): Promise<void> {
    const writable = await handle.createWritable()
    await writable.write(fileExport.content)
    await writable.close()
}

function downloadExport(fileExport: ISpreadsheetFileExport): void {
    const objectUrl = URL.createObjectURL(fileExport.content)
    const anchor = document.createElement('a')

    anchor.href = objectUrl
    anchor.download = fileExport.fileName
    document.body.append(anchor)
    anchor.click()
    anchor.remove()

    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0)
}

async function chooseSaveFileHandle(
    format: TSpreadsheetSaveFormat,
    suggestedName: string,
    currentFile?: ISpreadsheetExternalFile | null,
): Promise<ISpreadsheetFileHandle | null> {
    const pickerWindow = window as TFilePickerWindow
    if (typeof pickerWindow.showSaveFilePicker !== 'function') {
        return null
    }

    try {
        return await pickerWindow.showSaveFilePicker({
            id: FILE_PICKER_ID,
            excludeAcceptAllOption: true,
            suggestedName,
            startIn: currentFile?.fileHandle ?? undefined,
            types: [FORMAT_METADATA[format].pickerType],
        })
    } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
            return null
        }

        throw error
    }
}

export function supportsSpreadsheetFileSystemAccess(): boolean {
    return typeof window !== 'undefined' && typeof (window as TFilePickerWindow).showSaveFilePicker === 'function'
}

export function getSpreadsheetFileSourceLabel(source: TSpreadsheetFileSource): string {
    return FORMAT_METADATA[source].label
}

export function createSpreadsheetFileExport(
    snapshot: ISpreadsheetSnapshot,
    sheetName: string,
    format: TSpreadsheetSaveFormat,
    currentFile?: ISpreadsheetExternalFile | null,
): ISpreadsheetFileExport {
    const fileName = resolveSuggestedFileName(sheetName, format, currentFile)

    if (format === 'json') {
        return {
            fileName,
            mimeType: FORMAT_METADATA.json.mimeType,
            content: new Blob([JSON.stringify(toStructuredJson(snapshot, sheetName), null, 2)], {
                type: FORMAT_METADATA.json.mimeType,
            }),
        }
    }

    if (format === 'csv') {
        const worksheet = XLSX.utils.aoa_to_sheet(snapshotToMatrix(snapshot))
        return {
            fileName,
            mimeType: FORMAT_METADATA.csv.mimeType,
            content: new Blob([XLSX.utils.sheet_to_csv(worksheet)], {
                type: FORMAT_METADATA.csv.mimeType,
            }),
        }
    }

    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(snapshotToMatrix(snapshot)), sanitizeWorksheetName(sheetName))

    return {
        fileName,
        mimeType: FORMAT_METADATA.excel.mimeType,
        content: new Blob([XLSX.write(workbook, { bookType: 'xlsx', type: 'array' })], {
            type: FORMAT_METADATA.excel.mimeType,
        }),
    }
}

export async function saveSpreadsheetToComputer(
    options: ISaveSpreadsheetToComputerOptions,
): Promise<ISaveSpreadsheetToComputerResult | null> {
    const fileExport = createSpreadsheetFileExport(options.snapshot, options.sheetName, options.format, options.currentFile)
    const handle = await chooseSaveFileHandle(options.format, fileExport.fileName, options.currentFile)

    if (handle) {
        await writeExportToHandle(handle, fileExport)

        return {
            externalFile: {
                fileName: handle.name || fileExport.fileName,
                source: options.format,
                worksheetName: options.format === 'excel' ? options.sheetName : undefined,
                fileHandle: handle,
            },
            method: 'file-system-access',
        }
    }

    if (supportsSpreadsheetFileSystemAccess()) {
        return null
    }

    downloadExport(fileExport)

    return {
        externalFile: {
            fileName: fileExport.fileName,
            source: options.format,
            worksheetName: options.format === 'excel' ? options.sheetName : undefined,
            fileHandle: null,
        },
        method: 'download',
    }
}