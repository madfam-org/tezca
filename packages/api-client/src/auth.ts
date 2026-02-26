/**
 * Authentication strategies for the Tezca API client.
 */

export interface AuthStrategy {
  getHeaders(): Record<string, string>;
}

export class APIKeyAuth implements AuthStrategy {
  constructor(private apiKey: string) {}

  getHeaders(): Record<string, string> {
    return { "X-API-Key": this.apiKey };
  }
}

export class JWTAuth implements AuthStrategy {
  constructor(private token: string) {}

  getHeaders(): Record<string, string> {
    return { Authorization: `Bearer ${this.token}` };
  }
}
