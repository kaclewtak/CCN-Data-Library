import { describe, expect, it } from 'vitest'

import {
    buildCcnColumnNameRegex,
    normalizeCcnColumnName,
    verifyCcnColumns,
} from './ccnColumnGuidance'

describe('CCN column guidance verification', () => {
    it('normalizes human-readable CCN column labels', () => {
        expect(normalizeCcnColumnName('Study ID')).toBe('study_id')
        expect(normalizeCcnColumnName('Pb-210 Unit')).toBe('pb210_unit')
        expect(normalizeCcnColumnName('Delta C-13')).toBe('delta_c13')
    })

    it('matches exact guidance columns after normalization', () => {
        const result = verifyCcnColumns('impacts', ['Study ID', 'site_id', 'Core ID', 'impact_class'])

        expect(result.missingColumns).toEqual([])
        expect(result.extraColumns).toEqual([])
        expect(result.exactMatches).toHaveLength(4)
    })

    it('flags appended and shortened names as likely variants', () => {
        const result = verifyCcnColumns('depthseries', [
            'study_id',
            'site_id',
            'core_ids',
            'method_id',
            'depth_min_cm',
            'depth_max_cm',
            'dry_bulk_density_g_cm3',
            'fraction_org_matter',
        ])

        expect(result.variantMatches.map((match) => match.guidanceColumn)).toEqual(expect.arrayContaining([
            'core_id',
            'depth_min',
            'depth_max',
            'dry_bulk_density',
            'fraction_organic_matter',
        ]))
        expect(result.extraColumns).toEqual([])
    })

    it('uses regex patterns for flexible separators and appended text', () => {
        expect(buildCcnColumnNameRegex('loss_on_ignition_temperature').test('Loss On Ignition Temperature C')).toBe(true)
        expect(buildCcnColumnNameRegex('site_latitude_max').test('Site Lat Max')).toBe(true)
        expect(buildCcnColumnNameRegex('core_id').test('core_ids')).toBe(true)
    })

    it('retains field IDs for coercing matched variants', () => {
        const result = verifyCcnColumns('cores', [
            { fieldId: 'core_ids', fieldName: 'core_ids' },
            { fieldId: 'lat', fieldName: 'lat' },
        ])

        expect(result.variantMatches).toEqual(expect.arrayContaining([
            expect.objectContaining({ fieldId: 'core_ids', fieldName: 'core_ids', guidanceColumn: 'core_id' }),
            expect.objectContaining({ fieldId: 'lat', fieldName: 'lat', guidanceColumn: 'latitude' }),
        ]))
    })

    it('reports missing key columns separately from other guidance columns', () => {
        const result = verifyCcnColumns('species', ['study_id', 'species_code', 'unknown_column'])

        expect(result.missingKeyColumns).toEqual(expect.arrayContaining(['site_id', 'core_id', 'habitat']))
        expect(result.missingOptionalColumns).toEqual(expect.arrayContaining(['code_type']))
        expect(result.extraColumns).toEqual(['unknown_column'])
    })
})
