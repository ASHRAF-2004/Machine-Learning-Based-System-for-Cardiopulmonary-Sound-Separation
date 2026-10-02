export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}
type TokenSource = (force?: boolean) => Promise<string>;
type FeedbackPage = {limit:number;offset?:number};
const messages: Record<string, string> = {
  email_verification_required: 'Verify your email before opening the workspace.',
  account_disabled: 'This account is restricted. Contact the project owner.',
  forbidden: 'You do not have permission for this action or resource.',
  account_missing: 'Your application account has not been synchronized. Retry sign-in.',
  ensemble_unavailable: 'Ensemble processing is not connected yet. No job or result was created.',
  separation_unavailable: 'Separation is temporarily unavailable. Your original recording is saved.',
  benchmark_unavailable: 'Benchmark execution is not available in this runtime.',
  last_admin: 'The last active administrator cannot be disabled or demoted.',
  upload_too_large: 'Choose a WAV file no larger than 25 MiB.',
  invalid_handle: 'Start with a letter. Use 3–20 letters, numbers, dots or underscores, without consecutive or ending separators.',
  reserved_handle: 'That handle is reserved. Try another name.',
  handle_unavailable: 'That handle is already in use. Try another name.',
  handle_change_used: 'Your one self-service handle change has already been used.',
  identity_unavailable: 'Your handle or public reference could not be saved. Please retry.',
  recipient_unavailable: 'No available person matches that confirmed handle. Check the spelling and find the person again.',
  sharing_lookup_limited: 'Too many lookups. Please wait before finding another person.',
  invalid_grant: 'That permission or expiry could not be accepted. Check the sharing options.',
};
export function createApiClient(token: TokenSource, onSessionExpired: () => void, transport: typeof fetch = fetch) {
  async function request(path: string, init: RequestInit = {}, page?:FeedbackPage): Promise<Response> {
    // Callers supply API-relative paths, never response URLs, absolute URLs or query tokens.
    if (!/^\/[a-z][a-z0-9/_-]*$/i.test(path) || path.includes('//') || path.includes('..')) throw new Error('Invalid API path.');
    // Pagination is typed numeric data, never a caller-supplied URL/query/token.
    let suffix='';
    if(page){
      if(!(path==='/reviews/history'||/^\/recordings\/[a-z0-9_-]+\/reviews$/i.test(path))||!Number.isSafeInteger(page.limit)||page.limit<1||page.limit>20||!Number.isSafeInteger(page.offset??0)||(page.offset??0)<0)throw new Error('Invalid feedback page.');
      suffix=`?limit=${page.limit}&offset=${page.offset??0}`;
    }
    for (let attempt = 0; attempt < 2; attempt++) {
      let bearer: string;
      try { bearer = await token(attempt === 1); } catch (error) { if (error instanceof DOMException && error.name === 'AbortError') throw error; onSessionExpired(); throw new ApiError(401, 'session_expired', 'Your session has expired. Sign in again.'); }
      const headers = new Headers(init.headers);
      headers.set('Authorization', `Bearer ${bearer}`);
      headers.set('Accept', 'application/json');
      if (typeof init.body === 'string') headers.set('Content-Type', 'application/json');
      let response: Response;
      try {
        response = await transport(`/api${path}${suffix}`, {...init, headers, credentials: 'omit', cache: 'no-store', redirect: 'error', referrerPolicy: 'no-referrer'});
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') throw error;
        throw new ApiError(0, 'network_unavailable', 'The application service could not be reached. Check your connection and retry.');
      }
      if (response.status === 401 && attempt === 0) continue;
      if (response.status === 401) onSessionExpired();
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const code = typeof body?.detail?.code === 'string' ? body.detail.code : 'request_failed';
        const fallback = response.status === 401 ? 'Your session has expired. Sign in again.' : response.status === 403 ? 'You do not have permission for this action or resource.' : response.status === 404 ? 'This resource is unavailable or you no longer have access.' : response.status === 422 ? 'The supplied values could not be accepted. Check the fields and retry.' : response.status === 503 ? 'This service is not configured or is temporarily unavailable. No demo data will be substituted.' : 'The request could not be completed. Please retry.';
        throw new ApiError(response.status, code, messages[code] || fallback);
      }
      return response;
    }
    throw new ApiError(401, 'session_expired', 'Sign in again.');
  }
  return {
    async checkMedia(id: string, signal?: AbortSignal): Promise<void> {
      // Recheck current resource authority without downloading private audio again.
      await request(`/media/${id}`, {method: 'HEAD', signal});
    },
    async json<T>(path: string, init?: RequestInit, page?:FeedbackPage): Promise<T> { const response = await request(path, init, page); return response.status === 204 ? undefined as T : response.json(); },
    async media(id: string, signal?: AbortSignal): Promise<Blob> {
      const response = await request(`/media/${id}`, {signal});
      const type = response.headers.get('Content-Type')?.split(';')[0] || '';
      if (!['audio/wav', 'audio/x-wav', 'audio/wave', 'audio/mpeg', 'audio/ogg', 'image/png', 'image/webp', 'image/jpeg'].includes(type)) throw new Error('Unsupported protected media type.');
      return response.blob();
    },
  };
}
export type ApiClient = ReturnType<typeof createApiClient>;
