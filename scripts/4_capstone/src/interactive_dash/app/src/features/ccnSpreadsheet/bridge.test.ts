import { describe, expect, it, vi } from 'vitest'

import {
    buildDatasetFingerprint,
    buildImportedDatasetIdentity,
    buildPersistedDatasetIdentity,
    createSharedDatasetSyncPayload,
    postSharedDatasetSyncPayload,
    resolveVisualizationDatasetFingerprint,
} from './bridge'

describe('shared dataset bridge helpers', () => {
    const snapshot = {
        fields: [
            { fid: 'study_id', name: 'Study ID', offset: 0, semanticType: 'nominal', analyticType: 'dimension' } as any,
            { fid: 'latitude', name: 'Latitude', offset: 0, semanticType: 'quantitative', analyticType: 'measure' } as any,
        ],
        rows: [
            { study_id: 'A1', latitude: 12.5 },
            { study_id: 'B2', latitude: 13.5 },
        ],
    }

    it('builds deterministic dataset fingerprints', () => {
        expect(buildDatasetFingerprint(snapshot)).toBe(buildDatasetFingerprint(snapshot))
        expect(
            buildDatasetFingerprint({
                ...snapshot,
                rows: [{ study_id: 'A1', latitude: 12.5 }],
            }),
        ).not.toBe(buildDatasetFingerprint(snapshot))
    })

    it('creates imported dataset identities from spreadsheet imports', () => {
        const identity = buildImportedDatasetIdentity({
            ...snapshot,
            name: 'uploaded-sheet',
            fileName: 'uploaded.csv',
            source: 'csv',
        })

        expect(identity.datasetLabel).toBe('uploaded-sheet')
        expect(identity.datasetFingerprint.startsWith('dataset::')).toBe(true)
    })

    it('resolves the visualization dataset fingerprint from the active imported dataset', () => {
        const importedIdentity = buildImportedDatasetIdentity({
            ...snapshot,
            name: 'uploaded-sheet',
            fileName: 'uploaded.csv',
            source: 'csv',
        })

        expect(
            resolveVisualizationDatasetFingerprint({
                activeDatasetIdentity: importedIdentity,
                defaultDatasetFingerprint: 'startup::ccn-test',
            }),
        ).toBe(importedIdentity.datasetFingerprint)

        expect(
            resolveVisualizationDatasetFingerprint({
                activeDatasetIdentity: null,
                defaultDatasetFingerprint: 'startup::ccn-test',
            }),
        ).toBe('startup::ccn-test')

        expect(
            resolveVisualizationDatasetFingerprint({
                activeDatasetIdentity: buildPersistedDatasetIdentity({
                    datasetFingerprint: 'dataset::persisted',
                    datasetLabel: 'Loaded sheet',
                    name: 'Loaded sheet',
                }),
                defaultDatasetFingerprint: 'startup::ccn-test',
            }),
        ).toBe('dataset::persisted')
    })

    it('builds sync payloads with bridge and file metadata', () => {
        const payload = createSharedDatasetSyncPayload({
            bridgeConfig: {
                enabled: true,
                bridgeId: 'bridge-123',
            },
            sequence: 7,
            datasetIdentity: {
                datasetFingerprint: 'dataset::123',
                datasetLabel: 'Uploaded dataset',
            },
            sheetName: 'uploaded-sheet',
            snapshot,
            currentExternalFile: {
                fileName: 'uploaded.csv',
                source: 'csv',
            },
        })

        expect(payload.bridgeId).toBe('bridge-123')
        expect(payload.sequence).toBe(7)
        expect(payload.fileName).toBe('uploaded.csv')
        expect(payload.rows).toEqual(snapshot.rows)
    })

    it('posts sync payloads to the parent window when the bridge is enabled', () => {
        const postMessage = vi.fn()
        Object.defineProperty(window, 'parent', {
            configurable: true,
            value: { postMessage },
        })

        const payload = createSharedDatasetSyncPayload({
            bridgeConfig: {
                enabled: true,
                bridgeId: 'bridge-123',
                targetOrigin: '*',
            },
            sequence: 1,
            datasetIdentity: {
                datasetFingerprint: 'dataset::123',
                datasetLabel: 'Uploaded dataset',
            },
            sheetName: 'uploaded-sheet',
            snapshot,
        })

        postSharedDatasetSyncPayload(payload, {
            enabled: true,
            bridgeId: 'bridge-123',
            targetOrigin: '*',
        })

        expect(postMessage).toHaveBeenCalledWith(payload, '*')
    })
})