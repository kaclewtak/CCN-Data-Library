import { act, render } from '@testing-library/react'
import { useEffect } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { createSheetActivationCommitOptions, type ICcnSpreadsheetState, useCcnSpreadsheetState } from './useCcnSpreadsheetState'

afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    window.localStorage.clear()
})

function SpreadsheetHarness(props: { onState: (state: ICcnSpreadsheetState) => void }) {
    const state = useCcnSpreadsheetState({
        enabled: true,
        config: {
            enabled: true,
            datasetFingerprint: 'startup::test-session',
            datasetLabel: 'Uploaded dataset',
            autosaveDebounceMs: 100000,
            syncDebounceMs: 10,
            historyLimit: 10,
        },
        bridgeConfig: {
            enabled: true,
            bridgeId: 'bridge-123',
            targetOrigin: '*',
        },
        initialRows: [{ column_1: null }],
        initialFields: [
            {
                fid: 'column_1',
                name: 'Column 1',
                offset: 0,
                semanticType: 'nominal',
                analyticType: 'dimension',
            } as any,
        ],
    })

    useEffect(() => {
        props.onState(state)
    }, [props, state])

    return null
}

describe('useCcnSpreadsheetState', () => {
    it('creates immediate graph-sync commit options for sheet activation events', () => {
        expect(createSheetActivationCommitOptions(1234567890, 'uploaded-sheet')).toEqual({
            dirty: false,
            historyMode: 'replace',
            lastSavedAt: 1234567890,
            nextSheetName: 'uploaded-sheet',
            syncGraphSnapshot: true,
        })
    })

    it('syncs user-edited startup sheet data through the shared dataset bridge', async () => {
        vi.useFakeTimers()
        const postMessage = vi.fn()
        Object.defineProperty(window, 'parent', {
            configurable: true,
            value: { postMessage },
        })

        let latestState: ICcnSpreadsheetState | null = null
        render(<SpreadsheetHarness onState={(state) => { latestState = state }} />)

        await act(async () => {
            await Promise.resolve()
            vi.advanceTimersByTime(20)
        })
        expect(postMessage).not.toHaveBeenCalled()

        await act(async () => {
            latestState!.commitCellValue(0, 'column_1', '0.12')
        })
        await act(async () => {
            vi.advanceTimersByTime(20)
            await Promise.resolve()
        })

        expect(postMessage).toHaveBeenCalledTimes(1)
        const [payload, targetOrigin] = postMessage.mock.calls[0]
        expect(targetOrigin).toBe('*')
        expect(payload).toMatchObject({
            type: 'ccn:shared-dataset-sync',
            bridgeId: 'bridge-123',
            hasUploadedData: true,
            datasetFingerprint: 'startup::test-session',
            datasetLabel: 'Uploaded dataset',
            sheetName: 'Uploaded dataset',
        })
        expect(payload.fields).toEqual(expect.arrayContaining([expect.objectContaining({ name: 'Column 1' })]))
        expect(payload.rows).toEqual([{ column_1: '0.12' }])
    })
})