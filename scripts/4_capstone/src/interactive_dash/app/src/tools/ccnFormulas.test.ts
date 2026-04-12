import type { DraggableFieldState, IChart, IFilterField, IViewField } from '@kanaries/graphic-walker/interfaces'
import { describe, expect, it } from 'vitest'

import { buildCcnFormulaChart, getAvailableCcnFormulaEntries } from './ccnFormulas'

function makeField(fid: string, name: string, analyticType: 'dimension' | 'measure' = 'measure'): IViewField {
    return {
        fid,
        name,
        basename: name,
        analyticType,
        semanticType: 'quantitative',
        ...(analyticType === 'measure' ? { aggName: 'sum' } : {}),
    }
}

function makeFilter(fid: string, name: string): IFilterField {
    return {
        fid,
        name,
        analyticType: 'dimension',
        semanticType: 'nominal',
        rule: {
            type: 'one of',
            value: ['A'],
        },
    }
}

function makeChart(fields: Partial<DraggableFieldState> = {}): IChart {
    return {
        visId: 'chart-1',
        name: 'Chart 1',
        config: {
            defaultAggregated: true,
            geoms: ['bar'],
            coordSystem: 'geographic',
            limit: -1,
            folds: ['legacy_fold'],
        },
        layout: {
            showActions: false,
            showTableSummary: false,
            stack: 'stack',
            interactiveScale: false,
            zeroScale: true,
            size: {
                mode: 'fixed',
                width: 600,
                height: 600,
            },
            format: {},
            geoKey: 'name',
            resolve: {},
            renderer: 'vega-lite',
        },
        encodings: {
            dimensions: [],
            measures: [],
            rows: [],
            columns: [],
            color: [],
            opacity: [],
            size: [],
            shape: [],
            theta: [],
            radius: [],
            longitude: [],
            latitude: [],
            geoId: [],
            details: [],
            filters: [],
            text: [],
            ...fields,
        },
    }
}

describe('ccn formulas', () => {
    it('builds a carbon vs organic matter preset and preserves filters', () => {
        const filter = makeFilter('study_id', 'Study ID')
        const chart = makeChart({
            measures: [
                makeField('fraction_carbon', 'fraction_carbon'),
                makeField('fraction_organic_matter', 'fraction_organic_matter'),
                makeField('dry_bulk_density', 'dry_bulk_density'),
            ],
            filters: [filter],
            color: [makeField('legacy_color', 'Legacy color')],
        })

        const result = buildCcnFormulaChart(chart, 'carbon_vs_organic_matter')

        expect(result.missing).toEqual([])
        expect(result.chart?.config.coordSystem).toBe('generic')
        expect(result.chart?.config.defaultAggregated).toBe(false)
        expect(result.chart?.config.geoms).toEqual(['point'])
        expect(result.chart?.config.folds).toBeUndefined()
        expect(result.chart?.encodings.columns[0].fid).toBe('fraction_organic_matter')
        expect(result.chart?.encodings.rows[0].fid).toBe('fraction_carbon')
        expect(result.chart?.encodings.color).toEqual([])
        expect(result.chart?.encodings.filters).toEqual([filter])
    })

    it('prefers carbon fields over carbonate lookalikes', () => {
        const chart = makeChart({
            measures: [
                makeField('carbonate_content', 'carbonate_content'),
                makeField('fraction_carbon', 'fraction_carbon'),
                makeField('dry_bulk_density', 'dry_bulk_density'),
            ],
        })

        const result = buildCcnFormulaChart(chart, 'carbon_vs_bulk_density')

        expect(result.missing).toEqual([])
        expect(result.chart?.encodings.rows[0].fid).toBe('fraction_carbon')
    })

    it('does not expose midpoint when only depth_min and depth_max are present', () => {
        const entries = getAvailableCcnFormulaEntries([
            makeField('fraction_carbon', 'fraction_carbon'),
            makeField('depth_min', 'depth_min'),
            makeField('depth_max', 'depth_max'),
        ]).filter((entry) => entry.preset.key === 'carbon_depth_profile')

        expect(entries.map((entry) => entry.key)).toEqual([
            'carbon_depth_profile__depth_min',
            'carbon_depth_profile__depth_max',
        ])
    })

    it('lists depth profile entries in depth order when multiple depth variants are available', () => {
        const entries = getAvailableCcnFormulaEntries([
            makeField('fraction_carbon', 'fraction_carbon'),
            makeField('depth', 'depth'),
            makeField('depth_midpoint', 'depth_midpoint'),
            makeField('depth_min', 'depth_min'),
            makeField('depth_max', 'depth_max'),
        ]).filter((entry) => entry.preset.key === 'carbon_depth_profile')

        expect(entries.map((entry) => entry.key)).toEqual([
            'carbon_depth_profile__depth',
            'carbon_depth_profile__midpoint',
            'carbon_depth_profile__depth_min',
            'carbon_depth_profile__depth_max',
        ])
        expect(entries.map((entry) => entry.label)).toEqual([
            'Carbon depth profile (Depth)',
            'Carbon depth profile (Midpoint)',
            'Carbon depth profile (Depth min)',
            'Carbon depth profile (Depth max)',
        ])
    })

    it('fails midpoint selection when the dataset does not contain a midpoint field', () => {
        const chart = makeChart({
            measures: [
                makeField('fraction_carbon', 'fraction_carbon'),
                makeField('depth_min', 'depth_min'),
                makeField('depth_max', 'depth_max'),
            ],
        })

        const result = buildCcnFormulaChart(chart, 'carbon_depth_profile__midpoint')

        expect(result.chart).toBeUndefined()
        expect(result.missing).toEqual(['depth'])
        expect(result.derivedDepthField).toBeUndefined()
    })

    it('lists only interval bounds when only depth_min and depth_max exist', () => {
        const entries = getAvailableCcnFormulaEntries([
            makeField('fraction_carbon', 'fraction_carbon'),
            makeField('depth_min', 'depth_min'),
            makeField('depth_max', 'depth_max'),
        ]).filter((entry) => entry.preset.key === 'carbon_depth_profile')

        expect(entries.map((entry) => entry.key)).toEqual([
            'carbon_depth_profile__depth_min',
            'carbon_depth_profile__depth_max',
        ])
    })

    it('builds a depth-min profile when the depth-min variant is selected', () => {
        const chart = makeChart({
            measures: [
                makeField('fraction_carbon', 'fraction_carbon'),
                makeField('depth', 'depth'),
                makeField('depth_min', 'depth_min'),
                makeField('depth_max', 'depth_max'),
            ],
        })

        const result = buildCcnFormulaChart(chart, 'carbon_depth_profile__depth_min')

        expect(result.missing).toEqual([])
        expect(result.selection.label).toBe('Carbon depth profile (Depth min)')
        expect(result.chart?.encodings.rows[0].fid).toBe('depth_min')
        expect(result.derivedDepthField).toBeUndefined()
    })

    it('reports missing CCN fields when a preset cannot be built', () => {
        const chart = makeChart({
            measures: [makeField('fraction_carbon', 'fraction_carbon')],
        })

        const result = buildCcnFormulaChart(chart, 'carbon_vs_organic_matter')

        expect(result.chart).toBeUndefined()
        expect(result.missing).toEqual(['organicMatter'])
    })
})