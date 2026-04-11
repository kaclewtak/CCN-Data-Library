import type { DraggableFieldState, IChart, IViewField } from '@kanaries/graphic-walker/interfaces'

type CcnMetricKey = 'carbon' | 'organicMatter' | 'bulkDensity' | 'depth'

export type CcnFormulaPresetKey =
    | 'carbon_vs_organic_matter'
    | 'carbon_vs_bulk_density'
    | 'bulk_density_vs_organic_matter'
    | 'carbon_depth_profile'
    | 'organic_matter_depth_profile'
    | 'bulk_density_depth_profile'

type MetricMatcher = {
    exact: string[]
    contains: string[]
    bad?: string[]
}

type CcnFormulaPreset = {
    key: CcnFormulaPresetKey
    label: string
    columnsMetric: CcnMetricKey
    rowsMetric: CcnMetricKey
    geom: 'point'
}

type BuildDepthFieldResult = {
    field?: IViewField
    addToMeasures?: boolean
    derived?: boolean
}

export type BuildCcnFormulaChartResult = {
    chart?: IChart
    preset: CcnFormulaPreset
    axisFields?: {
        columns: IViewField
        rows: IViewField
    }
    matched: Partial<Record<CcnMetricKey, IViewField>>
    missing: CcnMetricKey[]
    derivedDepthField?: IViewField
}

export const CCN_FORMULA_PRESETS: readonly CcnFormulaPreset[] = [
    {
        key: 'carbon_vs_organic_matter',
        label: 'Carbon ~ Organic matter',
        columnsMetric: 'organicMatter',
        rowsMetric: 'carbon',
        geom: 'point',
    },
    {
        key: 'carbon_vs_bulk_density',
        label: 'Carbon ~ Bulk density',
        columnsMetric: 'bulkDensity',
        rowsMetric: 'carbon',
        geom: 'point',
    },
    {
        key: 'bulk_density_vs_organic_matter',
        label: 'Bulk density ~ Organic matter',
        columnsMetric: 'organicMatter',
        rowsMetric: 'bulkDensity',
        geom: 'point',
    },
    {
        key: 'carbon_depth_profile',
        label: 'Carbon depth profile',
        columnsMetric: 'carbon',
        rowsMetric: 'depth',
        geom: 'point',
    },
    {
        key: 'organic_matter_depth_profile',
        label: 'Organic matter depth profile',
        columnsMetric: 'organicMatter',
        rowsMetric: 'depth',
        geom: 'point',
    },
    {
        key: 'bulk_density_depth_profile',
        label: 'Bulk density depth profile',
        columnsMetric: 'bulkDensity',
        rowsMetric: 'depth',
        geom: 'point',
    },
] as const

export const CCN_DEPTH_MIDPOINT_FID = 'ccn_depth_midpoint'
export const CCN_DEPTH_MIDPOINT_NAME = 'CCN Depth Midpoint'

const FIELD_LABELS: Record<CcnMetricKey, string> = {
    carbon: 'carbon',
    organicMatter: 'organic matter',
    bulkDensity: 'bulk density',
    depth: 'depth',
}

const METRIC_MATCHERS: Record<Exclude<CcnMetricKey, 'depth'>, MetricMatcher> = {
    carbon: {
        exact: ['fraction_carbon', 'frac_carbon_surface', 'carbon_measured_or_modeled'],
        contains: [
            'fraction_carbon',
            'frac_carbon',
            'carbon_measured_or_modeled',
            'soil_organic_carbon',
            'organic_carbon',
            'carbon_fraction',
            'oc_fraction',
            'frac_c',
            'foc',
            'carbon',
        ],
        bad: ['carbonate', 'carbonates', 'inorganic'],
    },
    organicMatter: {
        exact: ['fraction_organic_matter', 'frac_om_surface', 'soil_organic_matter', 'organic_matter'],
        contains: ['fraction_organic_matter', 'frac_om', 'soil_organic_matter', 'organic_matter', 'om_fraction', 'loss_on_ignition', 'loi', 'som'],
        bad: ['carbonate', 'carbonates', 'inorganic'],
    },
    bulkDensity: {
        exact: ['dry_bulk_density', 'bulk_density'],
        contains: ['dry_bulk_density', 'bulk_density', 'bulk_dens', 'dbd', 'dry_density'],
        bad: ['particle_density'],
    },
}

const DEPTH_MID_MATCHER: MetricMatcher = {
    exact: ['depth_midpoint', 'depth_mid', 'mid_depth', 'depth_center', 'depth_centre', 'depth_cm', 'sample_depth', 'core_depth', 'depth'],
    contains: ['depth_midpoint', 'depth_mid', 'mid_depth', 'midpoint_depth', 'depth_center', 'depth_centre', 'sample_depth', 'core_depth', 'depth_cm', 'depth'],
    bad: ['depth_min', 'depth_max', 'top_depth', 'bottom_depth', 'upper_depth', 'lower_depth', 'min_depth', 'max_depth'],
}

const DEPTH_MIN_MATCHER: MetricMatcher = {
    exact: ['depth_min'],
    contains: ['depth_min', 'top_depth', 'depth_top', 'upper_depth', 'min_depth'],
}

const DEPTH_MAX_MATCHER: MetricMatcher = {
    exact: ['depth_max'],
    contains: ['depth_max', 'bottom_depth', 'depth_bottom', 'lower_depth', 'max_depth'],
}

function normalizeFieldName(value: string): string {
    return value.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
}

function matchesAlias(normalizedName: string, alias: string): boolean {
    return (
        normalizedName === alias ||
        normalizedName.startsWith(`${alias}_`) ||
        normalizedName.endsWith(`_${alias}`) ||
        normalizedName.includes(`_${alias}_`)
    )
}

function isQuantitativeField(field: IViewField): boolean {
    return field.semanticType === 'quantitative' || field.analyticType === 'measure'
}

function scoreField(field: IViewField, matcher: MetricMatcher): number {
    if (!isQuantitativeField(field) || field.aggName === 'expr') {
        return Number.NEGATIVE_INFINITY
    }

    const normalizedName = normalizeFieldName(field.name ?? field.fid)
    const normalizedExact = matcher.exact.map(normalizeFieldName)
    const normalizedContains = matcher.contains.map(normalizeFieldName)
    const normalizedBad = (matcher.bad ?? []).map(normalizeFieldName)

    if (normalizedBad.some((alias) => matchesAlias(normalizedName, alias))) {
        return Number.NEGATIVE_INFINITY
    }

    const exactIndex = normalizedExact.findIndex((alias) => normalizedName === alias)
    if (exactIndex >= 0) {
        return 1000 - exactIndex - (field.computed ? 5 : 0)
    }

    const partialIndex = normalizedContains.findIndex((alias) => matchesAlias(normalizedName, alias))
    if (partialIndex >= 0) {
        const alias = normalizedContains[partialIndex]
        const aliasTokenCount = alias.split('_').filter(Boolean).length
        const fieldTokenCount = normalizedName.split('_').filter(Boolean).length
        const extraTokenPenalty = Math.max(0, fieldTokenCount - aliasTokenCount)
        return 800 - partialIndex * 5 - extraTokenPenalty - (field.computed ? 5 : 0)
    }

    return Number.NEGATIVE_INFINITY
}

function findBestField(fields: IViewField[], matcher: MetricMatcher): IViewField | undefined {
    let bestField: IViewField | undefined
    let bestScore = Number.NEGATIVE_INFINITY

    for (const field of fields) {
        const score = scoreField(field, matcher)
        if (score > bestScore) {
            bestScore = score
            bestField = field
        }
    }

    return bestScore === Number.NEGATIVE_INFINITY ? undefined : bestField
}

function quoteSqlIdentifier(value: string): string {
    return `"${value.replace(/"/g, '""')}"`
}

function toMeasureField(field: IViewField): IViewField {
    return {
        ...field,
        analyticType: 'measure',
        aggName: field.aggName ?? 'sum',
    }
}

function buildDepthMidpointField(depthMin: IViewField, depthMax: IViewField): IViewField {
    const minName = depthMin.name ?? depthMin.fid
    const maxName = depthMax.name ?? depthMax.fid

    return {
        fid: CCN_DEPTH_MIDPOINT_FID,
        name: CCN_DEPTH_MIDPOINT_NAME,
        basename: CCN_DEPTH_MIDPOINT_NAME,
        semanticType: 'quantitative',
        analyticType: 'measure',
        aggName: 'sum',
        computed: true,
        expression: {
            op: 'expr',
            as: CCN_DEPTH_MIDPOINT_FID,
            params: [
                {
                    type: 'sql',
                    value: `(${quoteSqlIdentifier(minName)} + ${quoteSqlIdentifier(maxName)}) / 2`,
                },
            ],
        },
    }
}

function resolveDepthField(fields: IViewField[]): BuildDepthFieldResult {
    const existingMidpoint = fields.find((field) => field.fid === CCN_DEPTH_MIDPOINT_FID)
    if (existingMidpoint) {
        return { field: toMeasureField(existingMidpoint), derived: Boolean(existingMidpoint.computed) }
    }

    const midpointField = findBestField(fields, DEPTH_MID_MATCHER)
    if (midpointField) {
        return { field: toMeasureField(midpointField) }
    }

    const depthMin = findBestField(fields, DEPTH_MIN_MATCHER)
    const depthMax = findBestField(fields, DEPTH_MAX_MATCHER)
    if (depthMin && depthMax) {
        const derivedField = buildDepthMidpointField(depthMin, depthMax)
        return { field: derivedField, addToMeasures: true, derived: true }
    }

    const fallback = depthMin ?? depthMax
    if (fallback) {
        return { field: toMeasureField(fallback) }
    }

    return {}
}

function resetViewChannels(encodings: DraggableFieldState): DraggableFieldState {
    return {
        ...encodings,
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
        text: [],
    }
}

function appendMeasureField(measures: IViewField[], field: IViewField): IViewField[] {
    if (measures.some((measure) => measure.fid === field.fid)) {
        return measures
    }

    return [...measures, field]
}

export function getCcnFormulaPreset(presetKey: CcnFormulaPresetKey): CcnFormulaPreset {
    const preset = CCN_FORMULA_PRESETS.find((candidate) => candidate.key === presetKey)
    if (!preset) {
        throw new Error(`Unknown CCN formula preset: ${presetKey}`)
    }
    return preset
}

export function getCcnMetricLabel(metric: CcnMetricKey): string {
    return FIELD_LABELS[metric]
}

export function buildCcnFormulaChart(chart: IChart, presetKey: CcnFormulaPresetKey): BuildCcnFormulaChartResult {
    const preset = getCcnFormulaPreset(presetKey)
    const allFields = [...chart.encodings.dimensions, ...chart.encodings.measures]

    const matched: Partial<Record<CcnMetricKey, IViewField>> = {
        carbon: findBestField(allFields, METRIC_MATCHERS.carbon),
        organicMatter: findBestField(allFields, METRIC_MATCHERS.organicMatter),
        bulkDensity: findBestField(allFields, METRIC_MATCHERS.bulkDensity),
    }

    const depthField = resolveDepthField(allFields)
    if (depthField.field) {
        matched.depth = depthField.field
    }

    const requiredMetrics = [preset.columnsMetric, preset.rowsMetric]
    const missing = requiredMetrics.filter((metric) => !matched[metric])
    if (missing.length > 0) {
        return {
            preset,
            matched,
            missing,
            ...(depthField.derived && depthField.field ? { derivedDepthField: depthField.field } : {}),
        }
    }

    const nextEncodings = resetViewChannels(chart.encodings)
    if (depthField.addToMeasures && depthField.field) {
        nextEncodings.measures = appendMeasureField(chart.encodings.measures, depthField.field)
    }

    const columnsField = toMeasureField(matched[preset.columnsMetric]!)
    const rowsField = toMeasureField(matched[preset.rowsMetric]!)

    nextEncodings.columns = [columnsField]
    nextEncodings.rows = [rowsField]

    return {
        preset,
        matched,
        missing: [],
        axisFields: {
            columns: columnsField,
            rows: rowsField,
        },
        chart: {
            ...chart,
            config: {
                ...chart.config,
                coordSystem: 'generic',
                geoms: [preset.geom],
                defaultAggregated: false,
                folds: undefined,
            },
            encodings: nextEncodings,
        },
        ...(depthField.derived && depthField.field ? { derivedDepthField: depthField.field } : {}),
    }
}