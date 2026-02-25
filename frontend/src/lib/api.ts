/**
 * API client for the Music Sheet Maker backend.
 */

export interface TranscribeResponse {
	job_id: string;
}

export interface ProgressEvent {
	status: string;
	progress: number;
	message: string;
}

export interface ChordInfo {
	time: number;
	chord: string;
}

export interface TranscriptionResult {
	musicxml: string;
	midi_b64: string;
	bpm: number;
	key: string;
	title: string;
	chords: ChordInfo[];
}

/**
 * Upload an audio file and start transcription.
 */
export async function uploadFile(file: File): Promise<TranscribeResponse> {
	const formData = new FormData();
	formData.append('file', file);

	const res = await fetch('/api/transcribe', {
		method: 'POST',
		body: formData,
	});

	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: res.statusText }));
		throw new Error(err.detail || `Upload failed: ${res.status}`);
	}

	return res.json();
}

/**
 * Subscribe to job progress via Server-Sent Events.
 * Calls onProgress for each update, resolves when done, rejects on error.
 */
export function subscribeToProgress(
	jobId: string,
	onProgress: (event: ProgressEvent) => void,
): Promise<void> {
	return new Promise((resolve, reject) => {
		const source = new EventSource(`/api/jobs/${jobId}/stream`);

		source.addEventListener('progress', (e: MessageEvent) => {
			try {
				const data: ProgressEvent = JSON.parse(e.data);
				onProgress(data);

				if (data.status === 'done') {
					source.close();
					resolve();
				} else if (data.status === 'error') {
					source.close();
					reject(new Error(data.message));
				}
			} catch (err) {
				source.close();
				reject(err);
			}
		});

		source.onerror = () => {
			source.close();
			reject(new Error('Connection to server lost.'));
		};
	});
}

/**
 * Fetch the completed transcription result.
 */
export async function fetchResult(jobId: string): Promise<TranscriptionResult> {
	const res = await fetch(`/api/jobs/${jobId}/result`);

	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: res.statusText }));
		throw new Error(err.detail || `Fetch result failed: ${res.status}`);
	}

	return res.json();
}
