// Tipos básicos para la plataforma OSINT

export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'analyst' | 'viewer';
  isActive: boolean;
  createdAt: string;
  lastLogin?: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  user?: User;
  token?: string;
  refreshToken?: string;
}

export interface Entity {
  id: string;
  name: string;
  type: 'person' | 'organization' | 'location' | 'phone' | 'email' | 'ip' | 'domain' | 'url' | 'hash' | 'file' | 'cryptocurrency' | 'social_media' | 'geolocation' | 'other' | 'subdomain';
  description?: string;
  properties: Record<string, any>;
  value?: string; // Agregado para compatibilidad con componentes
  investigation?: string; // Agregado para compatibilidad con EntityForm
  createdAt?: string; // Hecho opcional
  updatedAt?: string; // Hecho opcional
  created_at?: string; // Alias para compatibilidad con API
  updated_at?: string; // Alias para compatibilidad con API
}

export interface Investigation {
  id: string;
  title: string;
  description: string;
  status: 'active' | 'completed' | 'archived';
  priority: 'low' | 'medium' | 'high' | 'critical';
  entities: Entity[];
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  case_number?: string;
  jurisdiction?: string;
  estimated_loss?: string;
  victim_count?: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  errors?: string[];
}

export interface DashboardStats {
  totalInvestigations: number;
  activeInvestigations: number;
  completedInvestigations: number;
  totalEntities: number;
  recentActivity: number;
}

// Interfaces para GraphView y componentes relacionados
export interface GraphNode {
  id: string;
  type: 'person' | 'company' | 'email' | 'phone' | 'address' | 'domain';
  data: any;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  data?: any; // Agregado para compatibilidad con Cytoscape
}

// Interface para validación de formularios
export interface ValidationErrors {
  [key: string]: string;
}

// Interface para props de EntityTypeSelector
export interface EntityTypeSelectorProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
  selectedType?: string;
  onTypeSelect?: (type: string) => void;
  error?: string;
}

// Interface para props de EntityCard
export interface EntityCardProps {
  entity: Entity;
  onClick?: (entity: Entity) => void;
  onEdit?: (entity: Entity) => void;
  onDelete?: (entity: Entity) => Promise<void>;
  compact?: boolean;
}

// Tipos para Cytoscape
export interface CytoscapeNode {
  data: {
    id: string;
    label: string;
    type: string;
    connections: number;
    community?: number;
  };
}

export interface CytoscapeEdge {
  data: {
    id: string;
    source: string;
    target: string;
    type: string;
    label: string;
    weight?: number;
  };
}
