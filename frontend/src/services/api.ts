// Servicio API para la plataforma OSINT

import type { ApiResponse, AuthResponse, LoginCredentials, User, Investigation, Entity, DashboardStats } from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? '';

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
      console.log(`🔐 Token presente para ${endpoint}:`, this.token.substring(0, 20) + '...');
    } else {
      console.log(`❌ No hay token para ${endpoint}`);
    }

    console.log(`🌐 Haciendo petición a: ${url}`);
    console.log(`📋 Headers:`, headers);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      console.log(`📡 Respuesta de ${endpoint}:`, response.status, response.statusText);
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

        console.log(`❌ Error en ${endpoint}:`, data);
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

      console.log(`✅ Éxito en ${endpoint}:`, data);
      return {
        success: true,
        data: data
      };
    } catch (error) {
      console.error(`💥 Error de conexión en ${endpoint}:`, error);
      return {
        success: false,
        message: 'Error de conexión con el servidor',
        errors: [error instanceof Error ? error.message : 'Error desconocido']
      };
    }
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
    return this.request<Investigation>(`/api/investigations/${id}/`);
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

  async getInvestigationStats(): Promise<ApiResponse<any>> {
    return this.request<any>('/api/investigations/stats/');
  }

  async getInvestigationGraph(investigationId: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/api/investigations/${investigationId}/entities/graph/`);
  }

  // Métodos para entidades
  async getEntities(params?: Record<string, any>): Promise<ApiResponse<Entity[]>> {
    let url = '/api/entities/';
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
    return this.request<Entity[]>(url);
  }

  async getEntity(id: string): Promise<ApiResponse<Entity>> {
    return this.request<Entity>(`/api/entities/${id}/`);
  }

  async createEntity(entity: Partial<Entity>): Promise<ApiResponse<Entity>> {
    return this.request<Entity>('/api/entities/', {
      method: 'POST',
      body: JSON.stringify(entity),
    });
  }

  async updateEntity(id: string, entity: Partial<Entity>): Promise<ApiResponse<Entity>> {
    return this.request<Entity>(`/api/entities/${id}/`, {
      method: 'PUT',
      body: JSON.stringify(entity),
    });
  }

  async deleteEntity(id: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/api/entities/${id}/`, {
      method: 'DELETE',
    });
  }

  async getEntityTypes(): Promise<ApiResponse<string[]>> {
    return this.request<string[]>('/api/entities/types/');
  }

  async getEntityRelationships(id: string): Promise<ApiResponse<any[]>> {
    return this.request<any[]>(`/api/entities/${id}/relationships/`);
  }

  async createEntityRelationship(sourceId: string, targetId: string, relationshipType: string): Promise<ApiResponse<any>> {
    return this.request<any>('/api/entities/relationships/', {
      method: 'POST',
      body: JSON.stringify({
        source_entity: sourceId,
        target_entity: targetId,
        relationship_type: relationshipType
      }),
    });
  }

  async deleteEntityRelationship(relationshipId: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/api/entities/relationships/${relationshipId}/`, {
      method: 'DELETE',
    });
  }

  // Métodos para dashboard (usar estadísticas de usuario)
  async getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
    return this.request<DashboardStats>('/api/auth/user/stats/');
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
