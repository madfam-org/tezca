/**
 * Custom error classes for the Tezca API client.
 */

export class TezcaAPIError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown,
  ) {
    super(message);
    this.name = "TezcaAPIError";
  }
}

export class RateLimitError extends TezcaAPIError {
  constructor(
    public retryAfter: number,
    body?: unknown,
  ) {
    super(429, `Rate limit exceeded. Retry after ${retryAfter}s`, body);
    this.name = "RateLimitError";
  }
}

export class AuthError extends TezcaAPIError {
  constructor(message = "Authentication failed") {
    super(401, message);
    this.name = "AuthError";
  }
}

export class ForbiddenError extends TezcaAPIError {
  constructor(message = "Insufficient permissions") {
    super(403, message);
    this.name = "ForbiddenError";
  }
}
