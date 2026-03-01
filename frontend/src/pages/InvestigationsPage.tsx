import React, { useState, useEffect } from 'react';
import { Alert, Container, Row, Col, Button, Card, Table, Form, InputGroup, Badge, Pagination, Modal, Spinner } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import Swal from 'sweetalert2';
import type { User, Investigation as BaseInvestigation, Entity as EntityType } from '../types';
import Header from '../shared/components/Header';
import InvestigationWorkspace from './InvestigationWorkspace';
import { apiService } from '../services/api';

type Investigation = BaseInvestigation & {
  toolsUsed?: string[];
  entitiesCount?: number;
};


interface InvestigationsPageProps {
  user: User;
  onLogout: () => void;
}

// Tipos para las nuevas funcionalidades
interface OSINTTool {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  parameters: ToolParameter[];
  inputType?: string;
  isAvailable: boolean;
  availabilityMessage?: string;
  requiresApiKey?: boolean;
  apiKeyName?: string;
}

interface ToolParameter {
  name: string;
  type: 'text' | 'select' | 'number' | 'boolean';
  label: string;
  required: boolean;
  options?: string[];
  placeholder?: string;
}

interface BackendInvestigationListItem {
  id: string;
  name: string;
  description: string;
  status: string;
  priority?: string;
  target?: string;
  jurisdiction?: string;
  estimated_loss?: string;
  victim_count?: number | null;
  case_number?: string;
  created_by?: { username?: string } | null;
  created_at: string;
  updated_at: string;
  entities_count?: number;
  relationships_count?: number;
  executions_count?: number;
}


const placeholderForInputType = (inputType: string) => {
  switch (inputType) {
    case 'ip':
      return '192.168.1.1';
    case 'email':
      return 'user@domain.com';
    case 'url':
      return 'https://ejemplo.com';
    case 'domain':
      return 'ejemplo.com';
    default:
      return 'Ingrese el objetivo';
  }
};

const inferParameterType = (value: any): 'text' | 'select' | 'number' | 'boolean' => {
  if (typeof value === 'boolean') return 'boolean';
  if (typeof value === 'number') return 'number';
  return 'text';
};

const mapTransformToTool = (t: any): OSINTTool => {
  const inputType = typeof t?.input_type === 'string' ? t.input_type : 'any';
  const defaultParameters: Record<string, any> =
    t?.parameters && typeof t.parameters === 'object' && !Array.isArray(t.parameters)
      ? t.parameters
      : {};

  const optionalParameters: ToolParameter[] = Object.entries(defaultParameters)
    .filter(([key]) => key !== 'target' && key !== 'input' && key !== 'entity_type')
    .map(([key, value]) => ({
      name: String(key),
      type: inferParameterType(value),
      label: String(key),
      required: false,
      placeholder: typeof value === 'number' || typeof value === 'string' ? String(value) : undefined,
    }));

  const isAvailable = typeof t?.is_available === 'boolean' ? t.is_available : true;
  const availabilityMessage = typeof t?.availability_message === 'string' ? t.availability_message : undefined;
  const requiresApiKey = typeof t?.requires_api_key === 'boolean' ? t.requires_api_key : false;
  const apiKeyName = typeof t?.api_key_name === 'string' ? t.api_key_name : undefined;

  return {
    id: String(t?.name ?? ''),
    name: String(t?.display_name ?? t?.name ?? ''),
    description: String(t?.description ?? ''),
    icon: 'bi bi-cpu',
    category: String(t?.category ?? 'otros'),
    inputType,
    isAvailable,
    availabilityMessage,
    requiresApiKey,
    apiKeyName,
    parameters: [
      { name: 'target', type: 'text', label: `Objetivo (${inputType})`, required: true, placeholder: placeholderForInputType(inputType) },
      ...optionalParameters,
    ],
  };
};

const emptyInvestigationForm: Partial<Investigation> = {
  title: '',
  description: '',
  status: 'active',
  priority: 'medium',
  tags: [],
  target: '',
  jurisdiction: '',
  estimated_loss: '',
  victim_count: undefined,
  case_number: '',
};

const InvestigationsPage: React.FC<InvestigationsPageProps> = ({ user, onLogout }) => {
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [filteredInvestigations, setFilteredInvestigations] = useState<Investigation[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [toolsFilter, setToolsFilter] = useState('all');
  const [entitiesFilter, setEntitiesFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [showModal, setShowModal] = useState(false);
  const [newInvestigation, setNewInvestigation] = useState<Partial<Investigation>>(emptyInvestigationForm);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedInvestigation, setSelectedInvestigation] = useState<Investigation | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [editInvestigation, setEditInvestigation] = useState<Partial<Investigation>>(emptyInvestigationForm);
  const [editSaving, setEditSaving] = useState(false);
  const [showEntityModal, setShowEntityModal] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [showSessionExpiredModal, setShowSessionExpiredModal] = useState(false);
  const [sessionExpiredMessage, setSessionExpiredMessage] = useState('Sesión expirada. Inicia sesión nuevamente.');

  const [selectedTool, setSelectedTool] = useState<OSINTTool | null>(null);
  const [toolParameters, setToolParameters] = useState<{[key: string]: any}>({});
  const [osintTools, setOsintTools] = useState<OSINTTool[]>([]);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [toolsError, setToolsError] = useState<string | null>(null);
  const [showToolModal, setShowToolModal] = useState(false);
  const [toolSearch, setToolSearch] = useState('');
  const [toolInvestigationId, setToolInvestigationId] = useState<string | null>(null);
  const [entityInvestigationId, setEntityInvestigationId] = useState<string | null>(null);
  const [entityForm, setEntityForm] = useState<{ type: EntityType['type']; value: string; description: string }>({ type: 'domain', value: '', description: '' });

  const [workspaceMode, setWorkspaceMode] = useState(false);
  const itemsPerPage = 5;
  const navigate = useNavigate();

  const isAuthRelatedMessage = (message: string) => {
    const m = message.toLowerCase();
    return m.includes('sesión expirada') || m.includes('no autorizado') || m.includes('token not valid') || m.includes('token no válido');
  };

  const openSessionExpired = (message?: string) => {
    setSessionExpiredMessage(message || 'Sesión expirada. Inicia sesión nuevamente.');
    setShowModal(false);
    setShowViewModal(false);
    setShowEditModal(false);
    setSelectedInvestigation(null);
    setEditInvestigation(emptyInvestigationForm);
    setSelectedTool(null);
    setShowEntityModal(false);
    setShowToolModal(false);
    setShowSessionExpiredModal(true);
  };

  const maybeHandleAuthExpired = (message?: string, errors?: unknown) => {
    if (apiService.isAuthenticated()) return false;

    const errorItems: unknown[] = Array.isArray(errors) ? errors : [];
    const candidates: string[] = [
      ...(typeof message === 'string' ? [message] : []),
      ...errorItems.filter((e) => typeof e === 'string') as string[],
    ];

    if (candidates.some((m) => isAuthRelatedMessage(m))) {
      openSessionExpired(message);
      return true;
    }

    return false;
  };



  useEffect(() => {
    loadInvestigations();
    loadMockEntities();
    loadMockExecutions();
    loadTools();
  }, []);

  useEffect(() => {
    filterInvestigations();
  }, [investigations, searchTerm, statusFilter, priorityFilter, toolsFilter, entitiesFilter]);

  const filterInvestigations = () => {
    let filtered = [...investigations];

    // Filtrar por término de búsqueda
    if (searchTerm) {
      filtered = filtered.filter(inv => 
        inv.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        inv.description.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Filtrar por estado
    if (statusFilter !== 'all') {
      filtered = filtered.filter(inv => inv.status === statusFilter);
    }

    // Filtrar por prioridad
    if (priorityFilter !== 'all') {
      filtered = filtered.filter(inv => inv.priority === priorityFilter);
    }

    // Filtrar por herramientas (mock)
    if (toolsFilter !== 'all') {
      // En una implementación real, esto filtrarían por herramientas utilizadas
      filtered = filtered.filter(inv => inv.id !== '999'); // Mock filter
    }

    // Filtrar por entidades (mock)
    if (entitiesFilter !== 'all') {
      // En una implementación real, esto filtrarían por tipos de entidades
      filtered = filtered.filter(inv => inv.id !== '999'); // Mock filter
    }

    setFilteredInvestigations(filtered);
    setCurrentPage(1); // Reset a la primera página cuando se filtra
  };

  const loadMockEntities = () => {
    // Mock entities loading removed
  };

  const loadMockExecutions = () => {
    // Mock executions loading removed
  };

  const isToolFormValid = () => {
    if (!selectedTool) return false;
    const requiredParams = selectedTool.parameters.filter((p) => p.required);
    return requiredParams.every((param) => {
      const value = toolParameters[param.name];
      return value !== undefined && value !== null && value !== '';
    });
  };

  const handleToolExecution = (tool: OSINTTool) => {
    const execute = async () => {
      if (!toolInvestigationId) {
        setPageError('Seleccione una investigación para ejecutar la herramienta.');
        return;
      }

      if (!isToolFormValid()) {
        setPageError('Complete los parámetros requeridos para ejecutar la herramienta.');
        return;
      }

      const requiredParams = tool.parameters.filter((p) => p.required);
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
        setPageError('No se pudo determinar el input para la ejecución.');
        return;
      }

      const value = String(rawValue).trim();
      const looksLikeIp = /^(\d{1,3}\.){3}\d{1,3}$/.test(value);
      const looksLikeUrl = /^https?:\/\//.test(value);
      const entityType =
        toolParameters.entity_type ? String(toolParameters.entity_type) :
        tool.inputType && tool.inputType !== 'any' ? tool.inputType :
        looksLikeUrl ? 'url' :
        looksLikeIp ? 'ip' :
        'domain';

      const parameters: Record<string, any> = { ...toolParameters };
      delete parameters.target;
      delete parameters.entity_type;
      delete parameters.email;
      delete parameters.domain;
      delete parameters.username;
      delete parameters.entity_value;

      const res = await apiService.createTransformExecution(toolInvestigationId, {
        transform_name: tool.id,
        input: { entity_type: entityType, value },
        parameters,
      });

      if (!res.success) {
        if (maybeHandleAuthExpired(res.message, res.errors)) return;
        setPageError(res.message || 'No se pudo ejecutar la herramienta.');
        return;
      }

      setToolParameters({});
      setSelectedTool(null);
      setShowToolModal(false);
    };

    void execute();
  };

  const handleAddEntity = (entityData: Partial<EntityType>) => {
    const create = async () => {
      if (!entityInvestigationId) {
        setPageError('Seleccione una investigación válida para agregar la entidad.');
        return;
      }
      const value = (entityData.value || '').trim();
      if (!value) {
        setPageError('El valor de la entidad es obligatorio.');
        return;
      }

      const res = await apiService.createEntity(
        {
          name: value,
          type: entityData.type ?? 'domain',
          value,
          description: entityData.description,
          properties: entityData.properties ?? {},
        },
        entityInvestigationId
      );

      if (!res.success) {
        if (maybeHandleAuthExpired(res.message, res.errors)) return;
        setPageError(res.message || 'No se pudo crear la entidad.');
        return;
      }

      setEntityForm({ type: 'domain', value: '', description: '' });
      setShowEntityModal(false);
      await loadInvestigations();
    };

    void create();
  };



  const getCurrentPageItems = () => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filteredInvestigations.slice(startIndex, endIndex);
  };

  const totalPages = Math.ceil(filteredInvestigations.length / itemsPerPage);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'dark';
      case 'paused': return 'dark';
      case 'completed': return 'dark';
      case 'archived': return 'dark';
      default: return 'dark';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'active': return 'Activo';
      case 'paused': return 'Pausado';
      case 'completed': return 'Completado';
      case 'archived': return 'Archivado';
      default: return status;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'dark';
      case 'high': return 'dark';
      case 'medium': return 'dark';
      case 'low': return 'dark';
      default: return 'dark';
    }
  };

  const getPriorityText = (priority: string) => {
    switch (priority) {
      case 'critical': return 'Crítica';
      case 'high': return 'Alta';
      case 'medium': return 'Media';
      case 'low': return 'Baja';
      default: return priority;
    }
  };

  const handleView = (investigation: Investigation) => {
    setShowViewModal(true);
    setSelectedInvestigation(investigation);
    setDetailLoading(true);
    const load = async () => {
      const res = await apiService.getInvestigation(investigation.id);
      if (!res.success || !res.data) {
        if (maybeHandleAuthExpired(res.message, res.errors)) {
          setDetailLoading(false);
          return;
        }
        setPageError(res.message || 'No se pudo cargar la investigación');
        setDetailLoading(false);
        return;
      }
      setSelectedInvestigation(res.data);
      setDetailLoading(false);
    };
    void load();
  };

  const handleEdit = (investigation: Investigation) => {
    setShowEditModal(true);
    setEditInvestigation({
      ...emptyInvestigationForm,
      ...investigation,
    });
    setDetailLoading(true);
    const load = async () => {
      const res = await apiService.getInvestigation(investigation.id);
      if (!res.success || !res.data) {
        if (maybeHandleAuthExpired(res.message, res.errors)) {
          setDetailLoading(false);
          return;
        }
        setPageError(res.message || 'No se pudo cargar la investigación');
        setDetailLoading(false);
        return;
      }
      setEditInvestigation({
        ...emptyInvestigationForm,
        ...res.data,
      });
      setDetailLoading(false);
    };
    void load();
  };

  const handleDelete = async (investigation: Investigation) => {
    const result = await Swal.fire({
      title: '¿Estás seguro?',
      text: `¿Está seguro de que desea eliminar la investigación "${investigation.title}"?`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (result.isConfirmed) {
      const res = await apiService.deleteInvestigation(investigation.id);
      if (res.success) {
        Swal.fire('¡Eliminado!', 'La investigación ha sido eliminada.', 'success');
        await loadInvestigations();
        return;
      }
      if (maybeHandleAuthExpired(res.message, res.errors)) return;
      Swal.fire('Error', res.message || 'No se pudo eliminar la investigación', 'error');
    }
  };

  const handleWorkspace = (investigation: Investigation) => {
    navigate(`/investigations/workspace/${investigation.id}`);
  };



  const handleCreateInvestigation = () => {
    const create = async () => {
      const title = (newInvestigation.title || '').trim();
      const description = (newInvestigation.description || '').trim();
      if (!title) {
        setPageError('El título es obligatorio.');
        return;
      }
      if (title.length < 3) {
        setPageError('El título debe tener al menos 3 caracteres.');
        return;
      }

      setPageError(null);
      const res = await apiService.createInvestigation({
        name: title,
        description,
        status: newInvestigation.status || 'active',
        priority: newInvestigation.priority || 'medium',
        target: newInvestigation.target?.trim() || undefined,
        jurisdiction: newInvestigation.jurisdiction?.trim() || undefined,
        estimated_loss: newInvestigation.estimated_loss?.trim() || undefined,
        victim_count: typeof newInvestigation.victim_count === 'number' ? newInvestigation.victim_count : undefined,
        case_number: newInvestigation.case_number?.trim() || undefined,
        metadata: {
          tags: newInvestigation.tags || [],
        },
      } as any);

      if (res.success) {
        setShowModal(false);
        setNewInvestigation(emptyInvestigationForm);
        await loadInvestigations();
        return;
      }

      if (maybeHandleAuthExpired(res.message, res.errors)) return;
      console.error('💥 Error al crear investigación:', res.message, res.errors);
      setPageError(res.message || 'No se pudo crear la investigación');
    };

    void create();
  };

  const handleUpdateInvestigation = () => {
    const update = async () => {
      if (!editInvestigation.id) return;
      const title = (editInvestigation.title || '').trim();
      const description = (editInvestigation.description || '').trim();
      if (!title) {
        setPageError('El título es obligatorio.');
        return;
      }
      if (title.length < 3) {
        setPageError('El título debe tener al menos 3 caracteres.');
        return;
      }

      setEditSaving(true);
      setPageError(null);
      const res = await apiService.updateInvestigation(editInvestigation.id, {
        name: title,
        description,
        status: editInvestigation.status || 'active',
        priority: editInvestigation.priority || 'medium',
        target: editInvestigation.target?.trim() || undefined,
        jurisdiction: editInvestigation.jurisdiction?.trim() || undefined,
        estimated_loss: editInvestigation.estimated_loss?.trim() || undefined,
        victim_count: typeof editInvestigation.victim_count === 'number' ? editInvestigation.victim_count : undefined,
        case_number: editInvestigation.case_number?.trim() || undefined,
        metadata: {
          tags: editInvestigation.tags || [],
        },
      } as any);

      if (res.success) {
        setShowEditModal(false);
        setEditInvestigation(emptyInvestigationForm);
        await loadInvestigations();
        setEditSaving(false);
        return;
      }

      if (maybeHandleAuthExpired(res.message, res.errors)) {
        setEditSaving(false);
        return;
      }
      setPageError(res.message || 'No se pudo actualizar la investigación');
      setEditSaving(false);
    };

    void update();
  };

  const loadTools = async () => {
    setToolsLoading(true);
    setToolsError(null);
    try {
      const res = await apiService.listTransforms({ enabled: true });
      if (!res.success) {
        if (maybeHandleAuthExpired(res.message, res.errors)) return;
        setToolsError(res.message || 'No se pudieron cargar las herramientas.');
        setOsintTools([]);
        return;
      }
      const tools = (res.data || []).map(mapTransformToTool);
      setOsintTools(tools);
    } catch (err) {
      setToolsError(err instanceof Error ? err.message : 'No se pudieron cargar las herramientas.');
      setOsintTools([]);
    } finally {
      setToolsLoading(false);
    }
  };

  const openToolModal = (investigation: Investigation) => {
    setToolInvestigationId(investigation.id);
    setSelectedTool(null);
    setToolParameters({});
    setToolSearch('');
    setShowToolModal(true);
  };

  const openEntityModal = (investigation: Investigation) => {
    setEntityInvestigationId(investigation.id);
    setEntityForm({ type: 'domain', value: '', description: '' });
    setShowEntityModal(true);
  };

  const loadInvestigations = async () => {
    try {
      setPageError(null);
      const res = await apiService.getInvestigations();
      if (!res.success) {
        if (maybeHandleAuthExpired(res.message, res.errors)) return;
        setInvestigations([]);
        setPageError(res.message || 'No se pudieron cargar las investigaciones');
        return;
      }

      const payload: any = res.data;
      const items: BackendInvestigationListItem[] = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.results)
          ? payload.results
          : [];

      const mapped: Investigation[] = items.map((inv) => {
        const status = (inv.status || 'active') as Investigation['status'];
        const safeStatus: Investigation['status'] = (['active', 'completed', 'paused', 'archived'] as const).includes(status as any)
          ? status
          : 'active';
        const rawPriority = (inv.priority || 'medium') as Investigation['priority'];
        const safePriority: Investigation['priority'] = (['low', 'medium', 'high', 'critical'] as const).includes(rawPriority as any)
          ? rawPriority
          : 'medium';

        return {
          id: inv.id,
          title: inv.name,
          description: inv.description || '',
          status: safeStatus,
          priority: safePriority,
          entities: [],
          createdBy: inv.created_by?.username || 'N/A',
          createdAt: inv.created_at,
          updatedAt: inv.updated_at,
          entitiesCount: inv.entities_count ?? 0,
          toolsUsed: [],
          tags: [],
          target: inv.target,
          jurisdiction: inv.jurisdiction,
          estimated_loss: inv.estimated_loss,
          victim_count: typeof inv.victim_count === 'number' ? inv.victim_count : undefined,
          case_number: inv.case_number,
        };
      });

      setInvestigations(mapped);
    } catch (err) {
      setInvestigations([]);
      setPageError(err instanceof Error ? err.message : 'No se pudieron cargar las investigaciones');
    }
  };

  return (
    <div className="app-shell">
      <Header 
        user={user} 
        onLogout={onLogout} 
        showWorkspaceToggle={true}
        workspaceMode={workspaceMode}
        onWorkspaceToggle={() => setWorkspaceMode(!workspaceMode)}
      />

      <Container fluid className="app-page py-4">
        {pageError && (
          <Row className="mb-3">
            <Col>
              <Alert variant="danger" className="mb-0">
                {pageError}
              </Alert>
            </Col>
          </Row>
        )}
        {!workspaceMode ? (
          // Vista de Tabla Tradicional
          <>
            <Row className="mb-4">
              <Col>
                <div className="d-flex justify-content-between align-items-center">
                  <h4 className="mb-0">
                    <i className="bi bi-search me-2"></i>
                    Investigaciones
                  </h4>
                  <Button 
                    variant="primary"
                    onClick={() => setShowModal(true)}
                  >
                    <i className="bi bi-plus-lg me-2"></i>
                    Nueva Investigación
                  </Button>
                </div>
              </Col>
            </Row>

            <Row className="mb-4">
              <Col md={3}>
                <Card className="h-100">
                  <Card.Body className="d-flex align-items-center justify-content-between">
                    <div>
                      <div className="text-secondary small text-uppercase">Total</div>
                      <div className="fs-3 fw-semibold">{investigations.length}</div>
                    </div>
                    <i className="bi bi-search fs-2 text-primary"></i>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={3}>
                <Card className="h-100">
                  <Card.Body className="d-flex align-items-center justify-content-between">
                    <div>
                      <div className="text-secondary small text-uppercase">Activas</div>
                      <div className="fs-3 fw-semibold">{investigations.filter(i => i.status === 'active' || i.status === 'paused').length}</div>
                    </div>
                    <i className="bi bi-play-circle fs-2 text-primary"></i>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={3}>
                <Card className="h-100">
                  <Card.Body className="d-flex align-items-center justify-content-between">
                    <div>
                      <div className="text-secondary small text-uppercase">Completadas</div>
                      <div className="fs-3 fw-semibold">{investigations.filter(i => i.status === 'completed').length}</div>
                    </div>
                    <i className="bi bi-check-circle fs-2 text-primary"></i>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={3}>
                <Card className="h-100">
                  <Card.Body className="d-flex align-items-center justify-content-between">
                    <div>
                      <div className="text-secondary small text-uppercase">Archivadas</div>
                      <div className="fs-3 fw-semibold">{investigations.filter(i => i.status === 'archived').length}</div>
                    </div>
                    <i className="bi bi-archive fs-2 text-primary"></i>
                  </Card.Body>
                </Card>
              </Col>
            </Row>

        {/* Filtros y Búsqueda */}
        <Row className="mb-4">
          <Col>
            <Card>
              <Card.Body>
                <Row className="g-3">
                  <Col md={3}>
                    <InputGroup>
                      <InputGroup.Text>
                        <i className="bi bi-search"></i>
                      </InputGroup.Text>
                      <Form.Control
              type="text"
              placeholder="Buscar investigaciones..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
                    </InputGroup>
                  </Col>
                  <Col md={2}>
                    <Form.Select
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                    >
                      <option value="all">Todos los estados</option>
                      <option value="active">Activo</option>
                      <option value="completed">Completado</option>
                      <option value="archived">Archivado</option>
                    </Form.Select>
                  </Col>
                  <Col md={2}>
                    <Form.Select
                      value={priorityFilter}
                      onChange={(e) => setPriorityFilter(e.target.value)}
                    >
                      <option value="all">Todas las prioridades</option>
                      <option value="critical">Crítica</option>
                      <option value="high">Alta</option>
                      <option value="medium">Media</option>
                      <option value="low">Baja</option>
                    </Form.Select>
                  </Col>
                  <Col md={2}>
                    <Form.Select
                      value={toolsFilter}
                      onChange={(e) => setToolsFilter(e.target.value)}
                    >
                      <option value="all">Todas las herramientas</option>
                      <option value="holehe">Holehe</option>
                      <option value="assetfinder">Assetfinder</option>
                      <option value="amass">Amass</option>
                      <option value="nmap">Nmap</option>
                      <option value="shodan">Shodan</option>
                    </Form.Select>
                  </Col>
                  <Col md={2}>
                    <Form.Select
                      value={entitiesFilter}
                      onChange={(e) => setEntitiesFilter(e.target.value)}
                    >
                      <option value="all">Todos los tipos</option>
                      <option value="domain">Dominios</option>
                      <option value="ip">IPs</option>
                      <option value="email">Emails</option>
                      <option value="person">Personas</option>
                    </Form.Select>
                  </Col>
                  <Col md={1}>
                    <Button variant="outline-light" className="w-100" onClick={() => setShowModal(true)}>
                      <i className="bi bi-plus-circle"></i>
                    </Button>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Tabla de Investigaciones */}
        <Row>
          <Col>
            <Card>
              <Card.Body className="p-0">
                <Table responsive hover className="mb-0">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Título</th>
                      <th>Target</th>
                      <th>Estado</th>
                      <th>Prioridad</th>
                      <th>Tools Used</th>
                      <th>Entities Count</th>
                      <th>Fecha Creación</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {getCurrentPageItems().map((investigation) => (
                      <tr key={investigation.id}>
                        <td className="text-muted">#{investigation.id}</td>
                        <td className="fw-bold">{investigation.title}</td>
                        <td>
                          <code className="text-primary">{investigation.target || 'N/A'}</code>
                        </td>
                        <td>
                          <Badge bg={getStatusColor(investigation.status)}>
                            {getStatusText(investigation.status)}
                          </Badge>
                        </td>
                        <td>
                          <Badge bg={getPriorityColor(investigation.priority)}>
                            {getPriorityText(investigation.priority)}
                          </Badge>
                        </td>
                        <td>
                          <div className="d-flex flex-wrap gap-1">
                            {investigation.toolsUsed?.slice(0, 2).map((tool, index) => (
                              <Badge key={index} bg="secondary" className="small">
                                {tool}
                              </Badge>
                            ))}
                            {investigation.toolsUsed && investigation.toolsUsed.length > 2 && (
                              <Badge bg="secondary" className="small">
                                +{investigation.toolsUsed.length - 2}
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td>
                          <Badge bg="primary" className="rounded-pill">
                            {investigation.entitiesCount || 0}
                          </Badge>
                        </td>
                        <td className="text-muted">
                          {new Date(investigation.createdAt).toLocaleDateString('es-ES')}
                        </td>
                        <td>
                          <div className="d-flex gap-1">
                            <Button 
                              variant="outline-primary" 
                              size="sm"
                              title="Abrir Workspace"
                              onClick={() => handleWorkspace(investigation)}
                            >
                              <i className="bi bi-laptop"></i>
                            </Button>
                            <Button 
                              variant="outline-secondary" 
                              size="sm"
                              title="Ver en Grafo"
                              onClick={() => navigate(`/graphs?investigationId=${encodeURIComponent(investigation.id)}`)}
                            >
                              <i className="bi bi-diagram-3"></i>
                            </Button>
                            <Button
                              variant="outline-secondary"
                              size="sm"
                              title="Ejecutar herramienta OSINT"
                              onClick={() => openToolModal(investigation)}
                            >
                              <i className="bi bi-play"></i>
                            </Button>
                            <Button
                              variant="outline-secondary"
                              size="sm"
                              title="Agregar entidad"
                              onClick={() => openEntityModal(investigation)}
                            >
                              <i className="bi bi-plus"></i>
                            </Button>
                            <Button variant="outline-secondary" size="sm" title="Ver detalles" onClick={() => handleView(investigation)}>
                              <i className="bi bi-eye"></i>
                            </Button>
                            <Button variant="outline-secondary" size="sm" title="Editar" onClick={() => handleEdit(investigation)}>
                              <i className="bi bi-pencil"></i>
                            </Button>
                            <Button variant="outline-danger" size="sm" title="Eliminar" onClick={() => handleDelete(investigation)}>
                              <i className="bi bi-trash"></i>
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Paginación */}
        {totalPages > 1 && (
          <Row className="mt-4">
            <Col className="d-flex justify-content-center">
              <Pagination>
                <Pagination.Prev 
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(currentPage - 1)}
                />
                {[...Array(totalPages)].map((_, index) => (
                  <Pagination.Item
                    key={index + 1}
                    active={index + 1 === currentPage}
                    onClick={() => setCurrentPage(index + 1)}
                  >
                    {index + 1}
                  </Pagination.Item>
                ))}
                <Pagination.Next 
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage(currentPage + 1)}
                />
              </Pagination>
            </Col>
          </Row>
        )}
        </>
        ) : (
          // Vista de Workspace
          <InvestigationWorkspace />
        )}

        {/* Modal para Herramienta OSINT */}
        <Modal show={showToolModal} onHide={() => { setShowToolModal(false); setSelectedTool(null); }} size="lg" centered>
          <Modal.Header closeButton>
            <Modal.Title>
              {selectedTool && (
                <>
                  <i className={`${selectedTool.icon} me-2 text-secondary`}></i>
                  {selectedTool.name}
                </>
              )}
              {!selectedTool && (
                <>
                  <i className="bi bi-cpu me-2 text-secondary"></i>
                  Herramientas OSINT
                </>
              )}
            </Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {!selectedTool && (
              <>
                <Form className="mb-3">
                  <Form.Control
                    type="text"
                    placeholder="Buscar herramienta..."
                    value={toolSearch}
                    onChange={(e) => setToolSearch(e.target.value)}
                  />
                </Form>
                {toolsLoading && (
                  <div className="text-center py-3">
                    <Spinner animation="border" size="sm" className="me-2" />
                    Cargando herramientas...
                  </div>
                )}
                {toolsError && (
                  <Alert variant="danger">
                    {toolsError}
                  </Alert>
                )}
                {!toolsLoading && !toolsError && (
                  <div className="d-grid gap-2">
                    {osintTools
                      .filter((tool) =>
                        tool.name.toLowerCase().includes(toolSearch.toLowerCase()) ||
                        tool.description.toLowerCase().includes(toolSearch.toLowerCase())
                      )
                      .map((tool) => (
                        <Button
                          key={tool.id}
                          variant="outline-secondary"
                          className="text-start"
                          disabled={!tool.isAvailable}
                          onClick={() => setSelectedTool(tool)}
                        >
                          <div className="d-flex align-items-center justify-content-between gap-2">
                            <div className="fw-semibold">{tool.name}</div>
                            {!tool.isAvailable && (
                              <Badge bg="danger">No disponible</Badge>
                            )}
                            {tool.isAvailable && tool.requiresApiKey && tool.apiKeyName && (
                              <Badge bg="warning" text="dark">API key</Badge>
                            )}
                          </div>
                          <div className="text-secondary" style={{ fontSize: '0.85rem' }}>
                            {tool.description || 'Sin descripción'}
                          </div>
                          {!tool.isAvailable && tool.availabilityMessage && (
                            <div className="text-warning small mt-1">
                              {tool.availabilityMessage}
                            </div>
                          )}
                        </Button>
                      ))}
                    {osintTools.length === 0 && (
                      <div className="text-secondary text-center">
                        No hay herramientas disponibles.
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
            {selectedTool && (
              <>
                {!selectedTool.isAvailable && (
                  <Alert variant="warning" className="border border-secondary">
                    {selectedTool.availabilityMessage || 'Esta herramienta no está disponible en este entorno.'}
                  </Alert>
                )}
                {selectedTool.isAvailable && selectedTool.requiresApiKey && selectedTool.apiKeyName && (
                  <Alert variant="secondary" className="border border-secondary text-light">
                    Requiere API key: {selectedTool.apiKeyName}
                  </Alert>
                )}
                <div className="mb-4 p-3 rounded border border-secondary">
                  <p className="mb-0 text-secondary" style={{ fontSize: '0.95rem' }}>{selectedTool.description}</p>
                </div>
                <Form>
                  <Row className="g-4">
                    {selectedTool.parameters.map((param: any) => (
                      <Col md={12} key={param.name}>
                        <Form.Group>
                          <Form.Label className="text-light">
                            {param.label}
                          </Form.Label>
                          {param.type === 'text' && (
                            <Form.Control
                              type="text"
                              placeholder={param.placeholder}
                              className="bg-dark border-secondary text-light"
                              value={toolParameters[param.name] || ''}
                              onChange={(e) => setToolParameters(prev => ({...prev, [param.name]: e.target.value}))}
                            />
                          )}
                          {param.type === 'select' && (
                            <Form.Select
                              className="bg-dark border-secondary text-light"
                              value={toolParameters[param.name] || ''}
                              onChange={(e) => setToolParameters(prev => ({...prev, [param.name]: e.target.value}))}
                            >
                              <option value="">Seleccionar...</option>
                              {param.options?.map((option: string) => (
                                <option key={option} value={option}>{option}</option>
                              ))}
                            </Form.Select>
                          )}
                          {param.type === 'number' && (
                            <Form.Control
                              type="number"
                              placeholder={param.placeholder}
                              className="bg-dark border-secondary text-light"
                              value={toolParameters[param.name] || ''}
                              onChange={(e) => setToolParameters(prev => ({...prev, [param.name]: e.target.value}))}
                            />
                          )}
                          {param.type === 'boolean' && (
                            <Form.Check
                              type="checkbox"
                              label={param.label}
                              className="text-light"
                              checked={toolParameters[param.name] || false}
                              onChange={(e) => setToolParameters(prev => ({...prev, [param.name]: e.target.checked}))}
                            />
                          )}
                        </Form.Group>
                      </Col>
                    ))}
                  </Row>
                </Form>
              </>
            )}
          </Modal.Body>
          <Modal.Footer className="bg-dark border-secondary">
            {selectedTool ? (
              <>
                <Button variant="outline-secondary" onClick={() => setSelectedTool(null)}>
                  Cambiar herramienta
                </Button>
                <Button
                  variant="outline-light"
                  disabled={!selectedTool.isAvailable}
                  onClick={() => {
                    if (selectedTool) {
                      handleToolExecution(selectedTool);
                    }
                  }}
                >
                  <i className="bi bi-play-fill me-2"></i>
                  Ejecutar Herramienta
                </Button>
              </>
            ) : (
              <Button variant="outline-secondary" onClick={() => setShowToolModal(false)}>
                Cerrar
              </Button>
            )}
          </Modal.Footer>
        </Modal>

        <Modal show={showSessionExpiredModal} onHide={() => setShowSessionExpiredModal(false)} centered>
          <Modal.Header closeButton className="bg-dark border-secondary">
            <Modal.Title className="text-light">Sesión expirada</Modal.Title>
          </Modal.Header>
          <Modal.Body className="bg-dark text-light">
            <div className="text-secondary">{sessionExpiredMessage}</div>
          </Modal.Body>
          <Modal.Footer className="bg-dark border-secondary">
            <Button variant="outline-light" onClick={() => onLogout()}>
              Iniciar sesión
            </Button>
          </Modal.Footer>
        </Modal>

        {/* Modal para Agregar Entidad */}
        <Modal show={showEntityModal} onHide={() => setShowEntityModal(false)} centered>
          <Modal.Header closeButton className="bg-dark border-secondary">
            <Modal.Title className="text-light">
              <i className="bi bi-plus-circle me-2 text-secondary"></i>
              Agregar Entidad
            </Modal.Title>
          </Modal.Header>
          <Modal.Body className="bg-dark text-light">
            <div className="mb-4 p-3 rounded border border-secondary">
              <p className="mb-0 text-secondary" style={{ fontSize: '0.9rem' }}>
                <i className="bi bi-info-circle me-2"></i>
                Agregue una nueva entidad para enriquecer su investigación
              </p>
            </div>
            <Form>
              <Row className="g-4">
                <Col md={6}>
                  <Form.Group>
                    <Form.Label className="text-light">
                      <i className="bi bi-tag me-2 text-secondary"></i>
                      Tipo de Entidad
                    </Form.Label>
                    <Form.Select
                      className="bg-dark border-secondary text-light"
                      value={entityForm.type}
                      onChange={(e) => setEntityForm(prev => ({ ...prev, type: e.target.value as EntityType['type'] }))} 
                    >
                      <option value="domain">Dominio</option>
                      <option value="ip">Dirección IP</option>
                      <option value="email">Email</option>
                      <option value="person">Persona</option>
                      <option value="phone">Teléfono</option>
                      <option value="url">URL</option>
                      <option value="organization">Organización</option>
                      <option value="social_media">Red Social</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label className="text-light">
                      <i className="bi bi-pencil me-2 text-secondary"></i>
                      Valor
                    </Form.Label>
                    <Form.Control
                      type="text"
                      placeholder="ejemplo.com, 192.168.1.1, user@domain.com..."
                      className="bg-dark border-secondary text-light"
                      value={entityForm.value}
                      onChange={(e) => setEntityForm(prev => ({ ...prev, value: e.target.value }))}
                    />
                  </Form.Group>
                </Col>
                <Col md={12}>
                  <Form.Group>
                    <Form.Label className="text-light">
                      <i className="bi bi-chat-text me-2 text-secondary"></i>
                      Descripción (Opcional)
                    </Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={2}
                      placeholder="Información adicional sobre esta entidad..."
                      className="bg-dark border-secondary text-light"
                      value={entityForm.description}
                      onChange={(e) => setEntityForm(prev => ({ ...prev, description: e.target.value }))}
                    />
                  </Form.Group>
                </Col>
              </Row>
            </Form>
          </Modal.Body>
          <Modal.Footer className="bg-dark border-secondary">
            <Button variant="outline-secondary" onClick={() => setShowEntityModal(false)}>
              Cancelar
            </Button>
            <Button variant="outline-light" onClick={() => handleAddEntity(entityForm)}>
              <i className="bi bi-plus-circle me-2"></i>
              Agregar Entidad
            </Button>
          </Modal.Footer>
        </Modal>

        <Modal show={showViewModal} onHide={() => { setShowViewModal(false); setSelectedInvestigation(null); setDetailLoading(false); }} size="lg" centered>
          <Modal.Header closeButton className="bg-dark border-secondary">
            <Modal.Title className="text-light">
              <i className="bi bi-eye me-2 text-secondary"></i>
              Detalles de la Investigación
            </Modal.Title>
          </Modal.Header>
          <Modal.Body className="bg-dark text-light">
            {detailLoading && (
              <div className="text-center py-4">
                <Spinner animation="border" size="sm" className="me-2" />
                Cargando investigación...
              </div>
            )}
            {!detailLoading && selectedInvestigation && (
              <div className="d-grid gap-3">
                <div>
                  <div className="text-secondary small">Título</div>
                  <div className="fw-semibold">{selectedInvestigation.title}</div>
                </div>
                <div>
                  <div className="text-secondary small">Descripción</div>
                  <div>{selectedInvestigation.description || 'Sin descripción'}</div>
                </div>
                <Row className="g-3">
                  <Col md={6}>
                    <div className="text-secondary small">Estado</div>
                    <Badge bg={getStatusColor(selectedInvestigation.status)} className="border border-secondary text-light">
                      {getStatusText(selectedInvestigation.status)}
                    </Badge>
                  </Col>
                  <Col md={6}>
                    <div className="text-secondary small">Prioridad</div>
                    <Badge bg={getPriorityColor(selectedInvestigation.priority)} className="border border-secondary text-light">
                      {getPriorityText(selectedInvestigation.priority)}
                    </Badge>
                  </Col>
                </Row>
                <Row className="g-3">
                  <Col md={6}>
                    <div className="text-secondary small">Target</div>
                    <div>{selectedInvestigation.target || 'N/A'}</div>
                  </Col>
                  <Col md={6}>
                    <div className="text-secondary small">Jurisdicción</div>
                    <div>{selectedInvestigation.jurisdiction || 'N/A'}</div>
                  </Col>
                </Row>
                <Row className="g-3">
                  <Col md={6}>
                    <div className="text-secondary small">Pérdida estimada</div>
                    <div>{selectedInvestigation.estimated_loss || 'N/A'}</div>
                  </Col>
                  <Col md={6}>
                    <div className="text-secondary small">Número de víctimas</div>
                    <div>{typeof selectedInvestigation.victim_count === 'number' ? selectedInvestigation.victim_count : 'N/A'}</div>
                  </Col>
                </Row>
                <Row className="g-3">
                  <Col md={6}>
                    <div className="text-secondary small">Número de caso</div>
                    <div>{selectedInvestigation.case_number || 'N/A'}</div>
                  </Col>
                  <Col md={6}>
                    <div className="text-secondary small">Etiquetas</div>
                    <div>{selectedInvestigation.tags && selectedInvestigation.tags.length > 0 ? selectedInvestigation.tags.join(', ') : 'N/A'}</div>
                  </Col>
                </Row>
              </div>
            )}
          </Modal.Body>
          <Modal.Footer className="bg-dark border-secondary">
            <Button variant="outline-secondary" onClick={() => { setShowViewModal(false); setSelectedInvestigation(null); setDetailLoading(false); }}>
              Cerrar
            </Button>
          </Modal.Footer>
        </Modal>

        <Modal show={showEditModal} onHide={() => { setShowEditModal(false); setEditInvestigation(emptyInvestigationForm); setDetailLoading(false); }} size="lg" centered>
          <Modal.Header closeButton className="bg-dark border-secondary">
            <Modal.Title className="text-light">
              <i className="bi bi-pencil me-2 text-secondary"></i>
              Editar Investigación
            </Modal.Title>
          </Modal.Header>
          <Modal.Body className="bg-dark text-light">
            {detailLoading && (
              <div className="text-center py-4">
                <Spinner animation="border" size="sm" className="me-2" />
                Cargando investigación...
              </div>
            )}
            {!detailLoading && (
              <Form>
                <Row className="g-4">
                  <Col md={12}>
                    <Form.Group>
                      <Form.Label className="text-light">
                        <i className="bi bi-file-text me-2 text-secondary"></i>
                        Título de la Investigación
                      </Form.Label>
                      <Form.Control
                        type="text"
                        placeholder="Ej: Análisis de Fraude Financiero - Banco XYZ"
                        className="bg-dark border-secondary text-light"
                        value={editInvestigation.title || ''}
                        onChange={(e) => setEditInvestigation(prev => ({...prev, title: e.target.value}))}
                      />
                    </Form.Group>
                  </Col>
                  <Col md={12}>
                    <Form.Group>
                      <Form.Label className="text-light">
                        <i className="bi bi-chat-text me-2 text-secondary"></i>
                        Descripción y Objetivos
                      </Form.Label>
                      <Form.Control
                        as="textarea"
                        rows={3}
                        placeholder="Describa el contexto, objetivos específicos y alcance de la investigación..."
                        className="bg-dark border-secondary text-light"
                        value={editInvestigation.description || ''}
                        onChange={(e) => setEditInvestigation(prev => ({...prev, description: e.target.value}))}
                      />
                    </Form.Group>
                  </Col>
                  <Col md={12}>
                    <Form.Group>
                      <Form.Label className="text-light">
                        <i className="bi bi-bullseye me-2 text-secondary"></i>
                        Target Principal
                      </Form.Label>
                      <Form.Control
                        type="text"
                        placeholder="ejemplo.com, 192.168.1.1, usuario@empresa.com, Nombre Persona..."
                        className="bg-dark border-secondary text-light"
                        value={editInvestigation.target || ''}
                        onChange={(e) => setEditInvestigation(prev => ({...prev, target: e.target.value}))}
                      />
                      <Form.Text className="text-secondary">
                        Entidad principal que será el foco de la investigación
                      </Form.Text>
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group>
                      <Form.Label className="text-light">
                        <i className="bi bi-hash me-2 text-secondary"></i>
                        Número de Caso
                      </Form.Label>
                      <Form.Control
                        type="text"
                        placeholder="Caso-2026-001"
                        className="bg-dark border-secondary text-light"
                        value={editInvestigation.case_number || ''}
                        onChange={(e) => setEditInvestigation(prev => ({...prev, case_number: e.target.value}))}
                      />
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group>
                      <Form.Label className="text-light">
                        <i className="bi bi-geo-alt me-2 text-secondary"></i>
                        Jurisdicción
                      </Form.Label>
                      <Form.Control
                        type="text"
                        placeholder="MX, ES, EU..."
                        className="bg-dark border-secondary text-light"
                        value={editInvestigation.jurisdiction || ''}
                        onChange={(e) => setEditInvestigation(prev => ({...prev, jurisdiction: e.target.value}))}
                      />
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group>
                      <Form.Label className="text-light">
                        <i className="bi bi-cash-stack me-2 text-secondary"></i>
                        Pérdida Estimada
                      </Form.Label>
                      <Form.Control
                        type="text"
                        placeholder="USD 120,000"
                        className="bg-dark border-secondary text-light"
                        value={editInvestigation.estimated_loss || ''}
                        onChange={(e) => setEditInvestigation(prev => ({...prev, estimated_loss: e.target.value}))}
                      />
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group>
                      <Form.Label className="text-light">
                        <i className="bi bi-people me-2 text-secondary"></i>
                        Número de Víctimas
                      </Form.Label>
                      <Form.Control
                        type="number"
                        min={0}
                        placeholder="0"
                        className="bg-dark border-secondary text-light"
                        value={typeof editInvestigation.victim_count === 'number' ? editInvestigation.victim_count : ''}
                        onChange={(e) => {
                          const value = e.target.value;
                          const parsed = value === '' ? undefined : Number(value);
                          setEditInvestigation(prev => ({...prev, victim_count: Number.isFinite(parsed as number) ? (parsed as number) : undefined}));
                        }}
                      />
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group>
                      <Form.Label className="text-light">
                        <i className="bi bi-activity me-2 text-secondary"></i>
                        Estado
                      </Form.Label>
                      <Form.Select 
                        className="bg-dark border-secondary text-light"
                        value={editInvestigation.status || 'active'}
                        onChange={(e) => setEditInvestigation(prev => ({...prev, status: e.target.value as Investigation['status']}))}
                      >
                        <option value="active">Activa</option>
                        <option value="paused">Pausada</option>
                        <option value="completed">Completada</option>
                        <option value="archived">Archivada</option>
                      </Form.Select>
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group>
                      <Form.Label className="text-light">
                        <i className="bi bi-exclamation-triangle me-2 text-secondary"></i>
                        Nivel de Prioridad
                      </Form.Label>
                      <Form.Select 
                        className="bg-dark border-secondary text-light"
                        value={editInvestigation.priority || 'medium'}
                        onChange={(e) => setEditInvestigation(prev => ({...prev, priority: e.target.value as Investigation['priority']}))}
                      >
                        <option value="low">Baja</option>
                        <option value="medium">Media</option>
                        <option value="high">Alta</option>
                        <option value="critical">Crítica</option>
                      </Form.Select>
                    </Form.Group>
                  </Col>
                  <Col md={12}>
                    <Form.Group>
                      <Form.Label className="text-light">
                        <i className="bi bi-tags me-2 text-secondary"></i>
                        Etiquetas y Categorías
                      </Form.Label>
                      <Form.Control
                        type="text"
                        placeholder="fraude, financiero, bancario, phishing, malware, social engineering..."
                        className="bg-dark border-secondary text-light"
                        value={editInvestigation.tags?.join(', ') || ''}
                        onChange={(e) => setEditInvestigation(prev => ({
                          ...prev, 
                          tags: e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0)
                        }))}
                      />
                      <Form.Text className="text-secondary">
                        Separe las etiquetas con comas para facilitar la búsqueda y categorización
                      </Form.Text>
                    </Form.Group>
                  </Col>
                </Row>
              </Form>
            )}
          </Modal.Body>
          <Modal.Footer className="bg-dark border-secondary">
            <Button variant="outline-secondary" onClick={() => { setShowEditModal(false); setEditInvestigation(emptyInvestigationForm); setDetailLoading(false); }}>
              Cancelar
            </Button>
            <Button variant="outline-light" onClick={handleUpdateInvestigation} disabled={editSaving}>
              {editSaving ? (
                <>
                  <Spinner animation="border" size="sm" className="me-2" />
                  Guardando...
                </>
              ) : (
                <>
                  <i className="bi bi-save me-2"></i>
                  Guardar Cambios
                </>
              )}
            </Button>
          </Modal.Footer>
        </Modal>

        {/* Modal para Nueva Investigación */}
        <Modal show={showModal} onHide={() => setShowModal(false)} size="lg" centered>
          <Modal.Header closeButton className="bg-dark border-secondary">
            <Modal.Title className="text-light">
              <i className="bi bi-plus-circle me-2 text-secondary"></i>
              Nueva Investigación OSINT
            </Modal.Title>
          </Modal.Header>
          <Modal.Body className="bg-dark text-light">
            <div className="mb-4 p-3 rounded border border-secondary">
              <p className="mb-0 text-secondary" style={{ fontSize: '0.9rem' }}>
                <i className="bi bi-lightbulb me-2"></i>
                Configure los detalles de su nueva investigación OSINT. Todos los campos son importantes para un seguimiento efectivo.
              </p>
            </div>
            <Form>
              <Row className="g-4">
                <Col md={12}>
                  <Form.Group>
                    <Form.Label className="text-light">
                      <i className="bi bi-file-text me-2 text-secondary"></i>
                      Título de la Investigación
                    </Form.Label>
                    <Form.Control
                      type="text"
                      placeholder="Ej: Análisis de Fraude Financiero - Banco XYZ"
                      className="bg-dark border-secondary text-light"
                      value={newInvestigation.title}
                      onChange={(e) => setNewInvestigation(prev => ({...prev, title: e.target.value}))}
                    />
                  </Form.Group>
                </Col>
                <Col md={12}>
                  <Form.Group>
                    <Form.Label className="text-light">
                      <i className="bi bi-chat-text me-2 text-secondary"></i>
                      Descripción y Objetivos
                    </Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={3}
                      placeholder="Describa el contexto, objetivos específicos y alcance de la investigación..."
                      className="bg-dark border-secondary text-light"
                      value={newInvestigation.description}
                      onChange={(e) => setNewInvestigation(prev => ({...prev, description: e.target.value}))}
                    />
                  </Form.Group>
                </Col>
                <Col md={12}>
                  <Form.Group>
                    <Form.Label className="text-light">
                      <i className="bi bi-bullseye me-2 text-secondary"></i>
                      Target Principal
                    </Form.Label>
                    <Form.Control
                      type="text"
                      placeholder="ejemplo.com, 192.168.1.1, usuario@empresa.com, Nombre Persona..."
                      className="bg-dark border-secondary text-light"
                      value={newInvestigation.target || ''}
                      onChange={(e) => setNewInvestigation(prev => ({...prev, target: e.target.value}))}
                    />
                    <Form.Text className="text-secondary">
                      Entidad principal que será el foco de la investigación
                    </Form.Text>
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label className="text-light">
                      <i className="bi bi-hash me-2 text-secondary"></i>
                      Número de Caso
                    </Form.Label>
                    <Form.Control
                      type="text"
                      placeholder="Caso-2026-001"
                      className="bg-dark border-secondary text-light"
                      value={newInvestigation.case_number || ''}
                      onChange={(e) => setNewInvestigation(prev => ({...prev, case_number: e.target.value}))}
                    />
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label className="text-light">
                      <i className="bi bi-geo-alt me-2 text-secondary"></i>
                      Jurisdicción
                    </Form.Label>
                    <Form.Control
                      type="text"
                      placeholder="MX, ES, EU..."
                      className="bg-dark border-secondary text-light"
                      value={newInvestigation.jurisdiction || ''}
                      onChange={(e) => setNewInvestigation(prev => ({...prev, jurisdiction: e.target.value}))}
                    />
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label className="text-light">
                      <i className="bi bi-cash-stack me-2 text-secondary"></i>
                      Pérdida Estimada
                    </Form.Label>
                    <Form.Control
                      type="text"
                      placeholder="USD 120,000"
                      className="bg-dark border-secondary text-light"
                      value={newInvestigation.estimated_loss || ''}
                      onChange={(e) => setNewInvestigation(prev => ({...prev, estimated_loss: e.target.value}))}
                    />
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label className="text-light">
                      <i className="bi bi-people me-2 text-secondary"></i>
                      Número de Víctimas
                    </Form.Label>
                    <Form.Control
                      type="number"
                      min={0}
                      placeholder="0"
                      className="bg-dark border-secondary text-light"
                      value={typeof newInvestigation.victim_count === 'number' ? newInvestigation.victim_count : ''}
                      onChange={(e) => {
                        const value = e.target.value;
                        const parsed = value === '' ? undefined : Number(value);
                        setNewInvestigation(prev => ({...prev, victim_count: Number.isFinite(parsed as number) ? (parsed as number) : undefined}));
                      }}
                    />
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label className="text-light">
                      <i className="bi bi-activity me-2 text-secondary"></i>
                      Estado Inicial
                    </Form.Label>
                    <Form.Select 
                      className="bg-dark border-secondary text-light"
                      value={newInvestigation.status}
                      onChange={(e) => setNewInvestigation(prev => ({...prev, status: e.target.value as Investigation['status']}))}
                    >
                      <option value="active">Activa</option>
                      <option value="paused">Pausada</option>
                      <option value="completed">Completada</option>
                      <option value="archived">Archivada</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label className="text-light">
                      <i className="bi bi-exclamation-triangle me-2 text-secondary"></i>
                      Nivel de Prioridad
                    </Form.Label>
                    <Form.Select 
                      className="bg-dark border-secondary text-light"
                      value={newInvestigation.priority}
                      onChange={(e) => setNewInvestigation(prev => ({...prev, priority: e.target.value as 'low' | 'medium' | 'high' | 'critical'}))}
                    >
                      <option value="low">Baja</option>
                      <option value="medium">Media</option>
                      <option value="high">Alta</option>
                      <option value="critical">Crítica</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={12}>
                  <Form.Group>
                    <Form.Label className="text-light">
                      <i className="bi bi-tags me-2 text-secondary"></i>
                      Etiquetas y Categorías
                    </Form.Label>
                    <Form.Control
                      type="text"
                      placeholder="fraude, financiero, bancario, phishing, malware, social engineering..."
                      className="bg-dark border-secondary text-light"
                      value={newInvestigation.tags?.join(', ') || ''}
                      onChange={(e) => setNewInvestigation(prev => ({
                        ...prev, 
                        tags: e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0)
                      }))}
                    />
                    <Form.Text className="text-secondary">
                      Separe las etiquetas con comas para facilitar la búsqueda y categorización
                    </Form.Text>
                  </Form.Group>
                </Col>
              </Row>
            </Form>
          </Modal.Body>
          <Modal.Footer className="bg-dark border-secondary">
            <Button variant="outline-secondary" onClick={() => setShowModal(false)}>
              Cancelar
            </Button>
            <Button variant="outline-light" onClick={handleCreateInvestigation}>
              <i className="bi bi-plus-circle me-2"></i>
              Crear Investigación
            </Button>
          </Modal.Footer>
        </Modal>
      </Container>
    </div>
  );
};

export default InvestigationsPage;
