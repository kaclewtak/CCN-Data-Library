import { useMemo, useState } from 'react'

import type { IMutField } from '@kanaries/graphic-walker/interfaces'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'

import {
    CCN_COLUMN_GUIDANCE_DATASETS,
    CCN_SOIL_CARBON_GUIDANCE_URL,
    type ICcnColumnInput,
    type ICcnColumnDuplicateMatch,
    type ICcnColumnMatch,
    type TCcnDatasetType,
    verifyCcnColumns,
} from './ccnColumnGuidance'

interface ICcnColumnVerificationDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    fields: IMutField[]
    onCoerceColumnNames: (matches: ICcnColumnMatch[]) => void
}

function ColumnList(props: { columns: readonly string[]; emptyLabel: string; variant?: 'default' | 'warning' | 'success' }) {
    if (props.columns.length === 0) {
        return <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">{props.emptyLabel}</p>
    }

    const badgeVariant = props.variant === 'warning' ? 'destructive' : props.variant === 'success' ? 'secondary' : 'outline'

    return (
        <div className="flex max-h-36 flex-wrap gap-2 overflow-auto rounded-md border border-border bg-card p-3">
            {props.columns.map((column) => (
                <Badge key={column} variant={badgeVariant}>{column}</Badge>
            ))}
        </div>
    )
}

function VariantMatchList(props: { matches: readonly ICcnColumnMatch[] }) {
    if (props.matches.length === 0) {
        return <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">No likely renamed CCN columns were found.</p>
    }

    return (
        <div className="grid max-h-44 gap-2 overflow-auto rounded-md border border-border bg-card p-3">
            {props.matches.map((match) => (
                <div className="grid gap-1 text-sm" key={`${match.fieldName}-${match.guidanceColumn}`}>
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-foreground">{match.fieldName}</span>
                        <span className="text-muted-foreground">matches</span>
                        <Badge variant="outline">{match.guidanceColumn}</Badge>
                    </div>
                    <span className="text-xs text-muted-foreground">{match.reason}</span>
                </div>
            ))}
        </div>
    )
}

function DuplicateMatchList(props: { duplicateMatches: readonly ICcnColumnDuplicateMatch[] }) {
    if (props.duplicateMatches.length === 0) {
        return null
    }

    return (
        <div className="grid gap-2">
            <h3 className="text-sm font-semibold text-foreground">Duplicate Matches</h3>
            <div className="grid max-h-32 gap-2 overflow-auto rounded-md border border-border bg-card p-3">
                {props.duplicateMatches.map((match) => (
                    <div className="grid gap-1 text-sm" key={match.guidanceColumn}>
                        <Badge className="w-fit" variant="destructive">{match.guidanceColumn}</Badge>
                        <span className="text-xs text-muted-foreground">{match.fieldNames.join(', ')}</span>
                    </div>
                ))}
            </div>
        </div>
    )
}

export function CcnColumnVerificationDialog(props: ICcnColumnVerificationDialogProps) {
    const [datasetType, setDatasetType] = useState<TCcnDatasetType>('depthseries')
    const columnInputs = useMemo<ICcnColumnInput[]>(
        () => props.fields.map((field) => ({
            fieldId: field.fid,
            fieldName: field.name?.trim() || field.fid,
        })),
        [props.fields],
    )
    const verification = useMemo(
        () => verifyCcnColumns(datasetType, columnInputs),
        [datasetType, columnInputs],
    )
    const duplicateGuidanceColumns = useMemo(
        () => new Set(verification.duplicateMatches.map((match) => match.guidanceColumn)),
        [verification.duplicateMatches],
    )
    const coercibleMatches = useMemo(
        () => verification.variantMatches.filter((match) => match.fieldId && !duplicateGuidanceColumns.has(match.guidanceColumn)),
        [duplicateGuidanceColumns, verification.variantMatches],
    )

    return (
        <Dialog open={props.open} onOpenChange={props.onOpenChange}>
            <DialogContent className="max-w-4xl">
                <DialogHeader>
                    <DialogTitle>Verify CCN Columns</DialogTitle>
                    <DialogDescription>
                        Compare the current spreadsheet headers with the Smithsonian CCN soil carbon guidance.
                    </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4">
                    <div className="grid gap-2 md:max-w-sm">
                        <span className="text-sm font-medium text-foreground">Dataset type</span>
                        <Select value={datasetType} onValueChange={(value) => setDatasetType(value as TCcnDatasetType)}>
                            <SelectTrigger aria-label="CCN dataset type">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {CCN_COLUMN_GUIDANCE_DATASETS.map((dataset) => (
                                    <SelectItem key={dataset.type} value={dataset.type}>{dataset.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid gap-3 md:grid-cols-4">
                        <div className="rounded-md border border-border bg-card p-3">
                            <div className="text-xs text-muted-foreground">Current columns</div>
                            <div className="text-2xl font-semibold text-foreground">{verification.fieldCount}</div>
                        </div>
                        <div className="rounded-md border border-border bg-card p-3">
                            <div className="text-xs text-muted-foreground">Guidance columns</div>
                            <div className="text-2xl font-semibold text-foreground">{verification.expectedColumnCount}</div>
                        </div>
                        <div className="rounded-md border border-border bg-card p-3">
                            <div className="text-xs text-muted-foreground">Exact matches</div>
                            <div className="text-2xl font-semibold text-foreground">{verification.exactMatches.length}</div>
                        </div>
                        <div className="rounded-md border border-border bg-card p-3">
                            <div className="text-xs text-muted-foreground">Likely variants</div>
                            <div className="text-2xl font-semibold text-foreground">{verification.variantMatches.length}</div>
                        </div>
                    </div>
                    <div className="grid gap-4 md:grid-cols-2">
                        <div className="grid gap-2">
                            <h3 className="text-sm font-semibold text-foreground">Missing Key Columns</h3>
                            <ColumnList columns={verification.missingKeyColumns} emptyLabel="All key columns are represented." variant="warning" />
                        </div>
                        <div className="grid gap-2">
                            <h3 className="text-sm font-semibold text-foreground">Extra Columns</h3>
                            <ColumnList columns={verification.extraColumns} emptyLabel="No extra columns were found." />
                        </div>
                        <div className="grid gap-2">
                            <h3 className="text-sm font-semibold text-foreground">Likely Renamed Columns</h3>
                            <VariantMatchList matches={verification.variantMatches} />
                        </div>
                        <div className="grid gap-2">
                            <h3 className="text-sm font-semibold text-foreground">Missing Other Guidance Columns</h3>
                            <ColumnList columns={verification.missingOptionalColumns} emptyLabel="All non-key guidance columns are represented." />
                        </div>
                    </div>
                    <DuplicateMatchList duplicateMatches={verification.duplicateMatches} />
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <a className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline" href={CCN_SOIL_CARBON_GUIDANCE_URL} rel="noreferrer" target="_blank">
                            Open CCN soil carbon guidance
                        </a>
                        <div className="flex flex-wrap justify-end gap-2">
                            <Button
                                disabled={coercibleMatches.length === 0}
                                onClick={() => props.onCoerceColumnNames(coercibleMatches)}
                                type="button"
                            >
                                Coerce Similar Terms
                            </Button>
                            <Button onClick={() => props.onOpenChange(false)} type="button" variant="outline">
                                Close
                            </Button>
                        </div>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    )
}