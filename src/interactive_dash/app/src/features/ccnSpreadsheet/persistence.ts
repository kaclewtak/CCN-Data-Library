import type { IPersistedSheet } from './types'

const DB_NAME = 'ccn-pygwalker-spreadsheet'
const LOCAL_STORAGE_KEY = 'ccn-pygwalker-spreadsheet-store'
const STORE_NAME = 'sheets'

const memoryStore = new Map<string, IPersistedSheet>()

function supportsIndexedDb(): boolean {
    return typeof window !== 'undefined' && 'indexedDB' in window
}

function readLocalStorageStore(): Record<string, IPersistedSheet> {
    if (typeof window === 'undefined' || !window.localStorage) {
        return {}
    }

    try {
        const rawValue = window.localStorage.getItem(LOCAL_STORAGE_KEY)
        return rawValue ? (JSON.parse(rawValue) as Record<string, IPersistedSheet>) : {}
    } catch {
        return {}
    }
}

function writeLocalStorageStore(store: Record<string, IPersistedSheet>) {
    if (typeof window === 'undefined' || !window.localStorage) {
        return
    }

    window.localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(store))
}

async function openDatabase(): Promise<IDBDatabase | null> {
    if (!supportsIndexedDb()) {
        return null
    }

    return new Promise((resolve, reject) => {
        const request = window.indexedDB.open(DB_NAME, 1)

        request.onupgradeneeded = () => {
            const database = request.result
            if (!database.objectStoreNames.contains(STORE_NAME)) {
                database.createObjectStore(STORE_NAME, { keyPath: 'id' })
            }
        }
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error)
    })
}

async function withStorageFallback<T>(
    indexedDbOperation: (database: IDBDatabase) => Promise<T>,
    fallbackOperation: () => T | Promise<T>,
): Promise<T> {
    try {
        const database = await openDatabase()

        if (!database) {
            return await fallbackOperation()
        }

        return await indexedDbOperation(database)
    } catch {
        return await fallbackOperation()
    }
}

export function getAutosaveSheetId(datasetFingerprint: string): string {
    return `autosave::${datasetFingerprint}`
}

export async function saveSheetRecord(sheet: IPersistedSheet): Promise<void> {
    await withStorageFallback(
        async (database) => {
            await new Promise<void>((resolve, reject) => {
                const transaction = database.transaction(STORE_NAME, 'readwrite')
                const store = transaction.objectStore(STORE_NAME)
                const request = store.put(sheet)

                request.onsuccess = () => resolve()
                request.onerror = () => reject(request.error)
            })
        },
        () => {
            const localStorageStore = readLocalStorageStore()
            localStorageStore[sheet.id] = sheet
            writeLocalStorageStore(localStorageStore)
            memoryStore.set(sheet.id, sheet)
        },
    )
}

export async function listSheetsForFingerprint(datasetFingerprint: string): Promise<IPersistedSheet[]> {
    return withStorageFallback(
        async (database) => {
            const allSheets = await new Promise<IPersistedSheet[]>((resolve, reject) => {
                const transaction = database.transaction(STORE_NAME, 'readonly')
                const store = transaction.objectStore(STORE_NAME)
                const request = store.getAll()

                request.onsuccess = () => resolve((request.result as IPersistedSheet[]) ?? [])
                request.onerror = () => reject(request.error)
            })

            return allSheets
                .filter((sheet) => sheet.datasetFingerprint === datasetFingerprint)
                .sort((left, right) => right.updatedAt - left.updatedAt)
        },
        () => {
            const merged = {
                ...readLocalStorageStore(),
                ...Object.fromEntries(memoryStore.entries()),
            }

            return Object.values(merged)
                .filter((sheet) => sheet.datasetFingerprint === datasetFingerprint)
                .sort((left, right) => right.updatedAt - left.updatedAt)
        },
    )
}
