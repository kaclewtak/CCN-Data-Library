import { useMemo, useState } from 'react'

import {
    Columns3,
    Copy,
    FolderOpen,
    ListChecks,
    PencilLine,
    Plus,
    Redo2,
    Rows3,
    Save,
    Sheet,
    Trash2,
    Undo2,
} from 'lucide-react'

import { Button } from '@/components/ui/button'

import { CcnColumnVerificationDialog } from './CcnColumnVerificationDialog'
import { SaveSheetDialog } from './SaveSheetDialog'
import { SavedSheetsDialog } from './SavedSheetsDialog'
import type { ICcnSpreadsheetState } from './useCcnSpreadsheetState'
import { displayCellValue, serializeCellValue } from './utils'

interface ICcnSpreadsheetPanelProps {
    state: ICcnSpreadsheetState
}

function ToolbarButton(props: {
    label: string
    onClick: () => void | Promise<void>
    icon: React.ComponentType<{ className?: string }>
    disabled?: boolean
}) {
    const Icon = props.icon

    return (
        <Button className="gap-1.5" disabled={props.disabled} onClick={() => void props.onClick()} size="sm" type="button" variant="outline">
            <Icon className="h-3.5 w-3.5" />
            {props.label}
        </Button>
    )
}

export function CcnSpreadsheetPanel(props: ICcnSpreadsheetPanelProps) {
    const [verifyColumnsOpen, setVerifyColumnsOpen] = useState(false)
    const rowCountLabel = useMemo(
        () => `${props.state.rows.length} row${props.state.rows.length === 1 ? '' : 's'}`,
        [props.state.rows.length],
    )
    const columnCountLabel = useMemo(
        () => `${props.state.fields.length} column${props.state.fields.length === 1 ? '' : 's'}`,
        [props.state.fields.length],
    )

    return (
        <div className="ccn-spreadsheet-panel">
            <CcnColumnVerificationDialog
                fields={props.state.fields}
                onCoerceColumnNames={props.state.handleCoerceColumnNames}
                onOpenChange={setVerifyColumnsOpen}
                open={verifyColumnsOpen}
            />
            <SaveSheetDialog
                currentExternalFile={props.state.currentExternalFile}
                onOpenChange={props.state.setSaveDialogOpen}
                onSaveBrowserSheet={props.state.handleSaveBrowserSheet}
                onSaveComputerSheet={props.state.handleSaveComputerSheet}
                open={props.state.saveDialogOpen}
                sheetName={props.state.sheetName}
                sheets={props.state.savedSheets}
            />
            <SavedSheetsDialog
                onImportSheet={props.state.handleImportSheet}
                onLoadSheet={props.state.handleLoadSheet}
                onOpenChange={props.state.setLoadDialogOpen}
                open={props.state.loadDialogOpen}
                sheets={props.state.savedSheets}
            />
            <div className="ccn-spreadsheet-panel__header">
                <div className="grid gap-1">
                    <div className="flex items-center gap-2">
                        <h2 className="text-sm font-semibold text-foreground">Spreadsheet Editor</h2>
                        {/* <Badge variant="outline">CCN Addition</Badge> */}
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span>{props.state.sheetName}</span>
                        <span>•</span>
                        <span>{rowCountLabel}</span>
                        <span>•</span>
                        <span>{columnCountLabel}</span>
                        <span>•</span>
                        <span>{props.state.selectionLabel}</span>
                    </div>
                </div>
                <div className="grid justify-items-end gap-1 text-right text-xs text-muted-foreground">
                    <span>{props.state.isDirty ? 'Unsaved spreadsheet changes' : 'Browser-local save is current'}</span>
                    {props.state.lastSavedAt != null && (
                        <span>Last save or autosave: {new Date(props.state.lastSavedAt).toLocaleTimeString()}</span>
                    )}
                </div>
            </div>
            <div className="ccn-spreadsheet-toolbar">
                <ToolbarButton icon={Sheet} label="New Sheet" onClick={props.state.handleNewSheet} />
                <ToolbarButton icon={Save} label="Save" onClick={props.state.handleSaveSheet} />
                <ToolbarButton icon={FolderOpen} label="Load" onClick={() => props.state.setLoadDialogOpen(true)} />
                <ToolbarButton icon={ListChecks} label="Verify CCN Columns" onClick={() => setVerifyColumnsOpen(true)} />
                <ToolbarButton disabled={!props.state.canUndo} icon={Undo2} label="Undo" onClick={props.state.handleUndo} />
                <ToolbarButton disabled={!props.state.canRedo} icon={Redo2} label="Redo" onClick={props.state.handleRedo} />
                <ToolbarButton icon={Plus} label="Add Row" onClick={props.state.handleAddRow} />
                <ToolbarButton icon={Trash2} label="Remove Row" onClick={props.state.handleRemoveRow} />
                <ToolbarButton icon={Columns3} label="Add Column" onClick={props.state.handleAddColumn} />
                <ToolbarButton icon={Columns3} label="Remove Column" onClick={props.state.handleRemoveColumn} />
                <ToolbarButton icon={PencilLine} label="Rename Column" onClick={props.state.handleRenameColumn} />
                <ToolbarButton icon={Copy} label="Copy" onClick={props.state.handleCopySelection} />
                <ToolbarButton icon={Rows3} label="Paste" onClick={props.state.handlePasteSelection} />
            </div>
            <div className="ccn-spreadsheet-grid">
                <table>
                    <thead>
                        <tr>
                            <th className="ccn-spreadsheet-grid__row-header ccn-spreadsheet-grid__sticky-cell">#</th>
                            {props.state.fields.map((field) => (
                                <th key={field.fid}>
                                    <button
                                        aria-pressed={props.state.selectionKind === 'column' && field.fid === props.state.selectedColumnFid}
                                        className={props.state.selectionKind === 'column' && field.fid === props.state.selectedColumnFid ? 'ccn-spreadsheet-grid__selected' : undefined}
                                        onClick={() => props.state.selectColumn(field.fid)}
                                        type="button"
                                    >
                                        <span>{field.name}</span>
                                        <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
                                            {field.semanticType}
                                        </span>
                                    </button>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {props.state.rows.length === 0 ? (
                            <tr>
                                <td className="ccn-spreadsheet-grid__row-header ccn-spreadsheet-grid__sticky-cell text-muted-foreground">0</td>
                                <td className="text-sm text-muted-foreground" colSpan={props.state.fields.length}>
                                    The sheet is empty. Add a row to start editing.
                                </td>
                            </tr>
                        ) : (
                            props.state.rows.map((row, rowIndex) => (
                                <tr key={`row-${rowIndex}`}>
                                    <td className={props.state.selectionKind === 'row' && rowIndex === props.state.selectedRowIndex ? 'ccn-spreadsheet-grid__row-header ccn-spreadsheet-grid__sticky-cell ccn-spreadsheet-grid__band-selected' : 'ccn-spreadsheet-grid__row-header ccn-spreadsheet-grid__sticky-cell'}>
                                        <button
                                            aria-pressed={props.state.selectionKind === 'row' && rowIndex === props.state.selectedRowIndex}
                                            className={props.state.selectionKind === 'row' && rowIndex === props.state.selectedRowIndex ? 'ccn-spreadsheet-grid__selected' : undefined}
                                            onClick={() => props.state.selectRow(rowIndex)}
                                            type="button"
                                        >
                                            {rowIndex + 1}
                                        </button>
                                    </td>
                                    {props.state.fields.map((field) => {
                                        const cellKey = `${rowIndex}-${field.fid}-${serializeCellValue(row[field.fid])}`
                                        const isSelectedRow = props.state.selectionKind === 'row' && rowIndex === props.state.selectedRowIndex
                                        const isSelectedColumn = props.state.selectionKind === 'column' && field.fid === props.state.selectedColumnFid
                                        const isSelectedCell =
                                            props.state.selectedCell?.rowIndex === rowIndex && props.state.selectedCell?.columnFid === field.fid

                                        return (
                                            <td className={isSelectedRow || isSelectedColumn ? 'ccn-spreadsheet-grid__band-selected' : undefined} key={`${rowIndex}-${field.fid}`}>
                                                <input
                                                    aria-label={`Spreadsheet cell ${rowIndex + 1}-${field.name}`}
                                                    className={isSelectedCell ? 'ccn-spreadsheet-grid__input ccn-spreadsheet-grid__input--selected' : 'ccn-spreadsheet-grid__input'}
                                                    defaultValue={displayCellValue(row[field.fid])}
                                                    key={cellKey}
                                                    onBlur={(event) => props.state.commitCellValue(rowIndex, field.fid, event.currentTarget.value)}
                                                    onFocus={() => props.state.selectCell(rowIndex, field.fid)}
                                                    onKeyDown={(event) => {
                                                        if (event.key === 'Enter') {
                                                            event.currentTarget.blur()
                                                        }

                                                        if (event.key === 'Escape') {
                                                            event.currentTarget.value = displayCellValue(row[field.fid])
                                                            event.currentTarget.blur()
                                                        }
                                                    }}
                                                    type="text"
                                                />
                                            </td>
                                        )
                                    })}
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
