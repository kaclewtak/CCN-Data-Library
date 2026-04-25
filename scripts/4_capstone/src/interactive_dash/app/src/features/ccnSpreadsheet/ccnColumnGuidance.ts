export const CCN_SOIL_CARBON_GUIDANCE_URL = 'https://smithsonian.github.io/CCN-Community-Resources/soil_carbon_guidance.html'

export type TCcnColumnMatchType = 'exact' | 'variant'

export interface ICcnColumnGuidanceDataset {
    type: string
    label: string
    documentationName: string
    columns: readonly string[]
    keyColumns: readonly string[]
}

export interface ICcnColumnInput {
    fieldId?: string
    fieldName: string
}

export interface ICcnColumnMatch {
    fieldId?: string
    fieldName: string
    guidanceColumn: string
    matchType: TCcnColumnMatchType
    reason: string
}

export interface ICcnColumnDuplicateMatch {
    guidanceColumn: string
    fieldNames: string[]
}

export interface ICcnColumnVerificationResult {
    dataset: ICcnColumnGuidanceDataset
    fieldCount: number
    expectedColumnCount: number
    exactMatches: ICcnColumnMatch[]
    variantMatches: ICcnColumnMatch[]
    missingColumns: string[]
    missingKeyColumns: string[]
    missingOptionalColumns: string[]
    extraColumns: string[]
    duplicateMatches: ICcnColumnDuplicateMatch[]
}

export const CCN_COLUMN_GUIDANCE_DATASETS = [
    {
        type: 'materials_methods',
        label: 'Materials and Methods',
        documentationName: 'materials and methods',
        columns: [
            'study_id',
            'method_id',
            'coring_method',
            'roots_flag',
            'sediment_sieved_flag',
            'sediment_sieve_size',
            'compaction_flag',
            'dry_bulk_density_temperature',
            'dry_bulk_density_time',
            'dry_bulk_density_sample_volume',
            'dry_bulk_density_sample_mass',
            'dry_bulk_density_flag',
            'loss_on_ignition_temperature',
            'loss_on_ignition_time',
            'loss_on_ignition_sample_volume',
            'loss_on_ignition_sample_mass',
            'loss_on_ignition_flag',
            'carbon_measured_or_modeled',
            'carbonates_removed',
            'carbonate_removal_method',
            'fraction_carbon_method',
            'fraction_carbon_type',
            'carbon_profile_notes',
            'cs137_counting_method',
            'pb210_counting_method',
            'excess_pb210_rate',
            'excess_pb210_model',
            'ra226_assumption',
            'c14_counting_method',
            'dating_notes',
            'age_depth_model_reference',
            'age_depth_model_notes',
        ],
        keyColumns: [
            'study_id',
            'method_id',
            'coring_method',
            'roots_flag',
            'sediment_sieved_flag',
            'dry_bulk_density_temperature',
            'dry_bulk_density_time',
            'dry_bulk_density_sample_volume',
            'dry_bulk_density_sample_mass',
            'loss_on_ignition_temperature',
            'loss_on_ignition_time',
            'loss_on_ignition_sample_volume',
            'loss_on_ignition_sample_mass',
        ],
    },
    {
        type: 'sites',
        label: 'Sites',
        documentationName: 'sites',
        columns: [
            'study_id',
            'site_id',
            'site_description',
            'site_latitude_max',
            'site_latitude_min',
            'site_longitude_max',
            'site_longitude_min',
            'site_boundaries',
            'salinity_class',
            'salinity_method',
            'salinity_notes',
            'vegetation_class',
            'vegetation_method',
            'vegetation_notes',
            'inundation_class',
            'inundation_method',
            'inundation_notes',
        ],
        keyColumns: [
            'study_id',
            'site_id',
            'salinity_class',
            'salinity_method',
            'vegetation_class',
            'vegetation_method',
            'inundation_class',
            'inundation_method',
        ],
    },
    {
        type: 'cores',
        label: 'Cores',
        documentationName: 'cores',
        columns: [
            'study_id',
            'site_id',
            'core_id',
            'year',
            'month',
            'day',
            'core_notes',
            'latitude',
            'longitude',
            'position_accuracy',
            'position_method',
            'position_notes',
            'elevation',
            'elevation_datum',
            'elevation_accuracy',
            'elevation_method',
            'elevation_notes',
            'salinity_class',
            'salinity_method',
            'salinity_notes',
            'vegetation_class',
            'vegetation_method',
            'vegetation_notes',
            'habitat',
            'inundation_class',
            'inundation_method',
            'inundation_notes',
            'core_length_flag',
            'pb210_cic_accretion_rate',
            'pb210_cic_accretion_rate_se',
            'pb210_cic_notes',
            'pb210_cic_max_depth',
            'pb210_cic_r2',
        ],
        keyColumns: [
            'study_id',
            'site_id',
            'core_id',
            'year',
            'latitude',
            'longitude',
            'position_accuracy',
            'position_method',
            'salinity_class',
            'salinity_method',
            'vegetation_class',
            'vegetation_method',
            'habitat',
            'inundation_class',
            'inundation_method',
            'core_length_flag',
            'pb210_cic_accretion_rate_se',
            'pb210_cic_r2',
        ],
    },
    {
        type: 'depthseries',
        label: 'Depthseries',
        documentationName: 'depthseries',
        columns: [
            'study_id',
            'site_id',
            'core_id',
            'method_id',
            'depth_min',
            'depth_max',
            'representative_depth_min',
            'representative_depth_max',
            'sample_id',
            'dry_bulk_density',
            'fraction_organic_matter',
            'fraction_carbon',
            'compaction_fraction',
            'compaction_notes',
            'cs137_peak_age',
            'cs137_activity',
            'cs137_activity_se',
            'cs137_unit',
            'excess_pb210_activity',
            'excess_pb210_activity_se',
            'total_pb210_activity',
            'total_pb210_activity_se',
            'pb210_unit',
            'ra226_activity',
            'ra226_activity_se',
            'ra226_unit',
            'pb214_activity',
            'pb214_activity_se',
            'pb214_unit',
            'bi214_activity',
            'bi214_activity_se',
            'bi214_unit',
            'c14_age',
            'c14_age_se',
            'c14_material',
            'c14_notes',
            'delta_c13',
            'be7_activity',
            'be7_activity_se',
            'be7_unit',
            'marker_date',
            'marker_date_se',
            'marker_type',
            'marker_notes',
            'age',
            'age_min',
            'age_max',
            'age_se',
            'depth_interval_notes',
        ],
        keyColumns: [
            'study_id',
            'site_id',
            'core_id',
            'method_id',
            'depth_min',
            'depth_max',
            'dry_bulk_density',
            'fraction_organic_matter',
            'cs137_activity',
            'cs137_activity_se',
            'total_pb210_activity',
            'total_pb210_activity_se',
        ],
    },
    {
        type: 'impacts',
        label: 'Impacts',
        documentationName: 'impacts',
        columns: ['study_id', 'site_id', 'core_id', 'impact_class'],
        keyColumns: ['study_id', 'site_id', 'core_id', 'impact_class'],
    },
    {
        type: 'species',
        label: 'Species',
        documentationName: 'species',
        columns: ['study_id', 'site_id', 'core_id', 'species_code', 'code_type', 'habitat'],
        keyColumns: ['study_id', 'site_id', 'core_id', 'habitat'],
    },
] as const satisfies readonly ICcnColumnGuidanceDataset[]

export type TCcnDatasetType = (typeof CCN_COLUMN_GUIDANCE_DATASETS)[number]['type']

const TOKEN_ALIASES: Record<string, readonly string[]> = {
    accuracy: ['acc'],
    activity: ['act'],
    accretion: ['accr'],
    carbon: ['carb'],
    class: ['cls'],
    count: ['cnt'],
    density: ['dens'],
    description: ['desc'],
    fraction: ['frac'],
    identifier: ['id'],
    id: ['identifier', 'identification', 'ident'],
    latitude: ['lat'],
    longitude: ['lon', 'long', 'lng'],
    material: ['mat'],
    method: ['meth'],
    notes: ['note'],
    organic: ['org'],
    position: ['pos'],
    representative: ['rep'],
    sample: ['samp'],
    temperature: ['temp'],
    vegetation: ['veg'],
    volume: ['vol'],
}

function escapeRegex(value: string): string {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function normalizeCcnColumnName(value: string): string {
    return value
        .trim()
        .toLowerCase()
        .replace(/['’]/g, '')
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/(^|_)(pb|cs|ra|bi|be|c)_(\d+)(?=_|$)/g, '$1$2$3')
        .replace(/_+/g, '_')
        .replace(/^_|_$/g, '')
}

function tokenizeColumnName(value: string): string[] {
    const normalized = normalizeCcnColumnName(value)
    return normalized ? normalized.split('_') : []
}

function getSingularToken(token: string): string {
    if (token.length <= 3 || /\d/.test(token)) {
        return token
    }

    if (token.endsWith('ies')) {
        return `${token.slice(0, -3)}y`
    }

    if (token.endsWith('sses')) {
        return token.slice(0, -2)
    }

    if (token.endsWith('s')) {
        return token.slice(0, -1)
    }

    return token
}

function getTokenPattern(token: string): string {
    const parts = new Set([escapeRegex(token), ...(TOKEN_ALIASES[token] ?? []).map(escapeRegex)])

    if (!token.endsWith('s') && !/\d$/.test(token)) {
        parts.add(`${escapeRegex(token)}s`)
    }

    if (token.length >= 5) {
        parts.add(`${escapeRegex(token.slice(0, 4))}[a-z0-9]*`)
        parts.add(`${escapeRegex(getSingularToken(token).slice(0, 4))}[a-z0-9]*`)
    }

    return `(?:${Array.from(parts).join('|')})`
}

export function buildCcnColumnNameRegex(guidanceColumn: string): RegExp {
    const tokenPatterns = tokenizeColumnName(guidanceColumn).map(getTokenPattern)
    return new RegExp(`(?:^|[^a-z0-9])${tokenPatterns.join('[^a-z0-9]+')}(?:[^a-z0-9]+[a-z0-9]+)*$`, 'i')
}

function tokenMatchesGuidance(officialToken: string, candidateToken: string): boolean {
    if (officialToken === candidateToken) {
        return true
    }

    if (getSingularToken(officialToken) === getSingularToken(candidateToken)) {
        return true
    }

    if (TOKEN_ALIASES[officialToken]?.includes(candidateToken)) {
        return true
    }

    if (TOKEN_ALIASES[officialToken]?.includes(getSingularToken(candidateToken))) {
        return true
    }

    return officialToken.length >= 5 && candidateToken.length >= 3 && officialToken.startsWith(candidateToken)
}

function tokenSequencesMatch(candidateTokens: string[], officialTokens: string[]): boolean {
    if (candidateTokens.length !== officialTokens.length) {
        return false
    }

    return candidateTokens.every((token, index) => tokenMatchesGuidance(officialTokens[index], token))
}

function tokenSequenceStartsWith(candidateTokens: string[], officialTokens: string[]): boolean {
    if (candidateTokens.length < officialTokens.length) {
        return false
    }

    return officialTokens.every((token, index) => tokenMatchesGuidance(token, candidateTokens[index]))
}

function tokenSequenceIsLeadingShortening(candidateTokens: string[], officialTokens: string[]): boolean {
    if (candidateTokens.length >= officialTokens.length || candidateTokens.length === 0) {
        return false
    }

    const hasEnoughSignal = candidateTokens.length >= 2 || candidateTokens[0].length >= 3
    return hasEnoughSignal && candidateTokens.every((token, index) => tokenMatchesGuidance(officialTokens[index], token))
}

function tokenSequenceIsSuffixShortening(candidateTokens: string[], officialTokens: string[]): boolean {
    if (candidateTokens.length >= officialTokens.length || candidateTokens.length < 2) {
        return false
    }

    const suffixTokens = officialTokens.slice(officialTokens.length - candidateTokens.length)
    return candidateTokens.every((token, index) => tokenMatchesGuidance(suffixTokens[index], token))
}

function getGuidanceDataset(datasetType: TCcnDatasetType): ICcnColumnGuidanceDataset {
    return CCN_COLUMN_GUIDANCE_DATASETS.find((dataset) => dataset.type === datasetType) ?? CCN_COLUMN_GUIDANCE_DATASETS[0]
}

function normalizeColumnInput(input: string | ICcnColumnInput): ICcnColumnInput {
    return typeof input === 'string' ? { fieldName: input } : input
}

function findBestGuidanceMatch(input: string | ICcnColumnInput, dataset: ICcnColumnGuidanceDataset): ICcnColumnMatch | null {
    const columnInput = normalizeColumnInput(input)
    const normalizedFieldName = normalizeCcnColumnName(columnInput.fieldName)
    if (!normalizedFieldName) {
        return null
    }

    const exactGuidanceColumn = dataset.columns.find((column) => normalizeCcnColumnName(column) === normalizedFieldName)
    if (exactGuidanceColumn) {
        return {
            fieldId: columnInput.fieldId,
            fieldName: columnInput.fieldName,
            guidanceColumn: exactGuidanceColumn,
            matchType: 'exact',
            reason: 'Exact CCN guidance column name.',
        }
    }

    const candidateTokens = tokenizeColumnName(columnInput.fieldName)
    const candidates = dataset.columns
        .flatMap<{ score: number; match: ICcnColumnMatch }>((guidanceColumn) => {
            const officialTokens = tokenizeColumnName(guidanceColumn)
            const officialNameRegex = buildCcnColumnNameRegex(guidanceColumn)

            if (tokenSequenceStartsWith(candidateTokens, officialTokens)) {
                return [{
                    score: 80,
                    match: {
                        fieldId: columnInput.fieldId,
                        fieldName: columnInput.fieldName,
                        guidanceColumn,
                        matchType: 'variant' as const,
                        reason: 'Looks like the official name with appended text.',
                    },
                }]
            }

            if (tokenSequencesMatch(candidateTokens, officialTokens)) {
                return [{
                    score: 75,
                    match: {
                        fieldId: columnInput.fieldId,
                        fieldName: columnInput.fieldName,
                        guidanceColumn,
                        matchType: 'variant' as const,
                        reason: 'Uses shortened words or alternate separators.',
                    },
                }]
            }

            if (tokenSequenceIsLeadingShortening(candidateTokens, officialTokens)) {
                return [{
                    score: 70,
                    match: {
                        fieldId: columnInput.fieldId,
                        fieldName: columnInput.fieldName,
                        guidanceColumn,
                        matchType: 'variant' as const,
                        reason: 'Looks like a shortened form of the official name.',
                    },
                }]
            }

            if (tokenSequenceIsSuffixShortening(candidateTokens, officialTokens)) {
                return [{
                    score: 65,
                    match: {
                        fieldId: columnInput.fieldId,
                        fieldName: columnInput.fieldName,
                        guidanceColumn,
                        matchType: 'variant' as const,
                        reason: 'Looks like a shortened form with a leading qualifier removed.',
                    },
                }]
            }

            if (officialNameRegex.test(columnInput.fieldName)) {
                return [{
                    score: 60,
                    match: {
                        fieldId: columnInput.fieldId,
                        fieldName: columnInput.fieldName,
                        guidanceColumn,
                        matchType: 'variant' as const,
                        reason: 'Matches the official name pattern with flexible separators.',
                    },
                }]
            }

            return []
        })
        .sort((left, right) => right.score - left.score || left.match.guidanceColumn.length - right.match.guidanceColumn.length)

    return candidates[0]?.match ?? null
}

export function verifyCcnColumns(datasetType: TCcnDatasetType, fieldInputs: readonly (string | ICcnColumnInput)[]): ICcnColumnVerificationResult {
    const dataset = getGuidanceDataset(datasetType)
    const columnInputs = fieldInputs.map(normalizeColumnInput)
    const matches = columnInputs
        .map((fieldInput) => findBestGuidanceMatch(fieldInput, dataset))
        .filter((match): match is ICcnColumnMatch => match !== null)
    const matchedGuidanceColumns = new Set(matches.map((match) => match.guidanceColumn))
    const keyColumnSet = new Set(dataset.keyColumns)
    const missingColumns = dataset.columns.filter((column) => !matchedGuidanceColumns.has(column))
    const extraColumns = columnInputs.filter((fieldInput) => !findBestGuidanceMatch(fieldInput, dataset)).map((fieldInput) => fieldInput.fieldName)
    const matchesByGuidanceColumn = matches.reduce<Map<string, string[]>>((mapping, match) => {
        const fieldNamesForColumn = mapping.get(match.guidanceColumn) ?? []
        fieldNamesForColumn.push(match.fieldName)
        mapping.set(match.guidanceColumn, fieldNamesForColumn)
        return mapping
    }, new Map())

    return {
        dataset,
        fieldCount: columnInputs.length,
        expectedColumnCount: dataset.columns.length,
        exactMatches: matches.filter((match) => match.matchType === 'exact'),
        variantMatches: matches.filter((match) => match.matchType === 'variant'),
        missingColumns,
        missingKeyColumns: missingColumns.filter((column) => keyColumnSet.has(column)),
        missingOptionalColumns: missingColumns.filter((column) => !keyColumnSet.has(column)),
        extraColumns,
        duplicateMatches: Array.from(matchesByGuidanceColumn.entries())
            .filter(([, matchedFieldNames]) => matchedFieldNames.length > 1)
            .map(([guidanceColumn, matchedFieldNames]) => ({ guidanceColumn, fieldNames: matchedFieldNames })),
    }
}