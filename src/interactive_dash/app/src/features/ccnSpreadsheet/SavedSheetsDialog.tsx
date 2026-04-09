import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog'

import type { IPersistedSheet } from './types'

interface ISavedSheetsDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    sheets: IPersistedSheet[]
    onLoadSheet: (sheet: IPersistedSheet) => void
}

export function SavedSheetsDialog(props: ISavedSheetsDialogProps) {
    const manualSheets = props.sheets.filter((sheet) => sheet.kind === 'manual')
    const autosaveSheets = props.sheets.filter((sheet) => sheet.kind === 'autosave')

    return (
        <Dialog open={props.open} onOpenChange={props.onOpenChange}>
            <DialogContent className="max-w-2xl">
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
                <div className="flex justify-end">
                    <Button onClick={() => props.onOpenChange(false)} type="button" variant="outline">
                        Close
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    )
}
