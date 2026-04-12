import React, { useEffect, useMemo, useState } from 'react'

import { tracker } from '@/utils/tracker'
import type { IViewField } from '@kanaries/graphic-walker/interfaces'
import type { VizSpecStore } from '@kanaries/graphic-walker/store/visualSpecStore'
import type { ToolbarSelectButtonItem } from '@kanaries/graphic-walker/components/toolbar/toolbar-select-button'

import commonStore from '../store/common'

import {
    buildCcnFormulaChart,
    getAvailableCcnFormulaEntries,
    getCcnFormulaSelection,
    getCcnMetricLabel,
    type CcnFormulaSelectionKey,
} from './ccnFormulas'

function CcnFormulaIcon(iconProps: React.SVGProps<SVGSVGElement>) {
    return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true" {...iconProps}>
            <rect x="3" y="4" width="18" height="16" rx="3" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M7 8h10M7 12h6M7 16h4" />
            <text x="12" y="14.5" textAnchor="middle" fontSize="5.5" fill="currentColor" stroke="none">
                CCN
            </text>
        </svg>
    )
}

function RelationshipIcon(iconProps: React.SVGProps<SVGSVGElement>) {
    return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true" {...iconProps}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 19V5m0 14h14" />
            <circle cx="9" cy="14" r="1.25" fill="currentColor" stroke="none" />
            <circle cx="13.5" cy="11" r="1.25" fill="currentColor" stroke="none" />
            <circle cx="18" cy="8" r="1.25" fill="currentColor" stroke="none" />
        </svg>
    )
}

function DepthProfileIcon(iconProps: React.SVGProps<SVGSVGElement>) {
    return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true" {...iconProps}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 4v16m0 0h12" />
            <circle cx="11" cy="7" r="1.25" fill="currentColor" stroke="none" />
            <circle cx="14" cy="12" r="1.25" fill="currentColor" stroke="none" />
            <circle cx="17" cy="17" r="1.25" fill="currentColor" stroke="none" />
        </svg>
    )
}

function formatMissingMetrics(selectionKey: CcnFormulaSelectionKey, missing: string[]): string {
    const selection = getCcnFormulaSelection(selectionKey)
    const labels = missing.map((metric) => getCcnMetricLabel(metric as Parameters<typeof getCcnMetricLabel>[0]))
    const noun = labels.length === 1 ? 'field' : 'fields'

    return `Could not apply ${selection.label}. Missing ${noun}: ${labels.join(', ')}.`
}

export function getCcnFormulaTool(
    storeRef: React.MutableRefObject<VizSpecStore | null>,
    availableFields: IViewField[],
): ToolbarSelectButtonItem<CcnFormulaSelectionKey> {
    const [selectedPreset, setSelectedPreset] = useState<CcnFormulaSelectionKey>('carbon_vs_organic_matter')

    const formulaEntries = useMemo(() => getAvailableCcnFormulaEntries(availableFields), [availableFields])
    const activeSelectedPreset = formulaEntries.some((entry) => entry.key === selectedPreset)
        ? selectedPreset
        : (formulaEntries[0]?.key ?? selectedPreset)

    useEffect(() => {
        if (selectedPreset !== activeSelectedPreset) {
            setSelectedPreset(activeSelectedPreset)
        }
    }, [activeSelectedPreset, selectedPreset])

    const options = useMemo(
        () =>
            formulaEntries.map((entry) => ({
                key: entry.key,
                label: entry.label,
                icon: entry.preset.key.includes('depth_profile') ? DepthProfileIcon : RelationshipIcon,
            })),
        [formulaEntries]
    )

    const onSelect = (presetKey: CcnFormulaSelectionKey) => {
        setSelectedPreset(presetKey)
        tracker.track('click', { entity: `ccn_formula_${presetKey}` })

        const store = storeRef.current
        if (!store) {
            return
        }

        const result = buildCcnFormulaChart(store.currentVis, presetKey)
        if (!result.chart) {
            commonStore.setNotification(
                {
                    type: 'warning',
                    title: 'CCN formulas',
                    message: formatMissingMetrics(presetKey, result.missing),
                },
                5_000
            )
            return
        }

        store.replaceWithNLPQuery(`CCN formula: ${result.preset.label}`, JSON.stringify(result.chart))

        const columnsName = result.axisFields?.columns.name ?? result.axisFields?.columns.fid
        const rowsName = result.axisFields?.rows.name ?? result.axisFields?.rows.fid
        const detail = result.derivedDepthField ? ` using derived ${result.derivedDepthField.name}.` : ` using ${columnsName} and ${rowsName}.`

        commonStore.setNotification(
            {
                type: 'success',
                title: 'CCN formulas',
                message: `Applied ${result.selection.label}${detail}`,
            },
            3_000
        )
    }

    return {
        key: 'ccn_formulas',
        label: 'CCN formulas',
        icon: (iconProps?: React.SVGProps<SVGSVGElement>) => <CcnFormulaIcon {...iconProps} />,
        options,
        value: activeSelectedPreset,
        onSelect,
    }
}