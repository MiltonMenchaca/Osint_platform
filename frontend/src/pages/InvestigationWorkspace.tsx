import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Row,
  Col,
  Card,
  Nav,
  Tab,
  Button,
  Badge,
  ProgressBar,
  Alert,
  Modal,
  Form,
  InputGroup,
  Dropdown,
  Spinner,
  Offcanvas,
  ListGroup,
  Tooltip,
  OverlayTrigger
} from 'react-bootstrap';
import {
  Search,
  Play,
  Eye,
  Plus,
  Edit,
  Trash2,
  Filter,
  Download,
  AlertCircle,
  CheckCircle,
  Clock,
  X,
  ArrowLeft,
  Network,
  Home,
  BarChart3,
  Database,
  Activity,
  Shield,
  Zap,
  Target,
  Calendar,
  MapPin,
  RefreshCw,
  FileDown,
  Share2,
  ZoomIn,
  Wifi,
  Globe,
  FileText
} from 'lucide-react';
import Swal from 'sweetalert2';
import type { Investigation, Entity, TransformExecution, TransformExecutionStatus, User } from '../types';
import EntityForm from '../features/investigation/components/EntityForm';
import Header from '../shared/components/Header';
import apiService from '../services/api';

// Local type definitions
interface OSINTTool {
  id: string;
  transformUuid?: string;
  name: string;
  description: string;
  category: string;
  inputType: string;
  outputTypes: string[];
  requiresApiKey: boolean;
  apiKeyName?: string;
  parameters: ToolParameter[];
  defaultParameters: Record<string, any>;
}

interface ToolParameter {
  name: string;
  type: string;
  required: boolean;
  description: string;
  placeholder?: string;
  options?: string[];
}



// Estilos CSS para la timeline
const timelineStyles = `
  .timeline {
    position: relative;
    padding-left: 30px;
  }
  
  .timeline::before {
    content: '';
    position: absolute;
    left: 15px;
    top: 0;
    bottom: 0;
    width: 2px;
    background: var(--osint-border);
  }
  
  .timeline-item {
    position: relative;
    margin-bottom: 20px;
  }
  
  .timeline-marker {
    position: absolute;
    left: -23px;
    top: 8px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid var(--osint-bg);
    box-shadow: 0 0 5px currentColor;
  }
  
  .timeline-marker.system { background: var(--osint-muted); border-color: var(--osint-muted); color: var(--osint-muted); }
  .timeline-marker.osint { background: var(--osint-green); border-color: var(--osint-green); color: var(--osint-green); }
  .timeline-marker.alert { background: var(--osint-amber); border-color: var(--osint-amber); color: var(--osint-amber); }
  .timeline-marker.critical { background: var(--osint-red); border-color: var(--osint-red); color: var(--osint-red); }
  .timeline-marker.manual { background: #6f42c1; border-color: #6f42c1; color: #6f42c1; }
  
  .timeline-content {
    background: var(--osint-glass);
    border: 1px solid var(--osint-border);
    border-radius: 4px;
    padding: 12px;
    margin-left: 10px;
    backdrop-filter: blur(5px);
  }
`;

const placeholderForInputType = (inputType: string): string => {
  switch (inputType) {
    case 'email': return 'ejemplo@dominio.com';
    case 'ip': return '8.8.8.8';
    case 'url': return 'https://ejemplo.com';
    case 'domain': return 'ejemplo.com';
    case 'phone': return '+34123456789';
    default: return 'Objetivo';
  }
};

const inferParameterType = (value: any): string => {
  if (typeof value === 'boolean') return 'boolean';
  if (typeof value === 'number') return 'number';
  return 'string';
};

const mapTransformToTool = (t: any): OSINTTool => {
  const inputType = typeof t?.input_type === 'string' ? t.input_type : 'any';
  const defaultParameters: Record<string, any> =
    t?.parameters && typeof t.parameters === 'object' && !Array.isArray(t.parameters)
      ? t.parameters
      : {};

  const outputTypes: string[] = Array.isArray(t?.output_types) ? t.output_types.map((v: any) => String(v)) : [];
  const optionalParameters: ToolParameter[] = Object.entries(defaultParameters)
    .filter(([key]) => key !== 'target' && key !== 'input' && key !== 'entity_type')
    .map(([key, value]) => ({
      name: String(key),
      type: inferParameterType(value),
      required: false,
      description: String(key),
      placeholder: typeof value === 'number' || typeof value === 'string' ? String(value) : undefined,
    }));

  return {
    id: String(t?.name ?? ''),
    transformUuid: t?.id != null ? String(t.id) : undefined,
    name: String(t?.display_name ?? t?.name ?? ''),
    description: String(t?.description ?? ''),
    category: String(t?.category ?? 'other'),
    inputType,
    outputTypes,
    requiresApiKey: Boolean(t?.requires_api_key),
    apiKeyName: typeof t?.api_key_name === 'string' && t.api_key_name ? t.api_key_name : undefined,
    parameters: [
      { name: 'target', type: 'string', required: true, description: `Objetivo (${inputType})`, placeholder: placeholderForInputType(inputType) },
      ...optionalParameters,
    ],
    defaultParameters,
  };
};

type ExecutionStatus = TransformExecutionStatus;

interface ToolExecutionState {
  id: string;
  toolId: string;
  status: ExecutionStatus;
  progress: number;
  startTime?: Date;
  endTime?: Date;
  results?: any[];
  error?: string;
  toolParameters?: Record<string, any>;
}

const InvestigationWorkspace: React.FC = () => {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  
  // Estados principales
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [isLoadingInvestigation, setIsLoadingInvestigation] = useState(false);
  const [osintTools, setOsintTools] = useState<OSINTTool[]>([]);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [toolsError, setToolsError] = useState<string | null>(null);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const [lastRefreshAt, setLastRefreshAt] = useState<Date | null>(null);
  
  const [selectedTool, setSelectedTool] = useState<OSINTTool | null>(null);
  const [toolParameters, setToolParameters] = useState<Record<string, any>>({});
  const [executions, setExecutions] = useState<ToolExecutionState[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [entityFilter, setEntityFilter] = useState('');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [entitySourceFilter, setEntitySourceFilter] = useState('');
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [showEntityForm, setShowEntityForm] = useState(false);
  const [showExecutionDetails, setShowExecutionDetails] = useState<string | null>(null);
  const [executionDetailsLoading, setExecutionDetailsLoading] = useState(false);
  const [executionDetailsError, setExecutionDetailsError] = useState<string | null>(null);
  const [executionDetails, setExecutionDetails] = useState<any | null>(null);
  const [activePanel, setActivePanel] = useState<'overview' | 'analysis' | 'timeline' | 'geography' | 'network'>('overview');
  const [showOSINTPanel, setShowOSINTPanel] = useState(false);
  const [investigationStats, setInvestigationStats] = useState<any | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [executionActionLoading, setExecutionActionLoading] = useState<Record<string, boolean>>({});
  const [autoReconLoading, setAutoReconLoading] = useState(false);
  const [showAutoReconModal, setShowAutoReconModal] = useState(false);
  const [autoReconTarget, setAutoReconTarget] = useState('');
  const [autoReconResult, setAutoReconResult] = useState<any | null>(null);
  const [autoReconError, setAutoReconError] = useState<string | null>(null);
  const [autoReconExpanded, setAutoReconExpanded] = useState<Record<string, boolean>>({});
  const [showDockerCatalogModal, setShowDockerCatalogModal] = useState(false);
  const [dockerTarget, setDockerTarget] = useState('');
  const [dockerCatalog, setDockerCatalog] = useState<any | null>(null);
  const [dockerCatalogLoading, setDockerCatalogLoading] = useState(false);
  const [dockerCatalogError, setDockerCatalogError] = useState<string | null>(null);
  const [selectedDorks, setSelectedDorks] = useState<string[]>([]);
  const [executingDorks, setExecutingDorks] = useState(false);

  const loadInvestigation = useCallback(async (isAutoRefresh = false) => {
    if (!id) return;
    if (!isAutoRefresh) setIsLoadingInvestigation(true);
    setPageError(null);
    try {
      const invRes = await apiService.getInvestigation(id);
      if (!invRes.success || !invRes.data) {
        if (!isAutoRefresh) {
          setInvestigation(null);
          setEntities([]);
          setPageError(invRes.message || 'No se pudo cargar la investigación');
        }
        return;
      }

      setInvestigation(invRes.data);
      setEntities(Array.isArray(invRes.data.entities) ? invRes.data.entities : []);
      const metadataAutoRecon = invRes.data.metadata?.auto_recon ?? null;
      if (metadataAutoRecon) {
        setAutoReconResult(metadataAutoRecon);
      }
    } finally {
      if (!isAutoRefresh) setIsLoadingInvestigation(false);
    }
  }, [id]);

  const resolveDefaultTarget = () => {
    let target = investigation?.target || investigation?.metadata?.target || '';
    if (!target) {
      const targetEntity = entities.find(e => e.type === 'domain' || e.type === 'url' || e.type === 'ip');
      if (targetEntity) {
        target = targetEntity.value || '';
      }
    }
    return target;
  };

  const handleFullAutoRecon = () => {
    const target = resolveDefaultTarget();
    setAutoReconTarget(target);
    setShowAutoReconModal(true);
  };

  const loadDockerCatalog = async (target?: string) => {
    setDockerCatalogLoading(true);
    setDockerCatalogError(null);
    try {
      const res = await apiService.getOsintCatalog(target);
      if (!res.success) {
        setDockerCatalogError(res.message || 'No se pudo cargar el catálogo.');
        setDockerCatalog(null);
        return;
      }
      setDockerCatalog(res.data);
    } finally {
      setDockerCatalogLoading(false);
    }
  };

  const handleExecuteDorks = async () => {
    if (!id || selectedDorks.length === 0) return;
    setExecutingDorks(true);
    try {
      const res = await apiService.executeDorks(id, selectedDorks, dockerTarget);
      if (res.success) {
        Swal.fire({
          title: 'Búsquedas Iniciadas',
          text: `Se han encolado ${res.data?.execution_ids?.length || 0} búsquedas.`,
          icon: 'success',
          timer: 2000,
          showConfirmButton: false
        });
        setShowDockerCatalogModal(false);
        setSelectedDorks([]);
        void refreshAll();
      } else {
        Swal.fire('Error', res.message || 'Error al ejecutar dorks', 'error');
      }
    } catch (e) {
      console.error(e);
      Swal.fire('Error', 'Error de conexión', 'error');
    } finally {
      setExecutingDorks(false);
    }
  };

  const toggleDork = (query: string) => {
    setSelectedDorks(prev => 
      prev.includes(query) ? prev.filter(q => q !== query) : [...prev, query]
    );
  };

  const handleOpenDockerTools = () => {
    const target = resolveDefaultTarget();
    setDockerTarget(target);
    setShowDockerCatalogModal(true);
    void loadDockerCatalog(target);
  };

  const executeAutoRecon = async () => {
    if (!autoReconTarget) {
      Swal.fire({
        title: 'Atención',
        text: 'Por favor ingrese un objetivo.',
        icon: 'warning',
        confirmButtonText: 'Entendido'
      });
      return;
    }

    setShowAutoReconModal(false);
    setAutoReconLoading(true);
    setAutoReconError(null);
    try {
      const res = await apiService.autoRecon(autoReconTarget, id);
      if (!res.success) {
        setAutoReconResult(null);
        setAutoReconError(res.message || 'Ocurrió un error al ejecutar el escaneo automático.');
        Swal.fire({
          title: 'Error',
          text: res.message || 'Ocurrió un error al ejecutar el escaneo automático.',
          icon: 'error',
          confirmButtonText: 'Cerrar'
        });
      } else {
        setAutoReconResult(res.data ?? null);
        Swal.fire({
          title: '¡Escaneo completado!',
          text: 'Los resultados se han registrado con éxito.',
          icon: 'success',
          confirmButtonText: 'Genial'
        });
        // Refresh investigation data
        void refreshAll();
      }
    } catch (e) {
      console.error(e);
      setAutoReconResult(null);
      setAutoReconError('Ocurrió un error al ejecutar el escaneo automático.');
      Swal.fire({
        title: 'Error Crítico',
        text: 'Ocurrió un error al ejecutar el escaneo automático.',
        icon: 'error',
        confirmButtonText: 'Cerrar'
      });
    } finally {
      setAutoReconLoading(false);
    }
  };

  // Verificar redirección automática
  useEffect(() => {
    if (!id) {
      navigate('/investigations');
      return;
    }
  }, [id, navigate]);

  useEffect(() => {
    let cancelled = false;

    const stored = apiService.getStoredUser();
    if (stored && !cancelled) setCurrentUser(stored);

    const load = async () => {
      const res = await apiService.getCurrentUser();
      if (!cancelled && res.success && res.data) {
        setCurrentUser(res.data);
        localStorage.setItem('user', JSON.stringify(res.data));
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    void loadInvestigation();
  }, [loadInvestigation]);

  useEffect(() => {
    let cancelled = false;
    const loadTools = async () => {
      setToolsLoading(true);
      setToolsError(null);
      try {
        const res = await apiService.listTransforms({ enabled: true, page_size: 200 });
        if (!res.success || !res.data) {
          if (!cancelled) setToolsError(res.message || 'No se pudieron cargar las herramientas');
          return;
        }
        const tools = res.data
          .filter((t: any) => t && typeof t === 'object' && typeof t.name === 'string' && t.name)
          .map(mapTransformToTool);
        if (!cancelled) setOsintTools(tools);
      } finally {
        if (!cancelled) setToolsLoading(false);
      }
    };
    void loadTools();
    return () => {
      cancelled = true;
    };
  }, []);

  const mapBackendExecutionToState = useCallback((execution: TransformExecution): ToolExecutionState => {
    const isDone = execution.status === 'completed' || execution.status === 'failed' || execution.status === 'cancelled';
    const progress =
      execution.status === 'running' ? 50 : isDone ? 100 : 0;

    const toolId = execution.transform_name;
    const entitiesCreated = typeof execution.results?.entities_created === 'number' ? execution.results.entities_created : undefined;

    return {
      id: execution.id,
      toolId,
      status: execution.status,
      progress,
      startTime: execution.started_at ? new Date(execution.started_at) : undefined,
      endTime: execution.completed_at ? new Date(execution.completed_at) : undefined,
      results: execution.results
        ? [
            { type: 'data', count: entitiesCreated ?? 0 },
            { type: 'raw', data: execution.results },
          ]
        : undefined,
      error: execution.error_message ?? undefined,
    };
  }, []);

  const refreshExecutions = useCallback(async () => {
    if (!id) return;
    const response = await apiService.listTransformExecutions(id);
    if (response.success && response.data) {
      setExecutions(response.data.map(mapBackendExecutionToState));
    }
  }, [id, mapBackendExecutionToState]);

  const refreshEntities = useCallback(async () => {
    if (!id) return;
    const entRes = await apiService.getEntities(undefined, id);
    if (entRes.success && entRes.data) {
      setEntities(entRes.data);
    }
  }, [id]);

  const refreshStats = useCallback(
    async (showLoading = false) => {
      if (!id) return;
      if (showLoading) setStatsLoading(true);
      setStatsError(null);
      try {
        const res = await apiService.getInvestigationStats(id);
        if (!res.success || !res.data) {
          setInvestigationStats(null);
          setStatsError(res.message || 'No se pudieron cargar las estadísticas');
          return;
        }
        setInvestigationStats(res.data);
      } finally {
        if (showLoading) setStatsLoading(false);
      }
    },
    [id]
  );

  const refreshAll = useCallback(async () => {
    if (!id) return;
    await Promise.all([refreshExecutions(), refreshEntities(), refreshStats(false)]);
    setLastRefreshAt(new Date());
  }, [id, refreshExecutions, refreshEntities, refreshStats]);

  useEffect(() => {
    if (!id) return;
    void refreshAll();
    if (!autoRefreshEnabled) return;
    const interval = window.setInterval(() => {
      void refreshAll();
    }, 4000);
    return () => {
      window.clearInterval(interval);
    };
  }, [id, refreshAll, autoRefreshEnabled]);

  useEffect(() => {
    if (!id) return;
    void refreshStats(true);
  }, [id, refreshStats]);

  useEffect(() => {
    if (!showExecutionDetails || !id) return;
    let cancelled = false;
    const load = async () => {
      setExecutionDetailsLoading(true);
      setExecutionDetailsError(null);
      setExecutionDetails(null);
      try {
        const res = await apiService.getExecutionLogs(id, showExecutionDetails);
        if (!res.success) {
          if (!cancelled) setExecutionDetailsError(res.message || 'No se pudieron cargar los detalles');
          return;
        }
        if (!cancelled) setExecutionDetails(res.data ?? null);
      } finally {
        if (!cancelled) setExecutionDetailsLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [showExecutionDetails, id]);

  // Función para validar formulario
  const isFormValid = () => {
    if (!selectedTool) return false;
    
    const requiredParams = selectedTool.parameters.filter((p: any) => p.required);
    return requiredParams.every((param: any) => {
      const value = toolParameters[param.name];
      return value !== undefined && value !== null && value !== '';
    });
  };

  const executeOSINTTool = async (tool?: OSINTTool) => {
    const targetTool = tool || selectedTool;
    
    if (!targetTool) {
      Swal.fire({
        title: 'Herramienta no seleccionada',
        text: 'Por favor selecciona una herramienta OSINT para continuar.',
        icon: 'warning',
        confirmButtonText: 'Entendido'
      });
      return;
    }

    if (!isFormValid()) {
      Swal.fire({
        title: 'Formulario incompleto',
        text: 'Por favor completa todos los campos requeridos correctamente.',
        icon: 'warning',
        confirmButtonText: 'Entendido'
      });
      return;
    }

    if (!id) {
      Swal.fire('Error', 'Investigación inválida', 'error');
      return;
    }

    const transformName = targetTool.id;
    if (!transformName) {
      Swal.fire('Error', 'Herramienta inválida', 'error');
      return;
    }

    const requiredParams = targetTool.parameters.filter((p: any) => p.required);
    const primaryParamName = requiredParams[0]?.name;
    const primaryValue = primaryParamName ? toolParameters[primaryParamName] : undefined;

    const rawValue =
      toolParameters.email ??
      toolParameters.domain ??
      toolParameters.username ??
      toolParameters.target ??
      toolParameters.entity_value ??
      primaryValue;

    if (rawValue === undefined || rawValue === null || String(rawValue).trim() === '') {
      Swal.fire({
        title: 'Input no válido',
        text: 'No se pudo determinar el input para la ejecución.',
        icon: 'error',
        confirmButtonText: 'Revisar'
      });
      return;
    }

    const value = String(rawValue).trim();
    const looksLikeIp = /^(\d{1,3}\.){3}\d{1,3}$/.test(value);
    const looksLikeUrl = /^https?:\/\//.test(value);
    const entityType =
      toolParameters.entity_type ? String(toolParameters.entity_type) :
      targetTool.inputType && targetTool.inputType !== 'any' ? targetTool.inputType :
      looksLikeUrl ? 'url' :
      looksLikeIp ? 'ip' :
      'domain';

    setIsExecuting(true);
    try {
      const parameters: Record<string, any> = { ...toolParameters };
      delete parameters.target;
      delete parameters.entity_type;
      delete parameters.email;
      delete parameters.domain;
      delete parameters.username;
      delete parameters.entity_value;

      const response = await apiService.createTransformExecution(id, {
        transform_name: transformName,
        input: { entity_type: entityType, value },
        parameters,
      });

      if (!response.success || !response.data) {
        Swal.fire({
          title: 'Error de Ejecución',
          text: response.message || 'Error al ejecutar transform',
          icon: 'error',
          confirmButtonText: 'Cerrar'
        });
        return;
      }

      setToolParameters({});
      setSelectedTool(null);
      
      Swal.fire({
        title: 'Ejecución Iniciada',
        text: 'La herramienta se está ejecutando en segundo plano.',
        icon: 'success',
        timer: 2000,
        showConfirmButton: false
      });
      
      setExecutions(prev => [mapBackendExecutionToState(response.data as TransformExecution), ...prev]);
      void refreshAll();
    } finally {
      setIsExecuting(false);
    }
  };

  const handleExecutionAction = async (executionId: string, action: 'cancel' | 'retry') => {
    if (!id) return;
    const key = `${executionId}_${action}`;
    setExecutionActionLoading((prev) => ({ ...prev, [key]: true }));
    try {
      const res = await apiService.controlTransformExecution(id, executionId, action);
      if (!res.success) {
        Swal.fire('Error', res.message || 'No se pudo actualizar la ejecución', 'error');
        return;
      }
      
      Swal.fire({
        title: action === 'retry' ? 'Reintentando...' : 'Cancelado',
        text: `La ejecución ha sido ${action === 'retry' ? 'reiniciada' : 'cancelada'}.`,
        icon: 'success',
        timer: 1500,
        showConfirmButton: false
      });

      if (showExecutionDetails === executionId) {
        const details = await apiService.getExecutionLogs(id, executionId);
        if (details.success) setExecutionDetails(details.data ?? null);
      }
      await refreshAll();
    } finally {
      setExecutionActionLoading((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
  };

  const handleDeleteEntity = async (entityId: string) => {
    const result = await Swal.fire({
      title: '¿Estás seguro?',
      text: "Esta acción no se puede deshacer.",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (!result.isConfirmed) return;

    try {
      if (!id) {
        Swal.fire('Error', 'Investigación inválida', 'error');
        return;
      }
      const res = await apiService.deleteEntity(entityId, id);
      if (!res.success) {
        Swal.fire('Error', res.message || 'Error al eliminar la entidad', 'error');
        return;
      }
      setEntities(prev => prev.filter(e => e.id !== entityId));
      Swal.fire(
        '¡Eliminado!',
        'La entidad ha sido eliminada.',
        'success'
      );
    } catch {
      Swal.fire('Error', 'Error al eliminar la entidad', 'error');
    }
  };

  const handleEditEntity = (entity: Entity) => {
    setSelectedEntity(entity);
    setShowEntityForm(true);
  };

  const handleAddEntity = () => {
    setSelectedEntity(null);
    setShowEntityForm(true);
  };

  const filteredEntities = entities.filter(entity => {
    const q = entityFilter.toLowerCase();
    const matchesSearch =
      (entity.value && entity.value.toLowerCase().includes(q)) ||
      (entity.name && entity.name.toLowerCase().includes(q)) ||
      (entity.description && entity.description.toLowerCase().includes(q));
    const matchesType = !entityTypeFilter || entity.type === entityTypeFilter;
    const matchesSource = !entitySourceFilter || entity.properties?.source === entitySourceFilter;
    
    return matchesSearch && matchesType && matchesSource;
  });

  const metrics = useMemo(() => {
    const failed = executions.filter((e) => e.status === 'failed').length;
    const threatLevel = Math.min(10, Math.max(0, 2 + failed * 1.5 + Math.log1p(entities.length) / 2));
    const riskScore = Math.round(Math.min(100, threatLevel * 10));
    const suspiciousActivities = failed;
    const severityLabel = threatLevel >= 8 ? 'CRÍTICO' : threatLevel >= 5 ? 'ALTO' : threatLevel >= 3 ? 'MEDIO' : 'BAJO';
    return {
      threatLevel: Number(threatLevel.toFixed(1)),
      riskScore,
      suspiciousActivities,
      severityLabel,
    };
  }, [entities.length, executions]);

  const formatEntityType = (type: string) => {
    const map: Record<string, string> = {
      ip: 'IPs',
      domain: 'Dominios',
      email: 'Emails',
      url: 'URLs',
      port: 'Puertos',
      service: 'Servicios',
      hash: 'Hashes',
      person: 'Personas',
      organization: 'Organizaciones',
      phone: 'Teléfonos',
      geolocation: 'Geolocalizaciones',
      social_media: 'Redes Sociales',
      cryptocurrency: 'Cripto',
      file: 'Archivos',
      other: 'Otros',
    };
    return map[type] || type;
  };

  const formatRelationshipType = (type: string) => {
    const map: Record<string, string> = {
      owns: 'Propiedad',
      related_to: 'Relacionado',
      resolves_to: 'Resuelve a',
      communicates_with: 'Comunica con',
      linked_to: 'Vinculado a',
    };
    return map[type] || type.replace(/_/g, ' ');
  };

  const normalizeText = (value: any) => String(value ?? '').replace(/\s+/g, ' ').trim();

  const summarizeWhois = (raw: string): string[] => {
    if (!raw) return [];
    const fields = ['inetnum', 'netname', 'country', 'org-name', 'abuse-mailbox', 'origin', 'route'];
    const lines = raw.split('\n');
    const matches: string[] = [];
    for (const line of lines) {
      const clean = line.trim();
      const match = clean.match(/^([a-z-]+):\s*(.+)$/i);
      if (match && fields.includes(match[1])) {
        matches.push(`${match[1]}: ${match[2]}`);
      }
      if (matches.length >= 6) break;
    }
    return matches;
  };

  const summarizeNmap = (results: any[]): string[] => {
    const services = results
      .filter((item) => item?.type === 'service')
      .map((item) => {
        const props = item?.properties || {};
        const name = normalizeText(props.service_name || item?.value || 'service');
        const port = normalizeText(props.port);
        const product = normalizeText(props.product);
        const version = normalizeText(props.version);
        const parts = [name, port && `:${port}`, product, version].filter(Boolean);
        return parts.join(' ');
      });
    const ports = results
      .filter((item) => item?.type === 'port')
      .map((item) => {
        const props = item?.properties || {};
        const port = normalizeText(props.port || item?.value);
        const state = normalizeText(props.state);
        const product = normalizeText(props.service_product || props.product);
        const version = normalizeText(props.service_version || props.version);
        const parts = [port && `port ${port}`, state && `(${state})`, product, version].filter(Boolean);
        return parts.join(' ');
      });
    return [...services, ...ports].filter(Boolean).slice(0, 6);
  };

  const summarizeGenericResults = (results: any[]): string[] => {
    return results
      .map((item) => {
        const type = normalizeText(item?.type);
        const value = normalizeText(item?.value);
        const props = item?.properties || {};
        const extra = normalizeText(props?.service_name || props?.product || props?.version);
        const label = [type, value].filter(Boolean).join(': ');
        const full = [label, extra].filter(Boolean).join(' ');
        return full || value || type;
      })
      .filter(Boolean)
      .slice(0, 6);
  };

  const buildAutoReconSummary = (toolName: string, toolData: any): string[] => {
    const results = Array.isArray(toolData?.results) ? toolData.results : [];
    if (toolName === 'whois') {
      const raw = normalizeText(toolData?.results?.[0]?.properties?.raw || '');
      return summarizeWhois(raw);
    }
    if (toolName === 'nmap') {
      return summarizeNmap(results);
    }
    if (toolName === 'ping') {
      return results.map((item: any) => normalizeText(item?.value)).filter(Boolean).slice(0, 3);
    }
    return summarizeGenericResults(results);
  };

  const entityTypeStats = useMemo(() => {
    const byType = investigationStats?.entities?.by_type ?? {};
    const total = typeof investigationStats?.entities?.total === 'number' ? investigationStats.entities.total : 0;
    return Object.entries(byType)
      .map(([type, count]) => ({
        type,
        count: Number(count),
        percent: total > 0 ? Math.round((Number(count) / total) * 100) : 0,
      }))
      .filter((item) => item.count > 0)
      .sort((a, b) => b.count - a.count);
  }, [investigationStats]);

  const iocStats = useMemo(() => {
    const byType = investigationStats?.entities?.by_type ?? {};
    const types = ['ip', 'domain', 'url', 'hash', 'email'];
    return types
      .map((type) => ({ type, count: Number(byType[type] ?? 0) }))
      .filter((item) => item.count > 0);
  }, [investigationStats]);

  const relationshipTypeStats = useMemo(() => {
    const byType = investigationStats?.relationships?.by_type ?? {};
    return Object.entries(byType)
      .map(([type, count]) => ({ type, count: Number(count) }))
      .filter((item) => item.count > 0)
      .sort((a, b) => b.count - a.count);
  }, [investigationStats]);

  const executionStatusStats = useMemo(() => {
    const byStatus = investigationStats?.executions?.by_status ?? {};
    return Object.entries(byStatus)
      .map(([status, count]) => ({ status, count: Number(count) }))
      .filter((item) => item.count > 0)
      .sort((a, b) => b.count - a.count);
  }, [investigationStats]);

  const networkSummary = useMemo(() => {
    const totalNodes = typeof investigationStats?.entities?.total === 'number' ? investigationStats.entities.total : entities.length;
    const totalEdges = typeof investigationStats?.relationships?.total === 'number' ? investigationStats.relationships.total : 0;
    const density =
      totalNodes > 1 ? Math.round((2 * totalEdges * 100) / (totalNodes * (totalNodes - 1))) / 100 : 0;
    return {
      totalNodes,
      totalEdges,
      density,
    };
  }, [investigationStats, entities.length]);

  const geographySummary = useMemo(() => {
    const byType = investigationStats?.entities?.by_type ?? {};
    return {
      geolocations: Number(byType.geolocation ?? 0),
      ips: Number(byType.ip ?? 0),
      domains: Number(byType.domain ?? 0),
    };
  }, [investigationStats]);

  type TimelineItem = {
    title: string;
    description: string;
    badge: string;
    color: 'success' | 'primary' | 'warning' | 'danger' | 'secondary';
    timestamp: Date;
  };

  const timelineItems = useMemo<TimelineItem[]>(() => {
    const items: TimelineItem[] = [];
    if (investigation?.createdAt) {
      items.push({
        title: 'Investigación Iniciada',
        description: investigation.description || 'Investigación creada',
        badge: 'Sistema',
        color: 'success',
        timestamp: new Date(investigation.createdAt),
      });
    }
    for (const e of executions) {
      const status = e.status;
      const completed = e.endTime || undefined;
      const started = e.startTime || undefined;
      const when = completed ? completed : started ? started : new Date();
      const color = status === 'completed' ? 'primary' : status === 'failed' ? 'danger' : status === 'running' ? 'warning' : 'secondary';
      items.push({
        title: status === 'completed' ? `Transform ${e.toolId || e.id} completado` : status === 'failed' ? `Transform ${e.toolId || e.id} falló` : `Transform ${e.toolId || e.id} ${status}`,
        description: e.error ? e.error : `Ejecución ${status}`,
        badge: 'OSINT',
        color,
        timestamp: when,
      });
    }
    for (const ent of entities) {
      const when = ent.created_at ? new Date(ent.created_at) : ent.createdAt ? new Date(ent.createdAt) : undefined;
      if (!when) continue;
      items.push({
        title: 'Entidad Agregada',
        description: `${ent.type.toUpperCase()}: ${ent.value}`,
        badge: 'Sistema',
        color: 'secondary',
        timestamp: when,
      });
    }
    items.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
    return items.slice(0, 25);
  }, [investigation, executions, entities]);

  const getStatusVariant = (status: ExecutionStatus) => {
    switch (status) {
      case 'completed': return 'success';
      case 'running': return 'primary';
      case 'failed': return 'danger';
      case 'cancelled': return 'warning';
      default: return 'secondary';
    }
  };

  const getStatusIcon = (status: ExecutionStatus) => {
    switch (status) {
      case 'completed': return <CheckCircle size={16} />;
      case 'running': return <Spinner animation="border" size="sm" />;
      case 'failed': return <AlertCircle size={16} />;
      case 'cancelled': return <X size={16} />;
      default: return <Clock size={16} />;
    }
  };

  const handleLogout = () => {
    void apiService.logout();
    navigate('/login');
  };

  return (
    <div className="app-shell">
      {currentUser && <Header user={currentUser} onLogout={handleLogout} />}

      <div className="app-page">
        {pageError && (
          <Container fluid className="py-2">
            <Alert variant="danger" className="mb-0">
              {pageError}
            </Alert>
          </Container>
        )}
      
      {/* Header de la investigación */}
      <Container fluid className="py-3 border-bottom">
        <Row className="align-items-center">
          <Col>
            <div className="d-flex align-items-center gap-3">
              <Button 
                variant="outline-light" 
                size="sm" 
                onClick={() => navigate('/investigations')}
                className="d-flex align-items-center gap-2"
              >
                <ArrowLeft size={16} />
                Volver a Investigaciones
              </Button>
              
              <div>
                <h2 className="h4 mb-1">
                  {investigation?.title ?? 'Investigación'}
                  {isLoadingInvestigation && <Spinner animation="border" size="sm" className="ms-2" />}
                </h2>
                <div className="d-flex align-items-center gap-3 text-muted small">
                  <span>
                    {(investigation?.case_number || investigation?.jurisdiction)
                      ? `${investigation?.case_number ?? ''}${investigation?.case_number && investigation?.jurisdiction ? ' • ' : ''}${investigation?.jurisdiction ?? ''}`
                      : (investigation?.createdBy ? `Creada por ${investigation.createdBy}` : '')}
                  </span>
                  <Badge bg={['high', 'critical'].includes(investigation?.priority ?? 'medium') ? 'danger' : (investigation?.priority ?? 'medium') === 'medium' ? 'warning' : 'success'}>
                    {['high', 'critical'].includes(investigation?.priority ?? 'medium') ? 'CRÍTICA' : (investigation?.priority ?? 'medium') === 'medium' ? 'ACTIVA' : 'BAJA'}
                  </Badge>
                  <Button
                    variant="outline-primary"
                    size="sm"
                    className="d-flex align-items-center gap-1"
                    onClick={() => id && navigate(`/graphs?investigationId=${encodeURIComponent(id)}`)}
                    disabled={!id}
                  >
                    <Eye size={14} />
                    Ver en Grafo
                  </Button>
                </div>
              </div>
            </div>
          </Col>
          
          <Col xs="auto">
            <div className="text-end">
              <div className="h5 mb-0 text-danger">{investigation?.estimated_loss ?? '-'}</div>
              <div className="small text-muted">{investigation?.victim_count ?? 0} víctimas</div>
            </div>
          </Col>
        </Row>
      </Container>

      {/* Panel de métricas en tiempo real */}
      <Container fluid className="py-3">
          <Row className="g-4 justify-content-center">
            <Col md={3}>
              <Card className="h-100">
                <Card.Body className="text-center py-4">
                  <div className="d-flex align-items-center justify-content-center mb-3">
                    <Shield className="me-2" size={24} style={{color: '#dc3545'}} />
                    <span className="small" style={{color: '#6c757d'}}>{metrics.severityLabel}</span>
                  </div>
                  <div className="h3 mb-1" style={{color: '#dc3545'}}>{metrics.threatLevel}/10</div>
                  <div className="small text-muted">Nivel de Amenaza</div>
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={3}>
              <Card className="h-100">
                <Card.Body className="text-center py-4">
                  <div className="d-flex align-items-center justify-content-center mb-3">
                    <Target className="me-2" size={24} style={{color: '#fd7e14'}} />
                    <span className="small" style={{color: '#6c757d'}}>ALTO</span>
                  </div>
                  <div className="h3 mb-1" style={{color: '#fd7e14'}}>{metrics.riskScore}%</div>
                  <div className="small text-muted">Puntuación de Riesgo</div>
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={3}>
              <Card className="h-100">
                <Card.Body className="text-center py-4">
                  <div className="d-flex align-items-center justify-content-center mb-3">
                    <Database className="me-2" size={24} style={{color: '#0dcaf0'}} />
                    <span className="small" style={{color: '#6c757d'}}>+{Math.max(0, entities.length - 10)}</span>
                  </div>
                  <div className="h3 mb-1" style={{color: '#0dcaf0'}}>{entities.length}</div>
                  <div className="small text-muted">Entidades Totales</div>
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={3}>
              <Card className="h-100">
                <Card.Body className="text-center py-4">
                  <div className="d-flex align-items-center justify-content-center mb-3">
                    <Activity className="me-2" size={24} style={{color: '#ffc107'}} />
                    <span className="small" style={{color: '#6c757d'}}>ACTIVO</span>
                  </div>
                  <div className="h3 mb-1" style={{color: '#ffc107'}}>{metrics.suspiciousActivities}</div>
                  <div className="small text-muted">Actividades Sospechosas</div>
                </Card.Body>
              </Card>
            </Col>
          </Row>
          
          <Row className="mt-2">
            <Col>
              <div className="d-flex align-items-center justify-content-between">
                <div className="d-flex align-items-center gap-3">
                  <Button 
                    variant={autoRefreshEnabled ? 'outline-success' : 'outline-secondary'} 
                    size="sm" 
                    className="d-flex align-items-center gap-1"
                    onClick={() => {
                      const next = !autoRefreshEnabled;
                      setAutoRefreshEnabled(next);
                      if (next) void refreshAll();
                    }}
                  >
                    <RefreshCw size={14} />
                    Auto-refresh {autoRefreshEnabled ? 'ON' : 'OFF'}
                  </Button>
                  <span className="small text-muted">
                    Última actualización: {lastRefreshAt ? lastRefreshAt.toLocaleTimeString() : '-'}
                  </span>
                </div>
                <span className="small text-muted">En vivo</span>
              </div>
            </Col>
          </Row>
        </Container>

      {/* Contenido principal */}
      <Container fluid className="flex-grow-1">
        <Row className="h-100">
          {/* Panel principal */}
          <Col lg={9} className="p-3">
            <Tab.Container activeKey={activePanel} onSelect={(k) => setActivePanel(k as any)}>
              <Nav variant="tabs" className="mb-3 border-bottom">
                <Nav.Item>
                  <Nav.Link eventKey="overview">
                    <Home size={16} className="me-2" />
                    Vista General
                  </Nav.Link>
                </Nav.Item>
                <Nav.Item>
                  <Nav.Link eventKey="analysis">
                    <BarChart3 size={16} className="me-2" />
                    Análisis de Amenazas
                  </Nav.Link>
                </Nav.Item>
                <Nav.Item>
                  <Nav.Link eventKey="timeline">
                    <Calendar size={16} className="me-2" />
                    Línea de Tiempo
                  </Nav.Link>
                </Nav.Item>
                <Nav.Item>
                  <Nav.Link eventKey="geography">
                    <MapPin size={16} className="me-2" />
                    Análisis Geográfico
                  </Nav.Link>
                </Nav.Item>
                <Nav.Item>
                  <Nav.Link eventKey="network">
                    <Network size={16} className="me-2" />
                    Análisis de Red
                  </Nav.Link>
                </Nav.Item>
              </Nav>

              <Tab.Content>
                <Tab.Pane eventKey="overview">
                  <Row className="g-3">
                    {/* Panel de entidades */}
                    <Col lg={6}>
                      <Card className="h-100">
                        <Card.Header className="d-flex justify-content-between align-items-center">
                          <h6 className="mb-0">Entidades ({filteredEntities.length})</h6>
                          <div className="d-flex gap-2">
                            <OverlayTrigger
                              placement="top"
                              overlay={<Tooltip>Agregar nueva entidad</Tooltip>}
                            >
                              <Button variant="outline-primary" size="sm" onClick={handleAddEntity}>
                                <Plus size={14} />
                              </Button>
                            </OverlayTrigger>
                            <OverlayTrigger
                              placement="top"
                              overlay={<Tooltip>Filtros avanzados</Tooltip>}
                            >
                              <Button 
                                variant="outline-secondary" 
                                size="sm" 
                                onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                              >
                                <Filter size={14} />
                              </Button>
                            </OverlayTrigger>
                          </div>
                        </Card.Header>
                        
                        <Card.Body className="p-0">
                          {showAdvancedFilters && (
                            <div className="p-3 border-bottom">
                              <Row className="g-2">
                                <Col md={6}>
                                  <Form.Select size="sm" value={entityTypeFilter} onChange={(e) => setEntityTypeFilter(e.target.value)}>
                                    <option value="">Todos los tipos</option>
                                    <option value="email">Email</option>
                                    <option value="domain">Dominio</option>
                                    <option value="ip">IP</option>
                                    <option value="phone">Teléfono</option>
                                  </Form.Select>
                                </Col>
                                <Col md={6}>
                                  <Form.Select size="sm" value={entitySourceFilter} onChange={(e) => setEntitySourceFilter(e.target.value)}>
                                    <option value="">Todas las fuentes</option>
                                    <option value="manual">Manual</option>
                                    <option value="osint">OSINT</option>
                                    <option value="import">Importado</option>
                                  </Form.Select>
                                </Col>
                              </Row>
                            </div>
                          )}
                          
                          <div className="p-3">
                            <InputGroup size="sm" className="mb-3">
                              <InputGroup.Text>
                                <Search size={14} />
                              </InputGroup.Text>
                              <Form.Control
                                placeholder="Buscar entidades..."
                                value={entityFilter}
                                onChange={(e) => setEntityFilter(e.target.value)}
                              />
                            </InputGroup>
                          </div>
                          
                          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                            {filteredEntities.length === 0 ? (
                              <div className="text-center py-4 text-muted">
                                <Database size={32} className="mb-2 opacity-50" />
                                <p className="mb-0">No se encontraron entidades</p>
                              </div>
                            ) : (
                              <ListGroup variant="flush">
                                {filteredEntities.map((entity) => (
                                  <ListGroup.Item key={entity.id}>
                                    <div className="d-flex justify-content-between align-items-start">
                                      <div className="flex-grow-1">
                                        <div className="d-flex align-items-center gap-2 mb-1">
                                          <Badge bg="secondary" className="text-uppercase">
                                            {entity.type}
                                          </Badge>
                                          <code className="text-info">{entity.value}</code>
                                        </div>
                                        <p className="mb-1 small text-muted">{entity.description}</p>
                                        <div className="small text-muted">
                                          Creado: {entity.created_at || entity.createdAt ? new Date(entity.created_at || entity.createdAt!).toLocaleDateString() : 'N/A'}
                                        </div>
                                      </div>
                                      <Dropdown>
                                        <Dropdown.Toggle variant="outline-secondary" size="sm">
                                          <Edit size={14} />
                                        </Dropdown.Toggle>
                                        <Dropdown.Menu>
                                          <Dropdown.Item 
                                            onClick={() => handleEditEntity(entity)}
                                          >
                                            <Edit size={14} className="me-2" />
                                            Editar
                                          </Dropdown.Item>
                                          <Dropdown.Item 
                                            className="text-danger" 
                                            onClick={() => handleDeleteEntity(entity.id)}
                                          >
                                            <Trash2 size={14} className="me-2" />
                                            Eliminar
                                          </Dropdown.Item>
                                        </Dropdown.Menu>
                                      </Dropdown>
                                    </div>
                                  </ListGroup.Item>
                                ))}
                              </ListGroup>
                            )}
                          </div>
                        </Card.Body>
                      </Card>
                    </Col>

                    {/* Panel de ejecuciones OSINT */}
                    <Col lg={6}>
                      <Card className="h-100">
                        <Card.Header className="d-flex justify-content-between align-items-center">
                          <h6 className="mb-0">Ejecuciones OSINT ({executions.length})</h6>
                          <Button 
                            variant="outline-primary" 
                            size="sm" 
                            onClick={() => setShowOSINTPanel(true)}
                          >
                            <Plus size={14} className="me-1" />
                            Nueva Ejecución
                          </Button>
                        </Card.Header>
                        
                        <Card.Body className="p-0">
                          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                            {executions.length === 0 ? (
                              <div className="text-center py-5 text-muted">
                                <Clock size={32} className="mb-2 opacity-50" />
                                <p className="mb-0">No hay ejecuciones activas</p>
                                <Button 
                                  variant="outline-primary" 
                                  size="sm" 
                                  className="mt-2"
                                  onClick={() => setShowOSINTPanel(true)}
                                >
                                  Ejecutar herramienta OSINT
                                </Button>
                              </div>
                            ) : (
                              <div className="p-3">
                                {executions.map((execution) => {
                                  const tool = osintTools.find(t => t.id === execution.toolId);
                                  const canCancel = execution.status === 'pending' || execution.status === 'running';
                                  const canRetry = execution.status === 'failed' || execution.status === 'cancelled';
                                  return (
                                    <Card key={execution.id} className="mb-3">
                                      <Card.Body className="p-3">
                                        <div className="d-flex justify-content-between align-items-center mb-2">
                                          <div className="d-flex align-items-center gap-2">
                                            <div 
                                              className={`rounded-circle bg-${
                                                execution.status === 'completed' ? 'success' :
                                                execution.status === 'running' ? 'primary' :
                                                execution.status === 'failed' ? 'danger' : 'secondary'
                                              }`}
                                              style={{ width: '8px', height: '8px' }}
                                            />
                                            <h6 className="mb-0 small">{tool?.name ?? execution.toolId}</h6>
                                          </div>
                                          <div className="d-flex align-items-center gap-2">
                                            <Button
                                              variant="outline-info"
                                              size="sm"
                                              onClick={() => setShowExecutionDetails(execution.id)}
                                            >
                                              <Eye size={14} className="me-1" />
                                              Detalles
                                            </Button>
                                            {canCancel && (
                                              <Button
                                                variant="outline-danger"
                                                size="sm"
                                                disabled={executionActionLoading[`${execution.id}_cancel`]}
                                                onClick={() => handleExecutionAction(execution.id, 'cancel')}
                                              >
                                                <X size={14} className="me-1" />
                                                Cancelar
                                              </Button>
                                            )}
                                            {canRetry && (
                                              <Button
                                                variant="outline-warning"
                                                size="sm"
                                                disabled={executionActionLoading[`${execution.id}_retry`]}
                                                onClick={() => handleExecutionAction(execution.id, 'retry')}
                                              >
                                                <RefreshCw size={14} className="me-1" />
                                                Reintentar
                                              </Button>
                                            )}
                                            <Badge bg={getStatusVariant(execution.status)} className="small">
                                              {getStatusIcon(execution.status)}
                                              <span className="ms-1">
                                                {execution.status === 'completed' ? 'Completado' :
                                                 execution.status === 'running' ? 'Ejecutando' :
                                                 execution.status === 'failed' ? 'Fallido' :
                                                 execution.status === 'cancelled' ? 'Cancelado' :
                                                 'Pendiente'}
                                              </span>
                                            </Badge>
                                          </div>
                                        </div>
                                        
                                        {execution.status === 'running' && (
                                          <div className="mb-2">
                                            <div className="d-flex justify-content-between small text-muted mb-1">
                                              <span>Progreso</span>
                                              <span>{Math.round(execution.progress)}%</span>
                                            </div>
                                            <ProgressBar 
                                              now={execution.progress} 
                                              variant={execution.progress < 100 ? 'primary' : 'success'}
                                              style={{ height: '6px' }}
                                            />
                                          </div>
                                        )}
                                        
                                        {execution.error && (
                                          <Alert variant="danger" className="small mb-0 py-2">
                                            {execution.error}
                                          </Alert>
                                        )}
                                        
                                        {execution.results && (
                                          <div className="small text-success">
                                            ✓ {execution.results.find(r => r.type === 'data')?.count || 0} resultados encontrados
                                          </div>
                                        )}
                                      </Card.Body>
                                    </Card>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        </Card.Body>
                      </Card>
                    </Col>

                    <Col lg={12}>
                      <Card>
                        <Card.Header className="d-flex justify-content-between align-items-center">
                          <h6 className="mb-0">Auto Recon - Último resultado</h6>
                          <Badge bg={autoReconResult?.status === 'completed' ? 'success' : autoReconResult?.status === 'failed' ? 'danger' : 'secondary'}>
                            {autoReconResult?.status ?? 'Sin datos'}
                          </Badge>
                        </Card.Header>
                        <Card.Body>
                          {autoReconLoading ? (
                            <div className="text-center py-3">
                              <Spinner animation="border" size="sm" />
                            </div>
                          ) : autoReconError ? (
                            <Alert variant="danger" className="mb-0">{autoReconError}</Alert>
                          ) : !autoReconResult ? (
                            <div className="text-muted">Aún no se ha ejecutado Auto Recon en esta sesión.</div>
                          ) : (
                            <>
                              <div className="mb-3">
                                <strong className="text-muted">Objetivo:</strong>
                                <span className="ms-2">{autoReconResult?.target ?? '-'}</span>
                              </div>
                              <ListGroup>
                                {Object.entries(autoReconResult?.tools ?? {}).map(([toolName, toolData]: any) => {
                                  const hasError = Boolean(toolData?.error);
                                  const resultCount = Array.isArray(toolData?.results) ? toolData.results.length : 0;
                                  const expanded = !!autoReconExpanded[toolName];
                                  const summaryLines = buildAutoReconSummary(toolName, toolData);
                                  return (
                                    <ListGroup.Item key={toolName}>
                                      <div className="d-flex justify-content-between align-items-center">
                                        <div className="d-flex flex-column">
                                          <span className="text-capitalize">{toolName}</span>
                                          {!hasError && (
                                            <span className="small text-muted">
                                              Resultados: {resultCount}
                                            </span>
                                          )}
                                          {summaryLines.length > 0 && (
                                            <div className="small text-muted mt-1">
                                              {summaryLines.map((line, index) => (
                                                <div key={`${toolName}-${index}`}>{line}</div>
                                              ))}
                                            </div>
                                          )}
                                          {toolData?.metadata?.error && (
                                            <div className="small text-warning mt-1">
                                              {toolData.metadata.error}
                                            </div>
                                          )}
                                        </div>
                                        <div className="d-flex align-items-center gap-2">
                                          <Button
                                            variant="outline-info"
                                            size="sm"
                                            onClick={() => setAutoReconExpanded(prev => ({
                                              ...prev,
                                              [toolName]: !expanded
                                            }))}
                                          >
                                            {expanded ? 'Ocultar' : 'Ver'}
                                          </Button>
                                          <Badge bg={hasError ? 'warning' : 'success'}>
                                            {hasError ? toolData.error : 'OK'}
                                          </Badge>
                                        </div>
                                      </div>
                                      {expanded && (
                                        <div className="mt-2">
                                          <pre className="small mb-0" style={{ whiteSpace: 'pre-wrap' }}>
                                            {JSON.stringify(toolData, null, 2)}
                                          </pre>
                                        </div>
                                      )}
                                    </ListGroup.Item>
                                  );
                                })}
                              </ListGroup>
                            </>
                          )}
                        </Card.Body>
                      </Card>
                    </Col>
                  </Row>
                </Tab.Pane>
                
                <Tab.Pane eventKey="analysis">
                  <Row>
                    <Col md={6}>
                      <Card className="mb-3">
                        <Card.Header>
                          <h6 className="mb-0">Distribución de Entidades</h6>
                        </Card.Header>
                        <Card.Body>
                          {statsLoading ? (
                            <div className="text-center py-3">
                              <Spinner animation="border" size="sm" variant="light" />
                            </div>
                          ) : statsError ? (
                            <Alert variant="danger" className="small mb-0">{statsError}</Alert>
                          ) : entityTypeStats.length === 0 ? (
                            <div className="text-muted small">Sin datos disponibles</div>
                          ) : (
                            entityTypeStats.slice(0, 5).map((item) => (
                              <div className="mb-3" key={item.type}>
                                <div className="d-flex justify-content-between mb-1">
                                  <span className="small text-muted">{formatEntityType(item.type)}</span>
                                  <span className="small">{item.count} ({item.percent}%)</span>
                                </div>
                                <ProgressBar variant="info" now={item.percent} style={{ height: '8px' }} />
                              </div>
                            ))
                          )}
                        </Card.Body>
                      </Card>
                    </Col>
                    <Col md={6}>
                      <Card className="mb-3">
                        <Card.Header>
                          <h6 className="mb-0">Indicadores (IoCs)</h6>
                        </Card.Header>
                        <Card.Body>
                          {statsLoading ? (
                            <div className="text-center py-3">
                              <Spinner animation="border" size="sm" variant="light" />
                            </div>
                          ) : statsError ? (
                            <Alert variant="danger" className="small mb-0">{statsError}</Alert>
                          ) : iocStats.length === 0 ? (
                            <div className="text-muted small">Sin indicadores detectados</div>
                          ) : (
                            <ListGroup variant="flush">
                              {iocStats.map((item) => (
                                <ListGroup.Item key={item.type} className="d-flex justify-content-between">
                                  <span className="small">{formatEntityType(item.type)}</span>
                                  <Badge bg="warning">{item.count}</Badge>
                                </ListGroup.Item>
                              ))}
                            </ListGroup>
                          )}
                        </Card.Body>
                      </Card>
                    </Col>
                  </Row>
                  <Card>
                    <Card.Header>
                      <h6 className="mb-0">Estado de Ejecuciones</h6>
                    </Card.Header>
                    <Card.Body>
                      {statsLoading ? (
                        <div className="text-center py-3">
                          <Spinner animation="border" size="sm" variant="light" />
                        </div>
                      ) : statsError ? (
                        <Alert variant="danger" className="small mb-0">{statsError}</Alert>
                      ) : executionStatusStats.length === 0 ? (
                        <div className="text-muted small">Sin ejecuciones registradas</div>
                      ) : (
                        <ListGroup variant="flush">
                          {executionStatusStats.map((item) => (
                            <ListGroup.Item key={item.status} className="d-flex justify-content-between">
                              <span className="small text-capitalize">{item.status}</span>
                              <Badge bg="secondary">{item.count}</Badge>
                            </ListGroup.Item>
                          ))}
                        </ListGroup>
                      )}
                    </Card.Body>
                  </Card>
                </Tab.Pane>
                
                <Tab.Pane eventKey="timeline">
                  <Row>
                    <Col md={8}>
                      <Card>
                        <Card.Header className="d-flex justify-content-between align-items-center">
                          <h6 className="mb-0">Cronología de Eventos</h6>
                          <Form.Select size="sm" style={{ width: 'auto' }}>
                            <option>Últimas 24 horas</option>
                            <option>Última semana</option>
                            <option>Último mes</option>
                            <option>Todo el tiempo</option>
                          </Form.Select>
                        </Card.Header>
                        <Card.Body>
                          <div className="timeline">
                            {timelineItems.length === 0 ? (
                              <div className="text-muted small">Sin eventos</div>
                            ) : (
                              timelineItems.map((item, idx) => (
                                <div key={idx} className="timeline-item mb-4">
                                  <div className={`timeline-marker bg-${item.color}`}></div>
                                  <div className="timeline-content">
                                    <div className="d-flex justify-content-between align-items-start mb-2">
                                      <h6 className="mb-1">{item.title}</h6>
                                      <small className="text-muted">{item.timestamp.toLocaleString()}</small>
                                    </div>
                                    <p className="small text-muted mb-1">{item.description}</p>
                                    <Badge bg={item.color} className="small">{item.badge}</Badge>
                                  </div>
                                </div>
                              ))
                            )}
                          </div>
                        </Card.Body>
                      </Card>
                    </Col>
                    <Col md={4}>
                      <Card className="mb-3">
                        <Card.Header>
                          <h6 className="mb-0">Estadísticas de Actividad</h6>
                        </Card.Header>
                        <Card.Body>
                          <div className="mb-3">
                            <div className="d-flex justify-content-between mb-1">
                              <span className="small text-muted">Eventos Hoy</span>
                              <span className="small">8</span>
                            </div>
                            <div className="d-flex justify-content-between mb-1">
                              <span className="small text-muted">Esta Semana</span>
                              <span className="small">24</span>
                            </div>
                            <div className="d-flex justify-content-between mb-1">
                              <span className="small text-muted">Total</span>
                              <span className="small">156</span>
                            </div>
                          </div>
                        </Card.Body>
                      </Card>
                      
                      <Card>
                        <Card.Header>
                          <h6 className="mb-0">Filtros</h6>
                        </Card.Header>
                        <Card.Body>
                          <Form.Check 
                            type="checkbox" 
                            label="Eventos del Sistema" 
                            className="mb-2" 
                            defaultChecked
                          />
                          <Form.Check 
                            type="checkbox" 
                            label="Herramientas OSINT" 
                            className="mb-2" 
                            defaultChecked
                          />
                          <Form.Check 
                            type="checkbox" 
                            label="Alertas de Seguridad" 
                            className="mb-2" 
                            defaultChecked
                          />
                          <Form.Check 
                            type="checkbox" 
                            label="Acciones Manuales" 
                            defaultChecked
                          />
                        </Card.Body>
                      </Card>
                    </Col>
                  </Row>
                </Tab.Pane>
                
                <Tab.Pane eventKey="geography">
                  <Row>
                    <Col md={8}>
                      <Card>
                        <Card.Header className="d-flex justify-content-between align-items-center">
                          <h6 className="mb-0">Mapa de Amenazas</h6>
                        </Card.Header>
                        <Card.Body>
                          {statsLoading ? (
                            <div className="text-center py-4">
                              <Spinner animation="border" size="sm" variant="light" />
                            </div>
                          ) : statsError ? (
                            <Alert variant="danger" className="small mb-0">{statsError}</Alert>
                          ) : (
                            <div className="position-relative" style={{ height: '400px', backgroundColor: '#1a1a1a', borderRadius: '8px' }}>
                              <div className="position-absolute top-50 start-50 translate-middle text-center">
                                <MapPin size={48} className="mb-3 text-muted opacity-50" />
                                <h6 className="text-muted">Sin datos geográficos reales</h6>
                                <p className="small text-muted">Agrega entidades geolocalizadas para visualizar el mapa</p>
                              </div>
                            </div>
                          )}
                        </Card.Body>
                      </Card>
                    </Col>
                    <Col md={4}>
                      <Card className="mb-3">
                        <Card.Header>
                          <h6 className="mb-0">Resumen Geográfico</h6>
                        </Card.Header>
                        <Card.Body>
                          {statsLoading ? (
                            <div className="text-center py-3">
                              <Spinner animation="border" size="sm" variant="light" />
                            </div>
                          ) : statsError ? (
                            <Alert variant="danger" className="small mb-0">{statsError}</Alert>
                          ) : (
                            <>
                              <div className="d-flex justify-content-between mb-2">
                                <span className="small text-muted">Geolocalizaciones</span>
                                <span className="small">{geographySummary.geolocations}</span>
                              </div>
                              <div className="d-flex justify-content-between mb-2">
                                <span className="small text-muted">IPs</span>
                                <span className="small">{geographySummary.ips}</span>
                              </div>
                              <div className="d-flex justify-content-between">
                                <span className="small text-muted">Dominios</span>
                                <span className="small">{geographySummary.domains}</span>
                              </div>
                            </>
                          )}
                        </Card.Body>
                      </Card>
                      
                      <Card>
                        <Card.Header>
                          <h6 className="mb-0">Cobertura</h6>
                        </Card.Header>
                        <Card.Body>
                          {statsLoading ? (
                            <div className="text-center py-3">
                              <Spinner animation="border" size="sm" variant="light" />
                            </div>
                          ) : statsError ? (
                            <Alert variant="danger" className="small mb-0">{statsError}</Alert>
                          ) : (
                            <>
                              <div className="d-flex justify-content-between mb-2">
                                <span className="small text-muted">Entidades Totales</span>
                                <span className="small">{networkSummary.totalNodes}</span>
                              </div>
                              <div className="d-flex justify-content-between">
                                <span className="small text-muted">Cobertura Geográfica</span>
                                <span className="small">
                                  {networkSummary.totalNodes > 0
                                    ? Math.round((geographySummary.geolocations * 100) / networkSummary.totalNodes)
                                    : 0}%
                                </span>
                              </div>
                            </>
                          )}
                        </Card.Body>
                      </Card>
                    </Col>
                  </Row>
                </Tab.Pane>
                
                <Tab.Pane eventKey="network">
                  <Row>
                    <Col md={8}>
                      <Card>
                        <Card.Header className="d-flex justify-content-between align-items-center">
                          <h6 className="mb-0">Grafo de Relaciones</h6>
                          <div className="d-flex gap-2">
                            <Form.Select size="sm" style={{ width: 'auto' }}>
                              <option>Vista completa</option>
                              <option>Solo IPs</option>
                              <option>Solo dominios</option>
                              <option>Conexiones directas</option>
                            </Form.Select>
                            <Button variant="outline-secondary" size="sm">
                              <ZoomIn size={14} />
                            </Button>
                            <Button variant="outline-secondary" size="sm">
                              <Download size={14} />
                            </Button>
                          </div>
                        </Card.Header>
                        <Card.Body>
                          <div className="position-relative" style={{ height: '450px', backgroundColor: '#1a1a1a', borderRadius: '8px', overflow: 'hidden' }}>
                            <div className="position-absolute top-50 start-50 translate-middle text-center">
                              <Network size={48} className="mb-3 text-muted opacity-50" />
                              {statsLoading ? (
                                <div className="text-muted">Cargando datos de red...</div>
                              ) : statsError ? (
                                <div className="text-muted">Error al cargar datos de red</div>
                              ) : networkSummary.totalNodes === 0 && networkSummary.totalEdges === 0 ? (
                                <>
                                  <h6 className="text-muted">Sin datos reales</h6>
                                  <p className="small text-muted">Agrega entidades y relaciones para visualizar el grafo</p>
                                </>
                              ) : (
                                <>
                                  <h6 className="text-muted">Datos de red disponibles</h6>
                                  <p className="small text-muted">
                                    {networkSummary.totalNodes} nodos · {networkSummary.totalEdges} conexiones
                                  </p>
                                </>
                              )}
                            </div>
                          </div>
                        </Card.Body>
                      </Card>
                    </Col>
                    <Col md={4}>
                      <Card className="mb-3">
                        <Card.Header>
                          <h6 className="mb-0">Métricas de Red</h6>
                        </Card.Header>
                        <Card.Body>
                          {statsLoading ? (
                            <div className="text-center py-3">
                              <Spinner animation="border" size="sm" variant="light" />
                            </div>
                          ) : statsError ? (
                            <Alert variant="danger" className="small mb-0">{statsError}</Alert>
                          ) : (
                            <div className="mb-3">
                              <div className="d-flex justify-content-between mb-2">
                                <span className="small text-muted">Nodos Totales</span>
                                <span className="small">{networkSummary.totalNodes}</span>
                              </div>
                              <div className="d-flex justify-content-between mb-2">
                                <span className="small text-muted">Conexiones</span>
                                <span className="small">{networkSummary.totalEdges}</span>
                              </div>
                              <div className="d-flex justify-content-between mb-2">
                                <span className="small text-muted">Densidad</span>
                                <span className="small">{networkSummary.density}</span>
                              </div>
                              <div className="d-flex justify-content-between">
                                <span className="small text-muted">Componentes</span>
                                <span className="small">N/D</span>
                              </div>
                            </div>
                          )}
                        </Card.Body>
                      </Card>
                      
                      <Card className="mb-3">
                        <Card.Header>
                          <h6 className="mb-0">Nodos Centrales</h6>
                        </Card.Header>
                        <Card.Body>
                          {statsLoading ? (
                            <div className="text-center py-3">
                              <Spinner animation="border" size="sm" variant="light" />
                            </div>
                          ) : statsError ? (
                            <Alert variant="danger" className="small mb-0">{statsError}</Alert>
                          ) : (
                            <div className="text-muted small">Sin datos reales de centralidad</div>
                          )}
                        </Card.Body>
                      </Card>
                      
                      <Card>
                        <Card.Header>
                          <h6 className="mb-0">Tipos de Conexión</h6>
                        </Card.Header>
                        <Card.Body>
                          {statsLoading ? (
                            <div className="text-center py-3">
                              <Spinner animation="border" size="sm" variant="light" />
                            </div>
                          ) : statsError ? (
                            <Alert variant="danger" className="small mb-0">{statsError}</Alert>
                          ) : relationshipTypeStats.length === 0 ? (
                            <div className="text-muted small">Sin datos disponibles</div>
                          ) : (
                            relationshipTypeStats.slice(0, 5).map((item) => (
                              <div className="mb-2" key={item.type}>
                                <div className="d-flex justify-content-between align-items-center mb-1">
                                  <div className="d-flex align-items-center">
                                    <div className="bg-info" style={{ width: '12px', height: '2px' }}></div>
                                    <span className="small ms-2">{formatRelationshipType(item.type)}</span>
                                  </div>
                                  <span className="small text-muted">{item.count}</span>
                                </div>
                              </div>
                            ))
                          )}
                        </Card.Body>
                      </Card>
                    </Col>
                  </Row>
                </Tab.Pane>
              </Tab.Content>
            </Tab.Container>
          </Col>
          
          {/* Panel lateral de información */}
          <Col lg={3} className="p-3">
            <Card className="mb-3">
              <Card.Header>
                <h6 className="mb-0">Información de la Investigación</h6>
              </Card.Header>
              <Card.Body>
                <div className="small">
                  <div className="mb-2">
                    <strong className="text-muted">Estado:</strong>
                    <Badge
                      bg={(investigation?.status ?? 'active') === 'completed' ? 'secondary' : (investigation?.status ?? 'active') === 'paused' ? 'warning' : (investigation?.status ?? 'active') === 'archived' ? 'dark' : 'success'}
                      className="ms-2"
                    >
                      {(investigation?.status ?? 'active') === 'completed' ? 'Completada' : (investigation?.status ?? 'active') === 'paused' ? 'Pausada' : (investigation?.status ?? 'active') === 'archived' ? 'Archivada' : 'Activa'}
                    </Badge>
                  </div>
                  <div className="mb-2">
                    <strong className="text-muted">Prioridad:</strong>
                    <Badge
                      bg={['high', 'critical'].includes(investigation?.priority ?? 'medium') ? 'danger' : (investigation?.priority ?? 'medium') === 'medium' ? 'warning' : 'success'}
                      className="ms-2"
                    >
                      {['high', 'critical'].includes(investigation?.priority ?? 'medium') ? 'Alta' : (investigation?.priority ?? 'medium') === 'medium' ? 'Media' : 'Baja'}
                    </Badge>
                  </div>
                  <div className="mb-2">
                    <strong className="text-muted">Creada:</strong>
                    <span className="ms-2">{investigation?.createdAt ? new Date(investigation.createdAt).toLocaleDateString() : '-'}</span>
                  </div>
                  <div className="mb-2">
                    <strong className="text-muted">Actualizada:</strong>
                    <span className="ms-2">{investigation?.updatedAt ? new Date(investigation.updatedAt).toLocaleDateString() : '-'}</span>
                  </div>
                  <div className="mb-2">
                    <strong className="text-muted">Entidades:</strong>
                    <span className="ms-2">{entities.length}</span>
                  </div>
                </div>
              </Card.Body>
            </Card>
            
            <Card className="mt-3">
              <Card.Header>
                <h6 className="mb-0">OSINT Táctico</h6>
              </Card.Header>
              <Card.Body>
                <div className="d-grid gap-2">
                  <OverlayTrigger
                    placement="left"
                    overlay={<Tooltip>Ejecuta Ping, Nmap, Wappalyzer, Whois y DNS automáticamente sobre el objetivo</Tooltip>}
                  >
                    <Button 
                      variant="danger" 
                      size="lg" 
                      onClick={handleFullAutoRecon}
                      disabled={autoReconLoading}
                      className="d-flex align-items-center justify-content-center"
                    >
                      {autoReconLoading ? (
                        <Spinner animation="border" size="sm" className="me-2" />
                      ) : (
                        <Zap size={18} className="me-2" />
                      )}
                      {autoReconLoading ? 'Escaneando...' : 'AUTO RECON (Full Stack)'}
                    </Button>
                  </OverlayTrigger>
                  <div className="text-center text-muted small mt-1">
                    Script Python Automatizado
                  </div>
                  <OverlayTrigger
                    placement="left"
                    overlay={<Tooltip>Abrir herramientas OSINT dockerizadas y búsquedas avanzadas</Tooltip>}
                  >
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={handleOpenDockerTools}
                      className="d-flex align-items-center justify-content-center"
                    >
                      <Search size={16} className="me-2" />
                      Búsquedas Dockerizadas
                    </Button>
                  </OverlayTrigger>
                </div>
              </Card.Body>
            </Card>
            
            <Card>
              <Card.Header>
                <h6 className="mb-0">Acciones Rápidas</h6>
              </Card.Header>
              <Card.Body>
                <div className="d-grid gap-2">
                  <OverlayTrigger
                    placement="left"
                    overlay={<Tooltip>Ejecutar herramientas OSINT automáticamente</Tooltip>}
                  >
                    <Button variant="outline-primary" size="sm" onClick={() => setShowOSINTPanel(true)}>
                      <Zap size={14} className="me-2" />
                      Ejecutar OSINT
                    </Button>
                  </OverlayTrigger>
                  <OverlayTrigger
                    placement="left"
                    overlay={<Tooltip>Agregar nueva entidad a la investigación</Tooltip>}
                  >
                    <Button variant="outline-success" size="sm" onClick={handleAddEntity}>
                      <Plus size={14} className="me-2" />
                      Agregar Entidad
                    </Button>
                  </OverlayTrigger>
                  <OverlayTrigger
                    placement="left"
                    overlay={<Tooltip>Exportar datos de la investigación</Tooltip>}
                  >
                    <Button variant="outline-info" size="sm">
                      <FileDown size={14} className="me-2" />
                      Exportar Datos
                    </Button>
                  </OverlayTrigger>
                  <OverlayTrigger
                    placement="left"
                    overlay={<Tooltip>Compartir investigación con otros usuarios</Tooltip>}
                  >
                    <Button variant="outline-warning" size="sm">
                      <Share2 size={14} className="me-2" />
                      Compartir
                    </Button>
                  </OverlayTrigger>
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Container>

      {/* Panel lateral OSINT */}
      <Offcanvas 
        show={showOSINTPanel} 
        onHide={() => setShowOSINTPanel(false)} 
        placement="end"
        style={{ width: '400px' }}
      >
        <Offcanvas.Header closeButton className="border-bottom">
          <Offcanvas.Title>Herramientas OSINT</Offcanvas.Title>
        </Offcanvas.Header>
        <Offcanvas.Body>
          {!selectedTool ? (
            <div>
              <h6 className="mb-3">Seleccionar Herramienta</h6>
              <div className="d-grid gap-2">
                {toolsLoading ? (
                  <div className="text-center py-4">
                    <Spinner animation="border" variant="light" size="sm" />
                    <p className="mt-2 small text-muted">Cargando herramientas OSINT...</p>
                  </div>
                ) : toolsError ? (
                  <div className="text-center py-4 text-danger">
                    <AlertCircle size={20} className="mb-2" />
                    <p className="small mb-0">{toolsError}</p>
                  </div>
                ) : osintTools.length === 0 ? (
                  <div className="text-center py-4 text-muted">
                    <p className="small mb-0">No hay herramientas disponibles</p>
                  </div>
                ) : (
                  osintTools.map((tool) => (
                    <Card 
                      key={tool.id} 
                      className="cursor-pointer mb-2"
                      onClick={() => {
                        setSelectedTool(tool);
                        setToolParameters(tool.defaultParameters || {});
                      }}
                      style={{ cursor: 'pointer' }}
                    >
                      <Card.Body className="p-3">
                        <h6 className="mb-1">{tool.name}</h6>
                        <p className="small text-muted mb-1">{tool.description}</p>
                        <div className="d-flex flex-wrap gap-2">
                          <Badge bg="secondary" className="small">{tool.category}</Badge>
                          <Badge bg="light" text="dark" className="small border">{tool.inputType}</Badge>
                          {tool.requiresApiKey && (
                            <Badge bg="warning" text="dark" className="small">
                              API Key
                            </Badge>
                          )}
                        </div>
                      </Card.Body>
                    </Card>
                  ))
                )}
              </div>
            </div>
          ) : (
            <div>
              <div className="d-flex align-items-center justify-content-between mb-3">
                <h6 className="mb-0">{selectedTool.name}</h6>
                <Button 
                  variant="outline-secondary" 
                  size="sm" 
                  onClick={() => {
                    setSelectedTool(null);
                    setToolParameters({});
                  }}
                >
                  <X size={14} />
                </Button>
              </div>
              
              <p className="small text-muted mb-3">{selectedTool.description}</p>

              <div className="d-flex flex-wrap gap-2 mb-3">
                <Badge bg="secondary" className="small">{selectedTool.category}</Badge>
                <Badge bg="dark" className="small border border-secondary">{selectedTool.inputType}</Badge>
                {selectedTool.requiresApiKey && (
                  <Badge bg="warning" text="dark" className="small">
                    API Key
                  </Badge>
                )}
              </div>

              {selectedTool.requiresApiKey && (
                <Alert variant="warning" className="small border border-warning">
                  Requiere {selectedTool.apiKeyName ?? 'API key'} configurada en el backend.
                </Alert>
              )}
              
              <Form>
                {selectedTool.parameters.map((param: any) => (
                  <Form.Group key={param.name} className="mb-3">
                    <Form.Label className="small">
                      {param.description}
                      {param.required && <span className="text-danger">*</span>}
                    </Form.Label>
                    
                    {param.type === 'string' && (
                      <Form.Control
                        type="text"
                        placeholder={param.placeholder}
                        value={toolParameters[param.name] || ''}
                        onChange={(e) => setToolParameters(prev => ({
                          ...prev,
                          [param.name]: e.target.value
                        }))}
                      />
                    )}
                    
                    {param.type === 'number' && (
                      <Form.Control
                        type="number"
                        placeholder={param.placeholder}
                        value={toolParameters[param.name] || ''}
                        onChange={(e) => setToolParameters(prev => ({
                          ...prev,
                          [param.name]: parseInt(e.target.value) || ''
                        }))}
                      />
                    )}
                    
                    {param.type === 'boolean' && (
                      <Form.Check
                        type="checkbox"
                        label={param.description}
                        checked={toolParameters[param.name] || false}
                        onChange={(e) => setToolParameters(prev => ({
                          ...prev,
                          [param.name]: e.target.checked
                        }))}
                      />
                    )}
                    
                    {param.type === 'select' && param.options && (
                      <Form.Select
                        value={toolParameters[param.name] || ''}
                        onChange={(e) => setToolParameters(prev => ({
                          ...prev,
                          [param.name]: e.target.value
                        }))}
                      >
                        <option value="">Seleccionar...</option>
                        {param.options.map((option: string) => (
                          <option key={option} value={option}>{option}</option>
                        ))}
                      </Form.Select>
                    )}
                  </Form.Group>
                ))}
                
                <div className="d-grid gap-2 mt-4">
                  <Button 
                    variant="primary" 
                    onClick={() => executeOSINTTool()}
                    disabled={!isFormValid() || isExecuting}
                  >
                    {isExecuting ? (
                      <>
                        <Spinner animation="border" size="sm" className="me-2" />
                        Ejecutando...
                      </>
                    ) : (
                      <>
                        <Play size={14} className="me-2" />
                        Ejecutar
                      </>
                    )}
                  </Button>
                  <Button 
                    variant="outline-secondary" 
                    onClick={() => {
                      setSelectedTool(null);
                      setToolParameters({});
                    }}
                  >
                    Cancelar
                  </Button>
                </div>
              </Form>
            </div>
          )}
        </Offcanvas.Body>
      </Offcanvas>

      {/* Modal detalles de ejecución */}
      <Modal
        show={!!showExecutionDetails}
        onHide={() => setShowExecutionDetails(null)}
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title>Detalles de Ejecución</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {executionDetailsLoading ? (
            <div className="text-center py-4">
              <Spinner animation="border" variant="primary" size="sm" />
              <p className="mt-2 small text-muted mb-0">Cargando...</p>
            </div>
          ) : executionDetailsError ? (
            <Alert variant="danger" className="small mb-0">
              {executionDetailsError}
            </Alert>
          ) : !executionDetails ? (
            <div className="small text-muted">Sin datos disponibles</div>
          ) : (
            <div>
              <div className="d-flex flex-wrap gap-2 mb-3">
                <Badge bg="secondary">{String(executionDetails.transform_name ?? '')}</Badge>
                <Badge bg={getStatusVariant(String(executionDetails.status ?? 'pending') as ExecutionStatus)}>
                  {String(executionDetails.status ?? '')}
                </Badge>
                {executionDetails.duration != null && (
                  <Badge bg="info">{Number(executionDetails.duration).toFixed(1)}s</Badge>
                )}
              </div>
              <pre className="small mb-0" style={{ whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(executionDetails, null, 2)}
              </pre>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={() => setShowExecutionDetails(null)}>
            Cerrar
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Modal de Auto Recon */}
      <Modal show={showAutoReconModal} onHide={() => setShowAutoReconModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>
            <Zap className="me-2" size={20} />
            Auto Reconocimiento (Full Stack)
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p className="text-muted mb-3">
            Este proceso ejecutará automáticamente una secuencia de herramientas OSINT sobre el objetivo:
          </p>
          <ListGroup className="mb-4 small">
            <ListGroup.Item><Wifi size={14} className="me-2 text-success"/>Ping Check (Disponibilidad)</ListGroup.Item>
            <ListGroup.Item><Globe size={14} className="me-2 text-primary"/>Búsqueda DNS (A, MX, NS, TXT)</ListGroup.Item>
            <ListGroup.Item><FileText size={14} className="me-2 text-warning"/>Whois Lookup (Información de registro)</ListGroup.Item>
            <ListGroup.Item><Zap size={14} className="me-2 text-info"/>Wappalyzer (Tecnologías Web)</ListGroup.Item>
            <ListGroup.Item><Network size={14} className="me-2 text-danger"/>Nmap Scan (Puertos y Servicios)</ListGroup.Item>
          </ListGroup>
          
          <Form.Group className="mb-3">
            <Form.Label>Objetivo (URL, Dominio o IP)</Form.Label>
            <InputGroup>
              <InputGroup.Text><Target size={16} /></InputGroup.Text>
              <Form.Control 
                type="text" 
                placeholder="ejemplo.com" 
                value={autoReconTarget} 
                onChange={(e) => setAutoReconTarget(e.target.value)}
                autoFocus
              />
            </InputGroup>
            <Form.Text className="text-muted">
              Ingrese el dominio o URL raíz sin subdirectorios para mejores resultados.
            </Form.Text>
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowAutoReconModal(false)}>
            Cancelar
          </Button>
          <Button 
            variant="danger" 
            onClick={executeAutoRecon} 
            disabled={!autoReconTarget}
          >
            <Play size={16} className="me-2" />
            Iniciar Escaneo
          </Button>
        </Modal.Footer>
      </Modal>

      <Modal show={showDockerCatalogModal} onHide={() => setShowDockerCatalogModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>
            <Search className="me-2" size={20} />
            Búsquedas Dockerizadas
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form.Group className="mb-3">
            <Form.Label>Objetivo para dorking/indexación</Form.Label>
            <InputGroup>
              <InputGroup.Text><Target size={16} /></InputGroup.Text>
              <Form.Control
                type="text"
                placeholder="ejemplo.com"
                value={dockerTarget}
                onChange={(e) => setDockerTarget(e.target.value)}
              />
              <Button
                variant="outline-secondary"
                onClick={() => void loadDockerCatalog(dockerTarget)}
              >
                Actualizar
              </Button>
            </InputGroup>
          </Form.Group>

          {dockerCatalogLoading ? (
            <div className="text-center py-4">
              <Spinner animation="border" size="sm" />
            </div>
          ) : dockerCatalogError ? (
            <Alert variant="danger">{dockerCatalogError}</Alert>
          ) : (
            <>
              {(dockerCatalog?.indices?.length || 0) > 0 && (
                <Card className="mb-3">
                  <Card.Header>
                    <h6 className="mb-0">Índices Google</h6>
                  </Card.Header>
                  <Card.Body className="p-0">
                    <ListGroup variant="flush">
                      {(dockerCatalog?.indices || []).map((item: any, idx: number) => (
                        <ListGroup.Item key={`idx-${idx}`} className="d-flex justify-content-between">
                          <span className="text-muted">{item.operator}</span>
                          <span>{item.example}</span>
                        </ListGroup.Item>
                      ))}
                    </ListGroup>
                  </Card.Body>
                </Card>
              )}

              <Card className="mb-3">
                <Card.Header className="d-flex justify-content-between align-items-center">
                    <h6 className="mb-0">Google Dorks ({dockerCatalog?.dorks?.length || 0})</h6>
                    {selectedDorks.length > 0 && (
                        <Badge bg="primary">{selectedDorks.length} seleccionados</Badge>
                    )}
                </Card.Header>
                <Card.Body className="p-0" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                    <ListGroup variant="flush">
                        {(dockerCatalog?.dorks || []).map((dork: any, idx: number) => {
                            const query = dork.query.replace('{target}', dockerTarget || 'target');
                            const isSelected = selectedDorks.includes(query);
                            return (
                                <ListGroup.Item 
                                    key={`dork-${idx}`} 
                                    action 
                                    active={isSelected}
                                    onClick={() => toggleDork(query)}
                                    style={{ cursor: 'pointer' }}
                                >
                                    <div className="d-flex w-100 justify-content-between">
                                        <h6 className="mb-1">{dork.name}</h6>
                                        <small>{dork.category}</small>
                                    </div>
                                    <p className="mb-1 small font-monospace text-break">{query}</p>
                                    <small>{dork.intent}</small>
                                </ListGroup.Item>
                            );
                        })}
                    </ListGroup>
                </Card.Body>
              </Card>

            </>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowDockerCatalogModal(false)}>
            Cerrar
          </Button>
          <Button 
            variant="danger" 
            onClick={handleExecuteDorks}
            disabled={executingDorks || selectedDorks.length === 0}
          >
            {executingDorks ? <Spinner animation="border" size="sm" className="me-2" /> : <Play size={16} className="me-2" />}
            Ejecutar Seleccionados
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Modal de formulario de entidad */}
      {showEntityForm && (
        <EntityForm
          entity={selectedEntity || undefined}
          investigationId={id ?? ''}
          onSave={(entity) => {
            if (selectedEntity) {
              setEntities(prev => prev.map(e => e.id === entity.id ? entity : e));
            } else {
              setEntities(prev => [...prev, entity]);
            }
            setShowEntityForm(false);
            setSelectedEntity(null);
          }}
          onCancel={() => {
            setShowEntityForm(false);
            setSelectedEntity(null);
          }}
        />
      )}
      
      {/* Estilos CSS para la timeline */}
      <style>{timelineStyles}</style>
      </div>
    </div>
  );
};

export default InvestigationWorkspace;
