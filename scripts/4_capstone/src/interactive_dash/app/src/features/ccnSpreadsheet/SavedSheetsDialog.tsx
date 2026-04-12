import { useEffect, useRef, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog'

import { getSpreadsheetFileSourceLabel } from './fileTransfer'
import { IMPORT_FILE_ACCEPT, parseImportedSpreadsheetFile, pickAndParseImportedSpreadsheetFile, supportsSpreadsheetOpenPicker } from './fileImport'
import type { IImportedSpreadsheetSheet, IPersistedSheet } from './types'

interface ISavedSheetsDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    sheets: IPersistedSheet[]
    onLoadSheet: (sheet: IPersistedSheet) => void
    onImportSheet: (sheet: IImportedSpreadsheetSheet) => void | Promise<void>
}

export function SavedSheetsDialog(props: ISavedSheetsDialogProps) {
    const manualSheets = props.sheets.filter((sheet) => sheet.kind === 'manual')
    const autosaveSheets = props.sheets.filter((sheet) => sheet.kind === 'autosave')
    const fileInputRef = useRef<HTMLInputElement | null>(null)
    const [importedSheets, setImportedSheets] = useState<IImportedSpreadsheetSheet[]>([])
    const [importFileName, setImportFileName] = useState<string | null>(null)
    const [importSource, setImportSource] = useState<IImportedSpreadsheetSheet['source'] | null>(null)
    const [importError, setImportError] = useState<string | null>(null)
    const [isParsingImport, setIsParsingImport] = useState(false)
    const [importingSheetName, setImportingSheetName] = useState<string | null>(null)

    useEffect(() => {
        if (!props.open) {
            setImportedSheets([])
            setImportFileName(null)
            setImportSource(null)
            setImportError(null)
            setIsParsingImport(false)
            setImportingSheetName(null)
        }
    }, [props.open])

    const applyParsedImportFile = (parsedFile: Awaited<ReturnType<typeof parseImportedSpreadsheetFile>>) => {
        setImportedSheets(parsedFile.sheets)
        setImportFileName(parsedFile.fileName)
        setImportSource(parsedFile.source)
    }

    const handleChooseFile = async () => {
        if (!supportsSpreadsheetOpenPicker()) {
            fileInputRef.current?.click()
            return
        }

        setIsParsingImport(true)
        setImportError(null)

        try {
            const parsedFile = await pickAndParseImportedSpreadsheetFile()
            if (!parsedFile) {
                return
            }

            applyParsedImportFile(parsedFile)
        } catch (error) {
            setImportedSheets([])
            setImportFileName(null)
            setImportSource(null)
            setImportError(error instanceof Error ? error.message : 'The selected file could not be loaded.')
        } finally {
            setIsParsingImport(false)
        }
    }

    const handleImportFileSelection = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = event.currentTarget.files?.[0]
        event.currentTarget.value = ''

        if (!selectedFile) {
            return
        }

        setIsParsingImport(true)
        setImportError(null)

        try {
            const parsedFile = await parseImportedSpreadsheetFile(selectedFile)
            applyParsedImportFile(parsedFile)
        } catch (error) {
            setImportedSheets([])
            setImportFileName(selectedFile.name)
            setImportSource(null)
            setImportError(error instanceof Error ? error.message : 'The selected file could not be loaded.')
        } finally {
            setIsParsingImport(false)
        }
    }

    const handleImportSheet = async (sheet: IImportedSpreadsheetSheet) => {
        setImportingSheetName(sheet.name)

        try {
            await props.onImportSheet(sheet)
        } finally {
            setImportingSheetName(null)
        }
    }

    return (
        <Dialog open={props.open} onOpenChange={props.onOpenChange}>
            <DialogContent className="max-w-3xl">
                <DialogHeader>
                    <DialogTitle>Load Spreadsheet</DialogTitle>
                    <DialogDescription>
                        Browser-local saves and autosaves are grouped by the current uploaded dataset.
                    </DialogDescription>
                </DialogHeader>
                <div className="grid gap-6 md:grid-cols-2">
                    <div className="grid gap-3">
                        <div className="flex items-center gap-2">
                            <h3 className="text-sm font-semibold text-foreground">Saved Sheets</h3>
                            <Badge variant="secondary">{manualSheets.length}</Badge>
                        </div>
                        {manualSheets.length === 0 ? (
                            <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">
                                No named sheets have been saved for this dataset yet.
                            </p>
                        ) : (
                            manualSheets.map((sheet) => (
                                <button
                                    key={sheet.id}
                                    className="grid gap-1 rounded-md border border-border bg-card px-3 py-3 text-left transition-colors hover:border-ring hover:bg-accent"
                                    onClick={() => props.onLoadSheet(sheet)}
                                    type="button"
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="font-medium text-foreground">{sheet.name}</span>
                                        <Badge variant="outline">Saved</Badge>
                                    </div>
                                    <span className="text-xs text-muted-foreground">
                                        {new Date(sheet.updatedAt).toLocaleString()}
                                    </span>
                                </button>
                            ))
                        )}
                    </div>
                    <div className="grid gap-3">
                        <div className="flex items-center gap-2">
                            <h3 className="text-sm font-semibold text-foreground">Autosaves</h3>
                            <Badge variant="secondary">{autosaveSheets.length}</Badge>
                        </div>
                        {autosaveSheets.length === 0 ? (
                            <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">
                                No autosave is available for this dataset yet.
                            </p>
                        ) : (
                            autosaveSheets.map((sheet) => (
                                <button
                                    key={sheet.id}
                                    className="grid gap-1 rounded-md border border-border bg-card px-3 py-3 text-left transition-colors hover:border-ring hover:bg-accent"
                                    onClick={() => props.onLoadSheet(sheet)}
                                    type="button"
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="font-medium text-foreground">{sheet.name}</span>
                                        <Badge variant="outline">Autosave</Badge>
                                    </div>
                                    <span className="text-xs text-muted-foreground">
                                        {new Date(sheet.updatedAt).toLocaleString()}
                                    </span>
                                </button>
                            ))
                        )}
                    </div>
                </div>
                <div className="grid gap-3">
                    <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-foreground">Import from Computer</h3>
                        {importedSheets.length > 0 && <Badge variant="secondary">{importedSheets.length}</Badge>}
                    </div>
                    <input accept={IMPORT_FILE_ACCEPT} className="hidden" onChange={handleImportFileSelection} ref={fileInputRef} type="file" />
                    <button
                        className="grid gap-1 rounded-md border border-dashed border-border bg-card px-3 py-3 text-left transition-colors hover:border-ring hover:bg-accent"
                        onClick={handleChooseFile}
                        type="button"
                    >
                        <div className="flex items-center justify-between gap-2">
                            <span className="font-medium text-foreground">{isParsingImport ? 'Reading file...' : 'Choose JSON, CSV, or Excel file'}</span>
                            <Badge variant="outline">Computer File</Badge>
                        </div>
                        <span className="text-xs text-muted-foreground">
                            {supportsSpreadsheetOpenPicker()
                                ? 'Open a spreadsheet from this computer and keep its folder available for later saves when the browser allows it.'
                                : 'Load a saved spreadsheet from this computer into the browser-local sheet list.'}
                        </span>
                    </button>
                    {importError && (
                        <p className="rounded-md border border-dashed border-border p-3 text-sm text-destructive">
                            {importError}
                        </p>
                    )}
                    {importedSheets.length > 0 && (
                        <div className="grid gap-3 md:grid-cols-2">
                            {importedSheets.map((sheet) => (
                                <button
                                    className="grid gap-1 rounded-md border border-border bg-card px-3 py-3 text-left transition-colors hover:border-ring hover:bg-accent"
                                    disabled={importingSheetName != null}
                                    key={`${sheet.fileName}-${sheet.worksheetName ?? sheet.name}`}
                                    onClick={() => void handleImportSheet(sheet)}
                                    type="button"
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="font-medium text-foreground">{sheet.worksheetName ?? sheet.name}</span>
                                        <Badge variant="outline">{getSpreadsheetFileSourceLabel(importSource ?? sheet.source)}</Badge>
                                    </div>
                                    <span className="text-xs text-muted-foreground">
                                        {importFileName ?? sheet.fileName}
                                        {sheet.worksheetName && importedSheets.length > 1 ? ` • Worksheet ${sheet.worksheetName}` : ''}
                                    </span>
                                    <span className="text-xs text-muted-foreground">
                                        {sheet.rows.length} rows • {sheet.fields.length} columns
                                    </span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
                <div className="flex justify-end">
                    <Button onClick={() => props.onOpenChange(false)} type="button" variant="outline">
                        Close
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    )
}
