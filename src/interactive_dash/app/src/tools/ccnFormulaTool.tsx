import React, { useMemo, useState } from 'react'

import { tracker } from '@/utils/tracker'
import type { VizSpecStore } from '@kanaries/graphic-walker/store/visualSpecStore'
import type { ToolbarSelectButtonItem } from '@kanaries/graphic-walker/components/toolbar/toolbar-select-button'

import commonStore from '../store/common'

import {
    buildCcnFormulaChart,
    CCN_FORMULA_PRESETS,
    getCcnFormulaPreset,
    getCcnMetricLabel,
    type CcnFormulaPresetKey,
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

function formatMissingMetrics(presetKey: CcnFormulaPresetKey, missing: string[]): string {
    const preset = getCcnFormulaPreset(presetKey)
    const labels = missing.map((metric) => getCcnMetricLabel(metric as Parameters<typeof getCcnMetricLabel>[0]))
    const noun = labels.length === 1 ? 'field' : 'fields'

    return `Could not apply ${preset.label}. Missing ${noun}: ${labels.join(', ')}.`
}

export function getCcnFormulaTool(storeRef: React.MutableRefObject<VizSpecStore | null>): ToolbarSelectButtonItem<CcnFormulaPresetKey> {
    const [selectedPreset, setSelectedPreset] = useState<CcnFormulaPresetKey>('carbon_vs_organic_matter')

    const options = useMemo(
        () =>
            CCN_FORMULA_PRESETS.map((preset) => ({
                key: preset.key,
                label: preset.label,
                icon: preset.key.includes('depth_profile') ? DepthProfileIcon : RelationshipIcon,
            })),
        []
    )

    const onSelect = (presetKey: CcnFormulaPresetKey) => {
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
                message: `Applied ${result.preset.label}${detail}`,
            },
            3_000
        )
    }

    return {
        key: 'ccn_formulas',
        label: 'CCN formulas',
        icon: (iconProps?: React.SVGProps<SVGSVGElement>) => <CcnFormulaIcon {...iconProps} />,
        options,
        value: selectedPreset,
        onSelect,
    }
}