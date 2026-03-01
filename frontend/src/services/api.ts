// Servicio API para la plataforma OSINT

import type { ApiResponse, AuthResponse, LoginCredentials, User, Investigation, Entity, DashboardStats, TransformExecution } from '../types';

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ??
  'http://localhost:8000';

class ApiService {
  private token: string | null = null;

  constructor() {
    // Recuperar token del localStorage al inicializar
    this.token = localStorage.getItem('auth_token') || localStorage.getItem('access_token');
  }

  private resolveUrl(path: string): string {
    return API_BASE_URL ? `${API_BASE_URL}${path}` : path;
  }

  private clearAuthStorage() {
    this.token = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  }

  private async refreshAccessToken(): Promise<string | null> {
    const refresh = localStorage.getItem('refresh_token');
    if (!refresh) return null;

    try {
      const response = await fetch(this.resolveUrl('/api/auth/token/refresh/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      });

      if (!response.ok) {
        this.clearAuthStorage();
        return null;
      }

      const data: any = await response.json().catch(() => null);
      const access = data?.access;
      if (typeof access !== 'string' || !access) {
        this.clearAuthStorage();
        return null;
      }

      localStorage.setItem('access_token', access);
      localStorage.setItem('auth_token', access);
      this.token = access;
      return access;
    } catch {
      this.clearAuthStorage();
      return null;
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retryCount = 0
  ): Promise<ApiResponse<T>> {
    const url = this.resolveUrl(endpoint);
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add existing headers if any
    if (options.headers) {
      Object.assign(headers, options.headers);
    }

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });
      let data: any = null;
      if (response.status !== 204) {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          data = await response.json().catch(() => null);
        } else {
          const text = await response.text().catch(() => '');
          if (text) {
            try {
              data = JSON.parse(text);
            } catch {
              data = text;
            }
          }
        }
      }

      if (!response.ok) {
        if (response.status === 401 && this.token && retryCount === 0) {
          const refreshed = await this.refreshAccessToken();
          if (refreshed) {
            return this.request<T>(endpoint, options, retryCount + 1);
          }
        }
        const fieldErrors: string[] = [];
        if (data && typeof data === 'object' && !Array.isArray(data)) {
          for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
            if (Array.isArray(value)) {
              for (const item of value) {
                if (typeof item === 'string' && item.trim()) {
                  fieldErrors.push(`${key}: ${item}`);
                }
              }
              continue;
            }
            if (typeof value === 'string' && value.trim()) {
              fieldErrors.push(`${key}: ${value}`);
            }
          }
        }

        const statusMessage = response.status === 401
          ? 'No autorizado. Inicia sesión.'
          : response.status === 403
            ? 'Acceso denegado.'
            : response.status === 404
              ? 'Recurso no encontrado.'
              : `Error HTTP ${response.status}`;

        const message =
          (typeof data === 'string' && data.trim() ? data : undefined) ??
          (data && typeof data === 'object' && 'detail' in data ? (data as any).detail : undefined) ??
          (data && typeof data === 'object' && 'message' in data ? (data as any).message : undefined) ??
          (fieldErrors.length > 0 ? `Datos inválidos: ${fieldErrors[0]}` : undefined) ??
          statusMessage;

        const errors =
          (data && typeof data === 'object' && Array.isArray((data as any).errors) ? (data as any).errors : undefined) ??
          (data && typeof data === 'object' && typeof (data as any).detail === 'string' ? [(data as any).detail] : undefined) ??
          (fieldErrors.length > 0 ? fieldErrors : undefined) ??
          [];

        if (response.status === 401 && typeof message === 'string' && message.toLowerCase().includes('token not valid')) {
          this.clearAuthStorage();
          return {
            success: false,
            message: 'Sesión expirada. Inicia sesión nuevamente.',
            errors: [message],
          };
        }

        return {
          success: false,
          message,
          errors
        };
      }
      return {
        success: true,
        data: data
      };
    } catch (error) {
      return {
        success: false,
        message: 'Error de conexión con el servidor',
        errors: [error instanceof Error ? error.message : 'Error desconocido']
      };
    }
  }

  private unwrapListPayload(payload: any): any[] {
    if (Array.isArray(payload)) return payload;
    if (payload && typeof payload === 'object' && Array.isArray(payload.results)) return payload.results;
    return [];
  }

  private mapBackendEntity(entity: any): Entity {
    const type = (entity?.entity_type ?? entity?.type ?? 'other') as Entity['type'];
    const value = typeof entity?.value === 'string' ? entity.value : typeof entity?.name === 'string' ? entity.name : '';
    const name = typeof entity?.display_name === 'string' && entity.display_name
      ? entity.display_name
      : typeof entity?.name === 'string' && entity.name
        ? entity.name
        : value;

    const looksLikeUuid = (v: any) =>
      typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v);

    const investigationId = typeof entity?.investigation_id === 'string'
      ? entity.investigation_id
      : entity?.investigation_id != null
        ? String(entity.investigation_id)
        : looksLikeUuid(entity?.investigation)
          ? String(entity.investigation)
          : undefined;

    const investigationName = typeof entity?.investigation_name === 'string'
      ? entity.investigation_name
      : typeof entity?.investigation === 'string' && !looksLikeUuid(entity.investigation)
        ? entity.investigation
        : undefined;

    return {
      id: String(entity?.id ?? ''),
      name,
      type,
      description: typeof entity?.description === 'string' ? entity.description : '',
      properties: (entity?.properties && typeof entity.properties === 'object' ? entity.properties : {}) as Record<string, any>,
      value,
      investigation: investigationId ?? (typeof entity?.investigation === 'string' ? entity.investigation : undefined),
      investigationId,
      investigationName,
      created_at: typeof entity?.created_at === 'string' ? entity.created_at : undefined,
      updated_at: typeof entity?.updated_at === 'string' ? entity.updated_at : undefined,
      createdAt: typeof entity?.created_at === 'string' ? entity.created_at : undefined,
      updatedAt: typeof entity?.updated_at === 'string' ? entity.updated_at : undefined,
    };
  }

  private mapBackendInvestigation(investigation: any): Investigation {
    const status = (investigation?.status || 'active') as Investigation['status'];
    const safeStatus: Investigation['status'] = (['active', 'completed', 'paused', 'archived'] as const).includes(status as any)
      ? status
      : 'active';

    const rawPriority = (investigation?.priority || 'medium') as Investigation['priority'];
    const safePriority: Investigation['priority'] = (['low', 'medium', 'high', 'critical'] as const).includes(rawPriority as any)
      ? rawPriority
      : 'medium';

    const createdBy =
      typeof investigation?.created_by?.username === 'string' && investigation.created_by.username
        ? investigation.created_by.username
        : 'N/A';

    const entitiesRaw = Array.isArray(investigation?.entities) ? investigation.entities : [];
    const metadata = investigation?.metadata && typeof investigation.metadata === 'object' ? investigation.metadata : {};
    const metadataTags = Array.isArray((metadata as any).tags) ? (metadata as any).tags.filter((t: any) => typeof t === 'string') : [];

    return {
      id: String(investigation?.id ?? ''),
      title: typeof investigation?.name === 'string' ? investigation.name : String(investigation?.title ?? ''),
      description: typeof investigation?.description === 'string' ? investigation.description : '',
      status: safeStatus,
      priority: safePriority,
      entities: entitiesRaw.map((e: any) => this.mapBackendEntity(e)),
      createdBy,
      createdAt: typeof investigation?.created_at === 'string' ? investigation.created_at : new Date().toISOString(),
      updatedAt: typeof investigation?.updated_at === 'string' ? investigation.updated_at : new Date().toISOString(),
      target: typeof investigation?.target === 'string' ? investigation.target : (metadata as any)?.target,
      tags: metadataTags,
      case_number: investigation?.case_number ?? (metadata as any)?.case_number,
      jurisdiction: investigation?.jurisdiction ?? (metadata as any)?.jurisdiction,
      estimated_loss: investigation?.estimated_loss ?? (metadata as any)?.estimated_loss,
      victim_count: investigation?.victim_count ?? (metadata as any)?.victim_count,
      metadata,
    };
  }

  // Métodos de autenticación
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      const response = await fetch(this.resolveUrl('/api/auth/token/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.access) {
        // Guardar tokens en localStorage
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('auth_token', data.access);
        
        // Actualizar token de la instancia
        this.token = data.access;
        
        // Obtener información del usuario y guardarla
        try {
          const userResponse = await this.getCurrentUser();
          if (userResponse.success && userResponse.data) {
            localStorage.setItem('user', JSON.stringify(userResponse.data));
          }
        } catch (userError) {
          console.warn('No se pudo obtener información del usuario:', userError);
        }
        
        return { success: true, message: 'Login exitoso' };
      }
      
      return { success: false, message: data.detail || 'Error en el login' };
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, message: error instanceof Error ? error.message : 'Error de conexión' };
    }
  }

  async logout(): Promise<void> {
    this.clearAuthStorage();
  }

  async getCurrentUser(): Promise<ApiResponse<User>> {
    return this.request<User>('/api/auth/user/');
  }

  // Métodos para investigaciones
  async getInvestigations(): Promise<ApiResponse<Investigation[]>> {
    return this.request<Investigation[]>('/api/investigations/');
  }

  async getInvestigation(id: string): Promise<ApiResponse<Investigation>> {
    const response = await this.request<any>(`/api/investigations/${id}/`);
    if (!response.success || !response.data) return response as ApiResponse<Investigation>;
    return { success: true, data: this.mapBackendInvestigation(response.data) };
  }

  async autoRecon(target: string, investigationId?: string): Promise<ApiResponse<any>> {
    return this.request<any>('/api/investigations/auto-recon/', {
      method: 'POST',
      body: JSON.stringify({ target, investigation_id: investigationId })
    });
  }

  async getOsintCatalog(target?: string): Promise<ApiResponse<any>> {
    const query = target ? `?target=${encodeURIComponent(target)}` : '';
    return this.request<any>(`/api/investigations/osint-catalog/${query}`);
  }

  async executeDorks(investigationId: string, dorks: any[], targetDomain?: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/api/investigations/${investigationId}/execute-dorks/`, {
      method: 'POST',
      body: JSON.stringify({ dorks, target_domain: targetDomain })
    });
  }

  async createInvestigation(investigation: Partial<Investigation>): Promise<ApiResponse<Investigation>> {
    return this.request<Investigation>('/api/investigations/', {
      method: 'POST',
      body: JSON.stringify(investigation),
    });
  }

  async updateInvestigation(id: string, investigation: Partial<Investigation>): Promise<ApiResponse<Investigation>> {
    return this.request<Investigation>(`/api/investigations/${id}/`, {
      method: 'PUT',
      body: JSON.stringify(investigation),
    });
  }

  async deleteInvestigation(id: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/api/investigations/${id}/`, {
      method: 'DELETE',
    });
  }

  async getInvestigationStats(investigationId: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/api/investigations/${investigationId}/stats/`);
  }

  async getInvestigationGraph(investigationId: string, limit: number = 500): Promise<ApiResponse<any>> {
    return this.request<any>(`/api/investigations/${investigationId}/entities/graph/?limit=${limit}`);
  }

  async listTransformExecutions(
    investigationId: string,
    params?: Record<string, any>
  ): Promise<ApiResponse<TransformExecution[]>> {
    let url = `/api/investigations/${investigationId}/executions/`;
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          searchParams.append(key, value.toString());
        }
      });
      if (searchParams.toString()) {
        url += '?' + searchParams.toString();
      }
    }
    const response = await this.request<any>(url);
    if (!response.success) return response as ApiResponse<TransformExecution[]>;
    return { success: true, data: this.unwrapListPayload(response.data) as TransformExecution[] };
  }

  async getTransformExecution(
    investigationId: string,
    executionId: string
  ): Promise<ApiResponse<TransformExecution>> {
    return this.request<TransformExecution>(
      `/api/investigations/${investigationId}/executions/${executionId}/`
    );
  }

  async createTransformExecution(
    investigationId: string,
    payload: {
      transform_name: string;
      input_entity_id?: string;
      input?: { entity_type: string; value: string };
      parameters?: Record<string, any>;
    }
  ): Promise<ApiResponse<TransformExecution>> {
    return this.request<TransformExecution>(
      `/api/investigations/${investigationId}/executions/`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  }

  async controlTransformExecution(
    investigationId: string,
    executionId: string,
    action: 'cancel' | 'retry'
  ): Promise<ApiResponse<any>> {
    return this.request<any>(
      `/api/investigations/${investigationId}/executions/${executionId}/control/`,
      {
        method: 'POST',
        body: JSON.stringify({ action }),
      }
    );
  }

  async listTransforms(params?: Record<string, any>): Promise<ApiResponse<any[]>> {
    let url = '/api/transforms/';
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          searchParams.append(key, value.toString());
        }
      });
      if (searchParams.toString()) {
        url += '?' + searchParams.toString();
      }
    }
    const response = await this.request<any>(url);
    if (!response.success) return response as ApiResponse<any[]>;
    return { success: true, data: this.unwrapListPayload(response.data) };
  }

  async getGeoEvents(limit?: number): Promise<ApiResponse<any[]>> {
    let url = '/api/events/geo/';
    if (typeof limit === 'number' && Number.isFinite(limit)) {
      const searchParams = new URLSearchParams();
      searchParams.append('limit', Math.max(1, Math.floor(limit)).toString());
      url += `?${searchParams.toString()}`;
    }
    const response = await this.request<any>(url);
    if (!response.success) return response as ApiResponse<any[]>;
    const payload = response.data;
    return {
      success: true,
      data: Array.isArray(payload) ? payload : this.unwrapListPayload(payload),
    };
  }

  async getExecutionLogs(
    investigationId: string,
    executionId: string
  ): Promise<ApiResponse<any>> {
    return this.request<any>(
      `/api/investigations/${investigationId}/executions/${executionId}/logs/`
    );
  }

  // Métodos para entidades
  async getEntities(params?: Record<string, any>, investigationId?: string): Promise<ApiResponse<Entity[]>> {
    let url = investigationId ? `/api/investigations/${investigationId}/entities/` : '/api/entities/';
    if (params) {
      const searchParams = new URLSearchParams();
      const normalizedParams: Record<string, any> = { ...params };
      if (normalizedParams.type && !normalizedParams.entity_type) {
        normalizedParams.entity_type = normalizedParams.type;
        delete normalizedParams.type;
      }
      delete normalizedParams.investigation;
      Object.entries(normalizedParams).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          searchParams.append(key, value.toString());
        }
      });
      if (searchParams.toString()) {
        url += '?' + searchParams.toString();
      }
    }
    const response = await this.request<any>(url);
    if (!response.success) return response as ApiResponse<Entity[]>;
    const items = this.unwrapListPayload(response.data);
    return {
      success: true,
      data: items.map((item) => this.mapBackendEntity(item)),
    };
  }

  async getEntity(id: string, investigationId?: string): Promise<ApiResponse<Entity>> {
    if (investigationId) {
      const response = await this.request<any>(`/api/investigations/${investigationId}/entities/${id}/`);
      if (!response.success) return response as ApiResponse<Entity>;
      return { success: true, data: this.mapBackendEntity(response.data) };
    }
    const list = await this.getEntities();
    if (!list.success) return { success: false, message: list.message, errors: list.errors };
    if (!list.data) return { success: false, message: 'Recurso no encontrado.', errors: ['Entity list not available'] };
    const found = list.data.find((e) => e.id === id);
    if (!found) return { success: false, message: 'Recurso no encontrado.', errors: ['Entity not found'] };
    return { success: true, data: found };
  }

  async createEntity(entity: Partial<Entity>, investigationId?: string): Promise<ApiResponse<Entity>> {
    if (!investigationId) {
      return { success: false, message: 'Investigación requerida para crear la entidad', errors: ['Missing investigationId'] };
    }
    const payload = {
      entity_type: (entity as any).entity_type ?? entity.type,
      display_name: entity.name,
      value: entity.value,
      description: entity.description,
      properties: entity.properties,
    };
    const response = await this.request<any>(`/api/investigations/${investigationId}/entities/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (!response.success) return response as ApiResponse<Entity>;
    return { success: true, data: this.mapBackendEntity(response.data) };
  }

  async updateEntity(id: string, entity: Partial<Entity>, investigationId?: string): Promise<ApiResponse<Entity>> {
    if (!investigationId) {
      return { success: false, message: 'Investigación requerida para actualizar la entidad', errors: ['Missing investigationId'] };
    }
    const payload = {
      entity_type: (entity as any).entity_type ?? entity.type,
      display_name: entity.name,
      value: entity.value,
      description: entity.description,
      properties: entity.properties,
    };
    const response = await this.request<any>(`/api/investigations/${investigationId}/entities/${id}/`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    if (!response.success) return response as ApiResponse<Entity>;
    return { success: true, data: this.mapBackendEntity(response.data) };
  }

  async deleteEntity(id: string, investigationId?: string): Promise<ApiResponse<void>> {
    if (!investigationId) {
      return { success: false, message: 'Investigación requerida para eliminar la entidad', errors: ['Missing investigationId'] };
    }
    return this.request<void>(`/api/investigations/${investigationId}/entities/${id}/`, {
      method: 'DELETE',
    });
  }

  async getEntityTypes(): Promise<ApiResponse<string[]>> {
    return this.request<string[]>('/api/entities/types/');
  }

  async getEntityRelationships(entityId: string, investigationId?: string): Promise<ApiResponse<any>> {
    if (!investigationId) {
      return { success: false, message: 'Investigación requerida para relaciones', errors: ['Missing investigationId'] };
    }
    const response = await this.request<any>(`/api/investigations/${investigationId}/entities/${entityId}/relationships/`);
    if (!response.success || !response.data) return response;

    const payload = response.data;
    const outgoing = Array.isArray(payload?.outgoing_relationships) ? payload.outgoing_relationships : [];
    const incoming = Array.isArray(payload?.incoming_relationships) ? payload.incoming_relationships : [];

    const normalizeRelationship = (rel: any) => {
      const sourceEntityRaw = rel?.source_entity;
      const targetEntityRaw = rel?.target_entity;

      return {
        id: String(rel?.id ?? ''),
        source_entity_id: String(sourceEntityRaw?.id ?? rel?.source_entity_id ?? ''),
        target_entity_id: String(targetEntityRaw?.id ?? rel?.target_entity_id ?? ''),
        relationship_type: String(rel?.relationship_type ?? ''),
        properties: (rel?.properties && typeof rel.properties === 'object') ? rel.properties : undefined,
        created_at: typeof rel?.created_at === 'string' ? rel.created_at : '',
        source_entity: sourceEntityRaw ? this.mapBackendEntity(sourceEntityRaw) : undefined,
        target_entity: targetEntityRaw ? this.mapBackendEntity(targetEntityRaw) : undefined,
      };
    };

    return {
      success: true,
      data: [...outgoing, ...incoming].map(normalizeRelationship),
    };
  }

  async createEntityRelationship(
    sourceId: string,
    targetId: string,
    relationshipType: string,
    investigationId?: string
  ): Promise<ApiResponse<any>> {
    if (!investigationId) {
      return { success: false, message: 'Investigación requerida para crear relación', errors: ['Missing investigationId'] };
    }
    return this.request<any>(`/api/investigations/${investigationId}/relationships/`, {
      method: 'POST',
      body: JSON.stringify({
        source_entity_id: sourceId,
        target_entity_id: targetId,
        relationship_type: relationshipType,
      }),
    });
  }

  async deleteEntityRelationship(relationshipId: string, investigationId?: string): Promise<ApiResponse<void>> {
    if (!investigationId) {
      return { success: false, message: 'Investigación requerida para eliminar relación', errors: ['Missing investigationId'] };
    }
    return this.request<void>(`/api/investigations/${investigationId}/relationships/${relationshipId}/`, { method: 'DELETE' });
  }

  // Métodos para dashboard (usar estadísticas de usuario)
  async getUserStats(): Promise<ApiResponse<any>> {
    return this.request<any>('/api/user/stats/');
  }

  async getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
    const response = await this.getUserStats();
    if (!response.success || !response.data) {
      return response as ApiResponse<DashboardStats>;
    }

    const investigations = response.data?.investigations ?? {};
    const byStatus = investigations?.by_status ?? {};
    const executions = response.data?.executions ?? {};
    const entities = response.data?.entities ?? {};

    return {
      success: true,
      data: {
        totalInvestigations: Number(investigations?.total ?? 0),
        activeInvestigations: Number(byStatus?.active ?? 0),
        completedInvestigations: Number(byStatus?.completed ?? 0),
        totalEntities: Number(entities?.total ?? 0),
        recentActivity: Number(investigations?.recent ?? 0) + Number(executions?.recent ?? 0),
      },
    };
  }

  // Verificar si el usuario está autenticado
  isAuthenticated(): boolean {
    return this.token !== null;
  }

  // Obtener usuario del localStorage
  getStoredUser(): User | null {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  }
}

export const apiService = new ApiService();
export { ApiService };
export default apiService;
