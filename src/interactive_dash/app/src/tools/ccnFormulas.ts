import type { DraggableFieldState, IChart, IViewField } from '@kanaries/graphic-walker/interfaces'

type CcnMetricKey = 'carbon' | 'organicMatter' | 'bulkDensity' | 'depth'
type CcnDepthVariant = 'depth' | 'midpoint' | 'depth_min' | 'depth_max'
type CcnDepthProfilePresetKey = 'carbon_depth_profile' | 'organic_matter_depth_profile' | 'bulk_density_depth_profile'

export type CcnFormulaPresetKey =
    | 'carbon_vs_organic_matter'
    | 'carbon_vs_bulk_density'
    | 'bulk_density_vs_organic_matter'
    | CcnDepthProfilePresetKey

export type CcnFormulaSelectionKey = CcnFormulaPresetKey | `${CcnDepthProfilePresetKey}__${CcnDepthVariant}`

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
    variant?: CcnDepthVariant
    field?: IViewField
    addToMeasures?: boolean
    derived?: boolean
}

export type CcnFormulaSelection = {
    key: CcnFormulaSelectionKey
    label: string
    preset: CcnFormulaPreset
    depthVariant?: CcnDepthVariant
}

export type BuildCcnFormulaChartResult = {
    chart?: IChart
    preset: CcnFormulaPreset
    selection: CcnFormulaSelection
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
const CCN_DEPTH_VARIANT_ORDER: readonly CcnDepthVariant[] = ['depth', 'midpoint', 'depth_min', 'depth_max'] as const
const CCN_DEPTH_VARIANT_LABELS: Record<CcnDepthVariant, string> = {
    depth: 'Depth',
    midpoint: 'Midpoint',
    depth_min: 'Depth min',
    depth_max: 'Depth max',
}
const DEPTH_PROFILE_PRESET_KEYS = new Set<CcnDepthProfilePresetKey>([
    'carbon_depth_profile',
    'organic_matter_depth_profile',
    'bulk_density_depth_profile',
])
const FORMULA_SELECTION_SEPARATOR = '__'
const FORMULA_PRESET_KEY_SET = new Set<CcnFormulaPresetKey>(CCN_FORMULA_PRESETS.map((preset) => preset.key))

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

const DEPTH_MATCHER: MetricMatcher = {
    exact: ['depth_cm', 'sample_depth', 'core_depth', 'depth'],
    contains: ['depth_cm', 'sample_depth', 'core_depth', 'depth'],
    bad: [
        'depth_midpoint',
        'depth_mid',
        'mid_depth',
        'midpoint_depth',
        'depth_center',
        'depth_centre',
        'depth_min',
        'depth_max',
        'top_depth',
        'bottom_depth',
        'upper_depth',
        'lower_depth',
        'min_depth',
        'max_depth',
    ],
}

const DEPTH_MID_MATCHER: MetricMatcher = {
    exact: ['depth_midpoint', 'depth_mid', 'mid_depth', 'depth_center', 'depth_centre'],
    contains: ['depth_midpoint', 'depth_mid', 'mid_depth', 'midpoint_depth', 'depth_center', 'depth_centre'],
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

function toMeasureField(field: IViewField): IViewField {
    return {
        ...field,
        analyticType: 'measure',
        aggName: field.aggName ?? 'sum',
    }
}

function isDepthProfilePresetKey(presetKey: CcnFormulaPresetKey): presetKey is CcnDepthProfilePresetKey {
    return DEPTH_PROFILE_PRESET_KEYS.has(presetKey as CcnDepthProfilePresetKey)
}

function isDepthVariant(value: string): value is CcnDepthVariant {
    return CCN_DEPTH_VARIANT_ORDER.includes(value as CcnDepthVariant)
}

function buildFormulaSelectionLabel(preset: CcnFormulaPreset, depthVariant?: CcnDepthVariant): string {
    if (!depthVariant) {
        return preset.label
    }

    return `${preset.label} (${CCN_DEPTH_VARIANT_LABELS[depthVariant]})`
}

function buildDepthSelectionKey(presetKey: CcnDepthProfilePresetKey, depthVariant: CcnDepthVariant): CcnFormulaSelectionKey {
    return `${presetKey}${FORMULA_SELECTION_SEPARATOR}${depthVariant}`
}

function parseFormulaSelectionKey(selectionKey: CcnFormulaSelectionKey): { presetKey: CcnFormulaPresetKey; depthVariant?: CcnDepthVariant } {
    const [rawPresetKey, rawDepthVariant, ...remaining] = selectionKey.split(FORMULA_SELECTION_SEPARATOR)
    if (
        remaining.length === 0
        && rawDepthVariant
        && FORMULA_PRESET_KEY_SET.has(rawPresetKey as CcnFormulaPresetKey)
        && isDepthProfilePresetKey(rawPresetKey as CcnFormulaPresetKey)
        && isDepthVariant(rawDepthVariant)
    ) {
        return {
            presetKey: rawPresetKey as CcnDepthProfilePresetKey,
            depthVariant: rawDepthVariant,
        }
    }

    return { presetKey: selectionKey as CcnFormulaPresetKey }
}

function collectChartFields(chart: IChart): IViewField[] {
    return [...chart.encodings.dimensions, ...chart.encodings.measures]
}

function resolveAvailableDepthFields(fields: IViewField[]): BuildDepthFieldResult[] {
    const results = new Map<CcnDepthVariant, BuildDepthFieldResult>()
    const directDepth = findBestField(fields, DEPTH_MATCHER)
    const midpointField = findBestField(fields, DEPTH_MID_MATCHER)
    const depthMin = findBestField(fields, DEPTH_MIN_MATCHER)
    const depthMax = findBestField(fields, DEPTH_MAX_MATCHER)

    if (directDepth) {
        results.set('depth', { variant: 'depth', field: toMeasureField(directDepth) })
    }

    if (midpointField) {
        results.set('midpoint', { variant: 'midpoint', field: toMeasureField(midpointField) })
    }

    if (depthMin) {
        results.set('depth_min', { variant: 'depth_min', field: toMeasureField(depthMin) })
    }

    if (depthMax) {
        results.set('depth_max', { variant: 'depth_max', field: toMeasureField(depthMax) })
    }

    return CCN_DEPTH_VARIANT_ORDER.flatMap((variant) => {
        const match = results.get(variant)
        return match ? [match] : []
    })
}

function resolveDepthField(fields: IViewField[], preferredVariant?: CcnDepthVariant): BuildDepthFieldResult {
    const depthFields = resolveAvailableDepthFields(fields)
    if (preferredVariant) {
        return depthFields.find((field) => field.variant === preferredVariant) ?? {}
    }

    return depthFields[0] ?? {}
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

export function getCcnFormulaSelection(selectionKey: CcnFormulaSelectionKey): CcnFormulaSelection {
    const { presetKey, depthVariant } = parseFormulaSelectionKey(selectionKey)
    const preset = getCcnFormulaPreset(presetKey)

    return {
        key: selectionKey,
        label: buildFormulaSelectionLabel(preset, depthVariant),
        preset,
        depthVariant,
    }
}

export function getAvailableCcnFormulaEntries(fields: IViewField[]): CcnFormulaSelection[] {
    const depthFields = resolveAvailableDepthFields(fields)

    return CCN_FORMULA_PRESETS.flatMap<CcnFormulaSelection>((preset) => {
        if (!isDepthProfilePresetKey(preset.key)) {
            return [
                {
                    key: preset.key,
                    label: preset.label,
                    preset,
                    depthVariant: undefined,
                },
            ]
        }

        const depthPresetKey = preset.key

        return depthFields.map((depthField) => ({
            key: buildDepthSelectionKey(depthPresetKey, depthField.variant!),
            label: buildFormulaSelectionLabel(preset, depthField.variant),
            preset,
            depthVariant: depthField.variant,
        }))
    })
}

export function buildCcnFormulaChart(chart: IChart, selectionKey: CcnFormulaSelectionKey): BuildCcnFormulaChartResult {
    const selection = getCcnFormulaSelection(selectionKey)
    const preset = selection.preset
    const allFields = collectChartFields(chart)

    const matched: Partial<Record<CcnMetricKey, IViewField>> = {
        carbon: findBestField(allFields, METRIC_MATCHERS.carbon),
        organicMatter: findBestField(allFields, METRIC_MATCHERS.organicMatter),
        bulkDensity: findBestField(allFields, METRIC_MATCHERS.bulkDensity),
    }

    const depthField = resolveDepthField(allFields, selection.depthVariant)
    if (depthField.field) {
        matched.depth = depthField.field
    }

    const requiredMetrics = [preset.columnsMetric, preset.rowsMetric]
    const missing = requiredMetrics.filter((metric) => !matched[metric])
    if (missing.length > 0) {
        return {
            preset,
            selection,
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
        selection,
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