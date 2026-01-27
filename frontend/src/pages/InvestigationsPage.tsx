import React, { useState, useEffect } from 'react';
import { Alert, Container, Row, Col, Button, Card, Table, Form, InputGroup, Badge, Pagination, Modal } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import type { User } from '../types';
import Header from '../components/Header';
import InvestigationWorkspace from './InvestigationWorkspace';
import { apiService } from '../services/api';

interface Investigation {
  id: string;
  title: string;
  description: string;
  status: 'active' | 'completed' | 'paused' | 'archived';
  priority: 'low' | 'medium' | 'high' | 'critical';
  entities: string[];
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  target?: string;
  toolsUsed?: string[];
  entitiesCount?: number;
  tags?: string[];
}


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
  category: 'reconnaissance' | 'enumeration' | 'scanning' | 'analysis';
  parameters: ToolParameter[];
}

interface ToolParameter {
  name: string;
  type: 'text' | 'select' | 'number' | 'boolean';
  label: string;
  required: boolean;
  options?: string[];
  placeholder?: string;
}

interface Entity {
  id: string;
  type: 'domain' | 'ip' | 'email' | 'person' | 'phone' | 'url';
  value: string;
  source: string;
  confidence: number;
  createdAt: string;
}

interface BackendInvestigationListItem {
  id: string;
  name: string;
  description: string;
  status: string;
  created_by?: { username?: string } | null;
  created_at: string;
  updated_at: string;
  entities_count?: number;
  relationships_count?: number;
  executions_count?: number;
}


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
  const [newInvestigation, setNewInvestigation] = useState<Partial<Investigation>>({title: '', description: '', status: 'active', priority: 'medium', tags: []});
  const [showEntityModal, setShowEntityModal] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [showSessionExpiredModal, setShowSessionExpiredModal] = useState(false);
  const [sessionExpiredMessage, setSessionExpiredMessage] = useState('Sesión expirada. Inicia sesión nuevamente.');

  const [selectedTool, setSelectedTool] = useState<OSINTTool | null>(null);
  const [toolParameters, setToolParameters] = useState<{[key: string]: any}>({});

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
    setSelectedTool(null);
    setShowEntityModal(false);
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

  const handleToolExecution = (tool: OSINTTool) => {
    // Tool execution handling removed
    console.log('Tool execution:', tool.name);
  };

  const handleAddEntity = (entityData: Partial<Entity>) => {
    // Entity addition handling removed
    console.log('Add entity:', entityData);
    setShowEntityModal(false);
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
    console.log('Ver investigación:', investigation.title);
  };

  const handleEdit = (investigation: Investigation) => {
    console.log('Editar investigación:', investigation.title);
  };

  const handleDelete = (investigation: Investigation) => {
    if (window.confirm(`¿Está seguro de que desea eliminar la investigación "${investigation.title}"?`)) {
      const remove = async () => {
        const res = await apiService.deleteInvestigation(investigation.id);
        if (res.success) {
          await loadInvestigations();
          console.log('Investigación eliminada:', investigation.title);
          return;
        }
        if (maybeHandleAuthExpired(res.message, res.errors)) return;
        console.error('💥 Error al eliminar investigación:', res.message, res.errors);
        setPageError(res.message || 'No se pudo eliminar la investigación');
      };
      void remove();
    }
  };

  const handleWorkspace = (investigation: Investigation) => {
    console.log('🔄 Navegando al workspace para investigación:', investigation.id);
    console.log('🔄 URL de destino:', `/investigations/workspace/${investigation.id}`);
    console.log('🔄 Objeto navigate:', navigate);
    
    try {
      navigate(`/investigations/workspace/${investigation.id}`);
      console.log('✅ Navegación ejecutada correctamente');
    } catch (error) {
      console.error('💥 Error en la navegación:', error);
    }
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
        metadata: {
          target: newInvestigation.target || undefined,
          priority: newInvestigation.priority || 'medium',
          tags: newInvestigation.tags || [],
        }
      } as any);

      if (res.success) {
        setShowModal(false);
        setNewInvestigation({title: '', description: '', status: 'active', priority: 'medium', tags: []});
        await loadInvestigations();
        return;
      }

      if (maybeHandleAuthExpired(res.message, res.errors)) return;
      console.error('💥 Error al crear investigación:', res.message, res.errors);
      setPageError(res.message || 'No se pudo crear la investigación');
    };

    void create();
  };

  const loadInvestigations = async () => {
    console.log('🔄 Cargando investigaciones...');

    try {
      setPageError(null);
      const res = await apiService.getInvestigations();
      if (!res.success) {
        if (maybeHandleAuthExpired(res.message, res.errors)) return;
        console.error('💥 Error al cargar investigaciones:', res.message, res.errors);
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

        return {
          id: inv.id,
          title: inv.name,
          description: inv.description || '',
          status: safeStatus,
          priority: 'medium',
          entities: [],
          createdBy: inv.created_by?.username || 'N/A',
          createdAt: inv.created_at,
          updatedAt: inv.updated_at,
          entitiesCount: inv.entities_count ?? 0,
          toolsUsed: [],
          tags: [],
        };
      });

      setInvestigations(mapped);
      console.log('✅ Investigaciones cargadas correctamente');
      
    } catch (err) {
      console.error('💥 Error al cargar investigaciones:', err);
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
              <Alert variant="dark" className="border border-secondary text-light mb-0">
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
                  <h4 className="text-light mb-0">
                    <i className="bi bi-search me-2"></i>
                    Investigaciones
                  </h4>
                  <Button 
                    variant="outline-light"
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
                <Card bg="dark" border="secondary" className="h-100">
                  <Card.Body className="d-flex align-items-center justify-content-between">
                    <div>
                      <div className="text-secondary small text-uppercase">Total</div>
                      <div className="text-light fs-3 fw-semibold">{investigations.length}</div>
                    </div>
                    <i className="bi bi-search fs-2 text-secondary"></i>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={3}>
                <Card bg="dark" border="secondary" className="h-100">
                  <Card.Body className="d-flex align-items-center justify-content-between">
                    <div>
                      <div className="text-secondary small text-uppercase">Activas</div>
                      <div className="text-light fs-3 fw-semibold">{investigations.filter(i => i.status === 'active' || i.status === 'paused').length}</div>
                    </div>
                    <i className="bi bi-play-circle fs-2 text-secondary"></i>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={3}>
                <Card bg="dark" border="secondary" className="h-100">
                  <Card.Body className="d-flex align-items-center justify-content-between">
                    <div>
                      <div className="text-secondary small text-uppercase">Completadas</div>
                      <div className="text-light fs-3 fw-semibold">{investigations.filter(i => i.status === 'completed').length}</div>
                    </div>
                    <i className="bi bi-check-circle fs-2 text-secondary"></i>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={3}>
                <Card bg="dark" border="secondary" className="h-100">
                  <Card.Body className="d-flex align-items-center justify-content-between">
                    <div>
                      <div className="text-secondary small text-uppercase">Archivadas</div>
                      <div className="text-light fs-3 fw-semibold">{investigations.filter(i => i.status === 'archived').length}</div>
                    </div>
                    <i className="bi bi-archive fs-2 text-secondary"></i>
                  </Card.Body>
                </Card>
              </Col>
            </Row>

        {/* Filtros y Búsqueda */}
        <Row className="mb-4">
          <Col>
            <Card bg="dark" border="secondary">
              <Card.Body>
                <Row className="g-3">
                  <Col md={3}>
                    <InputGroup>
                      <InputGroup.Text className="bg-secondary border-secondary text-light">
                        <i className="bi bi-search"></i>
                      </InputGroup.Text>
                      <Form.Control
                        type="text"
                        placeholder="Buscar investigaciones..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="bg-dark border-secondary text-light"
                      />
                    </InputGroup>
                  </Col>
                  <Col md={2}>
                    <Form.Select
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                      className="bg-dark border-secondary text-light"
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
                      className="bg-dark border-secondary text-light"
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
                      className="bg-dark border-secondary text-light"
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
                      className="bg-dark border-secondary text-light"
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
            <Card bg="dark" border="secondary">
              <Card.Body className="p-0">
                <Table responsive hover variant="dark" className="mb-0">
                  <thead className="bg-secondary">
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
                          <code className="text-secondary">{investigation.target || 'N/A'}</code>
                        </td>
                        <td>
                          <Badge bg={getStatusColor(investigation.status)} className="border border-secondary text-light">
                            {getStatusText(investigation.status)}
                          </Badge>
                        </td>
                        <td>
                          <Badge bg={getPriorityColor(investigation.priority)} className="border border-secondary text-light">
                            {getPriorityText(investigation.priority)}
                          </Badge>
                        </td>
                        <td>
                          <div className="d-flex flex-wrap gap-1">
                            {investigation.toolsUsed?.slice(0, 2).map((tool, index) => (
                              <Badge key={index} bg="dark" className="small border border-secondary text-light">
                                {tool}
                              </Badge>
                            ))}
                            {investigation.toolsUsed && investigation.toolsUsed.length > 2 && (
                              <Badge bg="dark" className="small border border-secondary text-light">
                                +{investigation.toolsUsed.length - 2}
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td>
                          <Badge bg="dark" className="rounded-pill border border-secondary text-light">
                            {investigation.entitiesCount || 0}
                          </Badge>
                        </td>
                        <td className="text-muted">
                          {new Date(investigation.createdAt).toLocaleDateString('es-ES')}
                        </td>
                        <td>
                          <div className="d-flex gap-1">
                            <Button 
                              variant="outline-light" 
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
                            >
                              <i className="bi bi-diagram-3"></i>
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
        <Modal show={selectedTool !== null} onHide={() => setSelectedTool(null)} size="lg" centered>
          <Modal.Header closeButton className="bg-dark border-secondary">
            <Modal.Title className="text-light">
              {selectedTool && (
                <>
                  <i className={`${selectedTool.icon} me-2 text-secondary`}></i>
                  {selectedTool.name}
                </>
              )}
            </Modal.Title>
          </Modal.Header>
          <Modal.Body className="bg-dark text-light">
            {selectedTool && (
              <>
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
            <Button variant="outline-secondary" onClick={() => setSelectedTool(null)}>
              Cancelar
            </Button>
            <Button
              variant="outline-light"
              onClick={() => {
                if (selectedTool) {
                  handleToolExecution(selectedTool);
                  setSelectedTool(null);
                  setToolParameters({});
                }
              }}
            >
              <i className="bi bi-play-fill me-2"></i>
              Ejecutar Herramienta
            </Button>
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
                    <Form.Select className="bg-dark border-secondary text-light">
                      <option value="domain">Dominio</option>
                      <option value="ip">Dirección IP</option>
                      <option value="email">Email</option>
                      <option value="person">Persona</option>
                      <option value="phone">Teléfono</option>
                      <option value="url">URL</option>
                      <option value="organization">Organización</option>
                      <option value="social">Red Social</option>
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
            <Button variant="outline-light" onClick={() => handleAddEntity({})}>
              <i className="bi bi-plus-circle me-2"></i>
              Agregar Entidad
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
                      <i className="bi bi-activity me-2 text-secondary"></i>
                      Estado Inicial
                    </Form.Label>
                    <Form.Select 
                      className="bg-dark border-secondary text-light"
                      value={newInvestigation.status}
                      onChange={(e) => setNewInvestigation(prev => ({...prev, status: e.target.value as 'active' | 'completed' | 'archived'}))}
                    >
                      <option value="active">Activa</option>
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
