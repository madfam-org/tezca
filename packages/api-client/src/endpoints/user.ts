/**
 * User endpoint methods (requires JWT auth).
 */

import type {
  UserPreferences,
  AnnotationData,
  CreateAnnotationParams,
  NotificationData,
  AlertData,
  CreateAlertParams,
} from "../types";

export class UserEndpoint {
  readonly annotations: AnnotationsSubEndpoint;
  readonly alerts: AlertsSubEndpoint;
  readonly notifications: NotificationsSubEndpoint;

  constructor(
    private request: <T>(path: string, params?: Record<string, string>) => Promise<T>,
    private requestBody: <T>(method: string, path: string, body?: unknown) => Promise<T>,
  ) {
    this.annotations = new AnnotationsSubEndpoint(request, requestBody);
    this.alerts = new AlertsSubEndpoint(request, requestBody);
    this.notifications = new NotificationsSubEndpoint(request, requestBody);
  }

  /** Get user preferences, bookmarks, and recently viewed. */
  async preferences(): Promise<UserPreferences> {
    return this.request("/user/preferences/");
  }

  /** Add a law to bookmarks. */
  async addBookmark(lawId: string): Promise<{ bookmarks: string[] }> {
    return this.requestBody("POST", "/user/bookmarks/", { law_id: lawId });
  }

  /** Remove a law from bookmarks. */
  async removeBookmark(lawId: string): Promise<{ bookmarks: string[] }> {
    return this.requestBody("DELETE", "/user/bookmarks/", { law_id: lawId });
  }

  /** Record a law view (for recently viewed). */
  async recordView(lawId: string): Promise<void> {
    await this.requestBody("POST", "/user/recently-viewed/", { law_id: lawId });
  }
}

class AnnotationsSubEndpoint {
  constructor(
    private request: <T>(path: string, params?: Record<string, string>) => Promise<T>,
    private requestBody: <T>(method: string, path: string, body?: unknown) => Promise<T>,
  ) {}

  /** List annotations, optionally filtered by law_id. */
  async list(lawId?: string): Promise<AnnotationData[]> {
    const params = lawId ? { law_id: lawId } : undefined;
    return this.request("/user/annotations/", params);
  }

  /** Create an annotation. */
  async create(params: CreateAnnotationParams): Promise<AnnotationData> {
    return this.requestBody("POST", "/user/annotations/", params);
  }

  /** Update an annotation's text. */
  async update(annotationId: number, text: string): Promise<AnnotationData> {
    return this.requestBody("PATCH", `/user/annotations/${annotationId}/`, { text });
  }

  /** Delete an annotation. */
  async delete(annotationId: number): Promise<void> {
    await this.requestBody("DELETE", `/user/annotations/${annotationId}/`);
  }
}

class AlertsSubEndpoint {
  constructor(
    private request: <T>(path: string, params?: Record<string, string>) => Promise<T>,
    private requestBody: <T>(method: string, path: string, body?: unknown) => Promise<T>,
  ) {}

  /** List active alerts. */
  async list(): Promise<AlertData[]> {
    return this.request("/user/alerts/");
  }

  /** Create an alert subscription. */
  async create(params: CreateAlertParams): Promise<AlertData> {
    return this.requestBody("POST", "/user/alerts/", params);
  }

  /** Delete an alert. */
  async delete(alertId: number): Promise<void> {
    await this.requestBody("DELETE", `/user/alerts/${alertId}/`);
  }
}

class NotificationsSubEndpoint {
  constructor(
    private request: <T>(path: string, params?: Record<string, string>) => Promise<T>,
    private requestBody: <T>(method: string, path: string, body?: unknown) => Promise<T>,
  ) {}

  /** List notifications. */
  async list(): Promise<NotificationData[]> {
    return this.request("/user/notifications/");
  }

  /** Mark notifications as read. */
  async markRead(notificationIds?: number[]): Promise<{ updated: number }> {
    return this.requestBody("POST", "/user/notifications/mark-read/", {
      notification_ids: notificationIds,
    });
  }
}
