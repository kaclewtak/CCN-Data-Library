import { useEffect, useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'

import {
    getSpreadsheetFileSourceLabel,
    SPREADSHEET_SAVE_FORMATS,
    supportsSpreadsheetFileSystemAccess,
} from './fileTransfer'
import type { ISpreadsheetExternalFile, IPersistedSheet, TSpreadsheetSaveFormat } from './types'

interface ISaveSheetDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    sheetName: string
    sheets: IPersistedSheet[]
    currentExternalFile: ISpreadsheetExternalFile | null
    onSaveBrowserSheet: (name: string) => void | Promise<void>
    onSaveComputerSheet: (format: TSpreadsheetSaveFormat) => void | Promise<void>
}

export function SaveSheetDialog(props: ISaveSheetDialogProps) {
    const manualSheets = useMemo(
        () => props.sheets.filter((sheet) => sheet.kind === 'manual'),
        [props.sheets],
    )
    const [browserSheetName, setBrowserSheetName] = useState(props.sheetName)
    const [saveError, setSaveError] = useState<string | null>(null)
    const [activeAction, setActiveAction] = useState<string | null>(null)
    const supportsFileSystemAccess = supportsSpreadsheetFileSystemAccess()

    useEffect(() => {
        if (!props.open) {
            setSaveError(null)
            setActiveAction(null)
            return
        }

        setBrowserSheetName(props.sheetName)
        setSaveError(null)
        setActiveAction(null)
    }, [props.open, props.sheetName])

    const handleSaveBrowserSheet = async (name: string) => {
        setActiveAction(`browser:${name}`)
        setSaveError(null)

        try {
            await props.onSaveBrowserSheet(name)
        } catch (error) {
            setSaveError(error instanceof Error ? error.message : 'The browser-local save could not be completed.')
        } finally {
            setActiveAction(null)
        }
    }

    const handleSaveComputerSheet = async (format: TSpreadsheetSaveFormat) => {
        setActiveAction(`computer:${format}`)
        setSaveError(null)

        try {
            await props.onSaveComputerSheet(format)
        } catch (error) {
            setSaveError(error instanceof Error ? error.message : 'The computer-file save could not be completed.')
        } finally {
            setActiveAction(null)
        }
    }

    return (
        <Dialog open={props.open} onOpenChange={props.onOpenChange}>
            <DialogContent className="max-w-3xl">
                <DialogHeader>
                    <DialogTitle>Save Spreadsheet</DialogTitle>
                    <DialogDescription>
                        Save a browser-local copy or export the current sheet to this computer.
                    </DialogDescription>
                </DialogHeader>
                <div className="grid gap-6 md:grid-cols-2">
                    <div className="grid gap-3">
                        <div className="flex items-center gap-2">
                            <h3 className="text-sm font-semibold text-foreground">Save in Browser</h3>
                            <Badge variant="secondary">{manualSheets.length}</Badge>
                        </div>
                        <form
                            className="grid gap-3 rounded-md border border-border bg-card px-3 py-3"
                            onSubmit={(event) => {
                                event.preventDefault()
                                void handleSaveBrowserSheet(browserSheetName)
                            }}
                        >
                            <div className="grid gap-1">
                                <span className="text-sm font-medium text-foreground">Sheet name</span>
                                <Input
                                    onChange={(event) => setBrowserSheetName(event.currentTarget.value)}
                                    placeholder="Saved spreadsheet name"
                                    type="text"
                                    value={browserSheetName}
                                />
                            </div>
                            <Button disabled={activeAction != null} type="submit">
                                Save Browser Copy
                            </Button>
                            <span className="text-xs text-muted-foreground">
                                This updates the current dataset-specific save list and browser autosave.
                            </span>
                        </form>
                        {manualSheets.length === 0 ? (
                            <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">
                                No named browser-local sheets have been saved for this dataset yet.
                            </p>
                        ) : (
                            manualSheets.map((sheet) => (
                                <button
                                    className="grid gap-1 rounded-md border border-border bg-card px-3 py-3 text-left transition-colors hover:border-ring hover:bg-accent"
                                    disabled={activeAction != null}
                                    key={sheet.id}
                                    onClick={() => void handleSaveBrowserSheet(sheet.name)}
                                    type="button"
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="font-medium text-foreground">{sheet.name}</span>
                                        <Badge variant="outline">Overwrite</Badge>
                                    </div>
                                    <span className="text-xs text-muted-foreground">
                                        Last saved {new Date(sheet.updatedAt).toLocaleString()}
                                    </span>
                                </button>
                            ))
                        )}
                    </div>
                    <div className="grid gap-3">
                        <div className="flex items-center gap-2">
                            <h3 className="text-sm font-semibold text-foreground">Save to Computer</h3>
                            <Badge variant="secondary">{SPREADSHEET_SAVE_FORMATS.length}</Badge>
                        </div>
                        {props.currentExternalFile ? (
                            <div className="grid gap-1 rounded-md border border-border bg-card px-3 py-3">
                                <div className="flex items-center justify-between gap-2">
                                    <span className="font-medium text-foreground">{props.currentExternalFile.fileName}</span>
                                    <Badge variant="outline">{getSpreadsheetFileSourceLabel(props.currentExternalFile.source)}</Badge>
                                </div>
                                <span className="text-xs text-muted-foreground">
                                    {props.currentExternalFile.worksheetName
                                        ? `Current worksheet: ${props.currentExternalFile.worksheetName}`
                                        : 'Current sheet was loaded from a computer file.'}
                                </span>
                                <span className="text-xs text-muted-foreground">
                                    {supportsFileSystemAccess && props.currentExternalFile.fileHandle
                                        ? 'Save As will open in this file’s folder by default.'
                                        : 'The browser cannot reopen the original folder in this session, so Save As will use the browser default location.'}
                                </span>
                            </div>
                        ) : (
                            <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">
                                No computer file is linked to the current sheet yet.
                            </p>
                        )}
                        {SPREADSHEET_SAVE_FORMATS.map((formatOption) => (
                            <button
                                className="grid gap-1 rounded-md border border-border bg-card px-3 py-3 text-left transition-colors hover:border-ring hover:bg-accent disabled:cursor-not-allowed disabled:opacity-60"
                                disabled={activeAction != null}
                                key={formatOption.format}
                                onClick={() => void handleSaveComputerSheet(formatOption.format)}
                                type="button"
                            >
                                <div className="flex items-center justify-between gap-2">
                                    <span className="font-medium text-foreground">Save as {formatOption.label}</span>
                                    <Badge variant="outline">Computer File</Badge>
                                </div>
                                <span className="text-xs text-muted-foreground">{formatOption.description}</span>
                                <span className="text-xs text-muted-foreground">
                                    {supportsFileSystemAccess
                                        ? props.currentExternalFile?.fileHandle
                                            ? 'The picker starts in the current file location when possible.'
                                            : 'Choose the exact file name and folder for this export.'
                                        : 'This browser will download the file instead of opening a save picker.'}
                                </span>
                            </button>
                        ))}
                    </div>
                </div>
                {saveError && (
                    <p className="rounded-md border border-dashed border-border p-3 text-sm text-destructive">
                        {saveError}
                    </p>
                )}
                <div className="flex justify-end">
                    <Button onClick={() => props.onOpenChange(false)} type="button" variant="outline">
                        Close
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    )
}