import type { Entry, FileEntry } from '@zip.js/zip.js';
import {
    BlobReader,
    BlobWriter,
    Uint8ArrayReader,
    Uint8ArrayWriter,
    ZipReader,
    ZipWriter,
} from '@zip.js/zip.js';

/**
 * Shrink a Google Takeout ZIP to just the parts Ido reads.
 *
 * A YouTube export is mostly the user's own uploaded videos -- 581 MB of 612 MB in the
 * archive this was built against -- and none of it is ever opened. Uploading it means
 * minutes of waiting and, on a hosted backend, usually a proxy timeout before the
 * request even arrives.
 *
 * So the browser does the trimming. A ZIP keeps its index at the END of the file, so a
 * random-access reader can list the entries and pull out three small members without
 * touching the video data at all. That is why this uses BlobReader (which reads through
 * Blob.slice) rather than loading the file into an ArrayBuffer -- a 612 MB buffer would
 * be a good way to crash the tab.
 *
 * Falls back to the original file whenever trimming would not help or cannot be done,
 * so a user is never blocked by this step.
 */

/** Basenames the backend's history locator looks for. */
const WANTED = new Set([
    'watch-history.json',
    'watch-history.html',
    'search-history.json',
    'search-history.html',
    'subscriptions.csv',
]);

/** Below this, trimming is not worth the wait -- just send the original. */
const WORTH_TRIMMING_BYTES = 20 * 1024 * 1024;

/** Takeout's HTML history is a flat run of these; each one is a single activity. */
const CELL_MARKER = '<div class="outer-cell';

/** The date line inside a cell, e.g. "Aug 21, 2026,". */
const CELL_DATE = /([A-Z][a-z]{2}) \d{1,2}, ((?:19|20)\d{2}),/;

/**
 * Drop history cells that do not belong to the chosen year.
 *
 * The backend already filters by year, but only after scanning and timestamp-mapping
 * every cell in the file -- about 1.7s of work on a 42,500-entry export that is then
 * thrown away. The date is plain text inside each cell, so the browser can cut them
 * with string operations alone: no HTML parsing, no date parsing.
 *
 * The boundary rule matters. Timestamps are wall-clock in the exporter's timezone and
 * the backend re-bins them in the viewer's, which can move a watch across midnight --
 * so December of the previous year and January of the next are kept. An earlier version
 * kept the whole neighbouring years, which sounds safer but removed nothing at all from
 * a two-year export: the margin has to be a few hours wide, not twelve months.
 *
 * Conservative everywhere else: an undated cell is kept, an unfamiliar layout is left
 * alone, and if filtering would empty the file the original is returned. Losing history
 * silently is far worse than being slow.
 */
function filterHtmlToYear(html: string, year: number): string {
    const first = html.indexOf(CELL_MARKER);
    if (first === -1) return html;              // not the layout we expect

    const head = html.slice(0, first);
    const parts = html.slice(first).split(CELL_MARKER);
    const kept: string[] = [];
    let tail = '';

    for (let i = 1; i < parts.length; i++) {
        const cell = CELL_MARKER + parts[i];
        let content = cell;

        // The final cell carries the document's closing tags; keep them regardless.
        if (i === parts.length - 1) {
            const close = cell.lastIndexOf('</div></div>');
            if (close !== -1) {
                tail = cell.slice(close + '</div></div>'.length);
                content = cell.slice(0, close + '</div></div>'.length);
            }
        }

        const match = content.match(CELL_DATE);
        if (!match) {
            kept.push(content);                 // undated: the backend decides
            continue;
        }

        const month = match[1];
        const cellYear = Number(match[2]);
        if (
            cellYear === year ||
            (cellYear === year - 1 && month === 'Dec') ||
            (cellYear === year + 1 && month === 'Jan')
        ) {
            kept.push(content);
        }
    }

    // Filtering everything means the year guess was wrong for this file -- send it whole
    // so the backend can report which years the export actually contains.
    if (kept.length === 0) return html;
    return head + kept.join('') + tail;
}

export interface StripResult {
    file: File;
    /** True when a smaller archive was actually built. */
    trimmed: boolean;
    originalBytes: number;
    finalBytes: number;
    /** Set when trimming was skipped or failed; the original file is used. */
    reason?: string;
}

const basename = (path: string) => path.split('/').pop()?.toLowerCase() ?? '';

// zip.js types Entry as DirectoryEntry | FileEntry, and getData exists only on the
// file half -- so narrowing has to happen through a predicate, not a plain filter.
const isWantedFile = (entry: Entry): entry is FileEntry =>
    !entry.directory && WANTED.has(basename(entry.filename));

export async function stripTakeout(
    file: File,
    onProgress?: (message: string) => void,
    year?: number
): Promise<StripResult> {
    const originalBytes = file.size;
    const unchanged = (reason: string): StripResult => ({
        file,
        trimmed: false,
        originalBytes,
        finalBytes: originalBytes,
        reason,
    });

    if (originalBytes < WORTH_TRIMMING_BYTES) {
        return unchanged('already small');
    }

    let reader: ZipReader<unknown> | undefined;
    try {
        onProgress?.('Reading your archive…');

        // BlobReader gives random access: zip.js reads the central directory from the
        // end of the file and then seeks only to the entries we ask for.
        reader = new ZipReader(new BlobReader(file));
        const entries = await reader.getEntries();

        const keep = entries.filter(isWantedFile);

        if (keep.length === 0) {
            // Not a YouTube Takeout, or an unexpected layout. Let the backend decide
            // rather than silently sending an empty archive.
            return unchanged('no history files found');
        }

        onProgress?.('Removing your videos…');

        const writer = new ZipWriter(new BlobWriter('application/zip'));
        const decoder = new TextDecoder();
        const encoder = new TextEncoder();

        for (const entry of keep) {
            let data: Uint8Array = await entry.getData(new Uint8ArrayWriter());

            // History files are the big ones and the only ones with dated rows.
            if (year && /history\.html$/i.test(entry.filename)) {
                const filtered = filterHtmlToYear(decoder.decode(data), year);
                data = encoder.encode(filtered);
            }
            // Paths are preserved: the backend locates members by basename at any
            // depth, but keeping the original layout means the archive is still a
            // valid Takeout if anyone opens it.
            await writer.add(entry.filename, new Uint8ArrayReader(data));
        }

        const blob = await writer.close();
        const trimmed = new File([blob], file.name.replace(/\.zip$/i, '') + '-history.zip', {
            type: 'application/zip',
        });

        // Trimming should shrink things; if it somehow did not, keep the original.
        if (trimmed.size >= originalBytes) {
            return unchanged('nothing to remove');
        }

        return {
            file: trimmed,
            trimmed: true,
            originalBytes,
            finalBytes: trimmed.size,
        };
    } catch (error) {
        // A corrupt or unusual archive is the backend's problem to report, with its
        // much better error messages. Never block the upload on this optimisation.
        return unchanged(
            error instanceof Error ? error.message : 'could not read the archive'
        );
    } finally {
        await reader?.close().catch(() => undefined);
    }
}

/** "612 MB" / "3.5 MB" / "96 KB" */
export function formatBytes(bytes: number): string {
    if (bytes >= 1024 * 1024 * 1024) return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
    if (bytes >= 1024 * 1024) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
    if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${bytes} B`;
}
