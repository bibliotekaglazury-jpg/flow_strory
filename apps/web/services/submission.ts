import type { GenerationInput } from "@ugc/contracts";
import { ServiceError } from "./http";
export interface PendingSubmission {
  key: string;
  input: GenerationInput;
}
export function prepareSubmission(
  pending: PendingSubmission | null,
  input: GenerationInput,
  newKey = () => crypto.randomUUID(),
): PendingSubmission {
  return pending ?? { key: newKey(), input: structuredClone(input) };
}
export function submissionFailed(
  pending: PendingSubmission,
  error: unknown,
): PendingSubmission | null {
  // Only a definite application rejection permits a new admission attempt.
  return error instanceof ServiceError &&
    !error.retryable &&
    ![
      "NETWORK_ERROR",
      "REQUEST_FAILED",
      "UNAUTHENTICATED",
      "INTERNAL_ERROR",
    ].includes(error.code)
    ? null
    : pending;
}
