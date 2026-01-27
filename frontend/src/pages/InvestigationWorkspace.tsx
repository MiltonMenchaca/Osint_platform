import React, { useState, useEffect } from 'react';
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
  Table,
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
  ZoomIn
} from 'lucide-react';
import type { Investigation, Entity } from '../types';
import EntityForm from '../components/EntityForm';
import Header from '../components/Header';

// Local type definitions
interface OSINTTool {
  id: string;
  name: string;
  description: string;
  category: string;
  parameters: ToolParameter[];
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
    background: #6c757d;
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
    border: 2px solid #212529;
  }
  
  .timeline-marker.system { background: #0d6efd; border-color: #0d6efd; }
  .timeline-marker.osint { background: #198754; border-color: #198754; }
  .timeline-marker.alert { background: #ffc107; border-color: #ffc107; }
  .timeline-marker.critical { background: #dc3545; border-color: #dc3545; }
  .timeline-marker.manual { background: #6f42c1; border-color: #6f42c1; }
  
  .timeline-content {
    background: #2d3748;
    border: 1px solid #4a5568;
    border-radius: 8px;
    padding: 12px;
    margin-left: 10px;
  }
`;

// Mock data para herramientas OSINT
const osintTools: OSINTTool[] = [
  {
    id: 'holehe',
    name: 'Holehe',
    description: 'Verificar si un email está registrado en diferentes sitios web',
    category: 'Email Intelligence',
    parameters: [
      { name: 'email', type: 'string', required: true, description: 'Email a verificar', placeholder: 'ejemplo@dominio.com' },
      { name: 'timeout', type: 'number', required: false, description: 'Timeout en segundos', placeholder: '10' },
      { name: 'only_used', type: 'boolean', required: false, description: 'Solo mostrar sitios donde el email está registrado' }
    ]
  },
  {
    id: 'assetfinder',
    name: 'Assetfinder',
    description: 'Encontrar subdominios relacionados con un dominio',
    category: 'Domain Intelligence',
    parameters: [
      { name: 'domain', type: 'string', required: true, description: 'Dominio objetivo', placeholder: 'ejemplo.com' },
      { name: 'subs_only', type: 'boolean', required: false, description: 'Solo subdominios (no incluir dominio principal)' },
      { name: 'sources', type: 'multiselect', required: false, description: 'Fuentes de datos', options: ['crtsh', 'hackertarget', 'threatcrowd', 'wayback'] }
    ]
  },
  {
    id: 'amass',
    name: 'Amass',
    description: 'Enumeración avanzada de subdominios y mapeo de red',
    category: 'Domain Intelligence',
    parameters: [
      { name: 'domain', type: 'string', required: true, description: 'Dominio objetivo', placeholder: 'ejemplo.com' },
      { name: 'passive', type: 'boolean', required: false, description: 'Solo reconocimiento pasivo' },
      { name: 'brute', type: 'boolean', required: false, description: 'Fuerza bruta de subdominios' }
    ]
  },
  {
    id: 'subfinder',
    name: 'Subfinder',
    description: 'Descubrimiento rápido de subdominios usando fuentes pasivas',
    category: 'Domain Intelligence',
    parameters: [
      { name: 'domain', type: 'string', required: true, description: 'Dominio objetivo', placeholder: 'ejemplo.com' },
      { name: 'silent', type: 'boolean', required: false, description: 'Modo silencioso' },
      { name: 'sources', type: 'multiselect', required: false, description: 'Fuentes específicas', options: ['crtsh', 'virustotal', 'shodan', 'censys'] }
    ]
  },
  {
    id: 'theharvester',
    name: 'TheHarvester',
    description: 'Recopilación de emails, subdominios y hosts desde fuentes públicas',
    category: 'Email Intelligence',
    parameters: [
      { name: 'domain', type: 'string', required: true, description: 'Dominio objetivo', placeholder: 'ejemplo.com' },
      { name: 'source', type: 'select', required: true, description: 'Fuente de datos', options: ['google', 'bing', 'linkedin', 'twitter', 'all'] },
      { name: 'limit', type: 'number', required: false, description: 'Límite de resultados', placeholder: '500' }
    ]
  },
  {
    id: 'recon-ng',
    name: 'Recon-ng',
    description: 'Framework modular de reconocimiento web con múltiples módulos',
    category: 'Web Intelligence',
    parameters: [
      { name: 'target', type: 'string', required: true, description: 'Objetivo', placeholder: 'ejemplo.com' },
      { name: 'module', type: 'select', required: true, description: 'Módulo a ejecutar', options: ['hackertarget', 'shodan_hostname', 'google_site_web', 'bing_domain_web'] },
      { name: 'options', type: 'string', required: false, description: 'Opciones adicionales', placeholder: 'key=value' }
    ]
  },
  {
    id: 'spiderfoot',
    name: 'SpiderFoot',
    description: 'Automatización de reconocimiento OSINT con más de 200 módulos',
    category: 'Comprehensive Intelligence',
    parameters: [
      { name: 'target', type: 'string', required: true, description: 'Objetivo', placeholder: 'ejemplo.com o 192.168.1.1' },
      { name: 'modules', type: 'select', required: true, description: 'Tipo de módulos', options: ['footprint', 'investigate', 'passive', 'all'] },
      { name: 'timeout', type: 'number', required: false, description: 'Timeout en minutos', placeholder: '30' }
    ]
  },
  {
    id: 'maltego',
    name: 'Maltego',
    description: 'Análisis de enlaces y visualización de relaciones entre entidades',
    category: 'Link Analysis',
    parameters: [
      { name: 'entity_type', type: 'select', required: true, description: 'Tipo de entidad', options: ['domain', 'person', 'email', 'phone', 'company'] },
      { name: 'entity_value', type: 'string', required: true, description: 'Valor de la entidad', placeholder: 'Valor de la entidad' },
      { name: 'transform_set', type: 'select', required: false, description: 'Set de transforms', options: ['standard', 'social', 'infrastructure'] }
    ]
  },
  {
    id: 'nmap',
    name: 'Nmap',
    description: 'Escaneo de puertos y detección de servicios',
    category: 'Network Intelligence',
    parameters: [
      { name: 'target', type: 'string', required: true, description: 'IP o rango de IPs', placeholder: '192.168.1.1 o 192.168.1.0/24' },
      { name: 'ports', type: 'string', required: false, description: 'Puertos específicos', placeholder: '80,443,22 o 1-1000' },
      { name: 'scan_type', type: 'select', required: false, description: 'Tipo de escaneo', options: ['TCP SYN (-sS)', 'TCP Connect (-sT)', 'UDP (-sU)', 'Stealth (-sN)'] },
      { name: 'service_detection', type: 'boolean', required: false, description: 'Detección de servicios (-sV)' },
      { name: 'os_detection', type: 'boolean', required: false, description: 'Detección de OS (-O)' },
      { name: 'aggressive', type: 'boolean', required: false, description: 'Escaneo agresivo (-A)' },
      { name: 'timing', type: 'select', required: false, description: 'Plantilla de timing', options: ['T0 (Paranoid)', 'T1 (Sneaky)', 'T2 (Polite)', 'T3 (Normal)', 'T4 (Aggressive)', 'T5 (Insane)'] }
    ]
  },
  {
    id: 'shodan',
    name: 'Shodan',
    description: 'Búsqueda de dispositivos conectados a internet',
    category: 'Network Intelligence',
    parameters: [
      { name: 'query', type: 'string', required: true, description: 'Consulta de búsqueda', placeholder: 'apache, port:80, country:ES' },
      { name: 'country', type: 'string', required: false, description: 'Código de país', placeholder: 'US, ES, FR' },
      { name: 'city', type: 'string', required: false, description: 'Ciudad', placeholder: 'Madrid, Barcelona' },
      { name: 'port', type: 'string', required: false, description: 'Puerto específico', placeholder: '80, 443, 22' },
      { name: 'limit', type: 'number', required: false, description: 'Límite de resultados', placeholder: '100' },
      { name: 'facets', type: 'multiselect', required: false, description: 'Facetas adicionales', options: ['country', 'city', 'port', 'org', 'domain', 'product'] }
    ]
  }
];

// Mock data para investigación actual
const mockInvestigation: Investigation = {
  id: '1',
  title: 'Operación CryptoShadow - Fraude de Inversión Cripto',
  description: 'Investigación de esquema Ponzi que utiliza criptomonedas para defraudar inversores. Pérdidas estimadas: $2.3M USD. Víctimas reportadas: 847 personas en 15 países.',
  status: 'active',
  priority: 'high',
  createdAt: '2024-01-10T08:00:00Z',
  updatedAt: '2024-01-15T16:45:00Z',
  entities: [],
  createdBy: 'admin'
};

// Mock data para métricas en tiempo real
const mockMetrics = {
  threatLevel: 8.5,
  riskScore: 7.2,
  aiConfidence: 94,
  totalEntities: 47,
  activeConnections: 23,
  suspiciousActivities: 12,
  geographicSpread: 15,
  timelineEvents: 156,
  dataPoints: 2847,
  correlations: 34
};

type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed';

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
  const [investigation] = useState<Investigation>(mockInvestigation);
  const [entities, setEntities] = useState<Entity[]>([
    {
      id: '1',
      name: 'Marcus Blackwood Email',
      type: 'email',
      value: 'marcus.blackwood@cryptofinance.io',
      description: 'CEO de CryptoFinance - Email principal identificado en investigación de fraude',
      created_at: '2024-01-15T10:30:00Z',
      properties: { 
        verified: true, 
        source: 'manual',
        risk_level: 'high',
        last_activity: '2024-01-14T18:45:00Z',
        associated_platforms: ['LinkedIn', 'Twitter', 'Telegram']
      }
    },
    {
      id: '2',
      name: 'CryptoFinance Domain',
      type: 'domain',
      value: 'cryptofinance.io',
      description: 'Dominio principal - Registrado bajo identidad falsa',
      created_at: '2024-01-15T10:35:00Z',
      properties: { 
        registrar: 'Namecheap',
        creation_date: '2023-08-15',
        expiry_date: '2025-08-15',
        privacy_protection: true,
        dns_servers: ['ns1.namecheap.com', 'ns2.namecheap.com'],
        ssl_certificate: 'Let\'s Encrypt'
      }
    },
    {
      id: '3',
      name: 'DigitalOcean Server',
      type: 'ip',
      value: '185.199.108.153',
      description: 'Servidor de hosting - Ubicado en Países Bajos',
      created_at: '2024-01-15T10:40:00Z',
      properties: { 
        country: 'NL',
        city: 'Amsterdam',
        organization: 'DigitalOcean LLC',
        open_ports: [80, 443, 22, 3306],
        services: ['nginx/1.18.0', 'MySQL 8.0', 'OpenSSH 8.2'],
        threat_score: 7.2
      }
    }
  ]);
  
  const [selectedTool, setSelectedTool] = useState<OSINTTool | null>(null);
  const [toolParameters, setToolParameters] = useState<Record<string, any>>({});
  const [executions, setExecutions] = useState<ToolExecutionState[]>([]);
  const [executionQueue, setExecutionQueue] = useState<string[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [entityFilter, setEntityFilter] = useState('');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [entitySourceFilter, setEntitySourceFilter] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [showEntityForm, setShowEntityForm] = useState(false);
  const [activePanel, setActivePanel] = useState<'overview' | 'analysis' | 'timeline' | 'geography' | 'network'>('overview');
  const [showOSINTPanel, setShowOSINTPanel] = useState(false);

  // Verificar redirección automática
  useEffect(() => {
    if (!id) {
      navigate('/investigations');
      return;
    }
  }, [id, navigate]);

  // Función para validar formulario
  const isFormValid = () => {
    if (!selectedTool) return false;
    
    const requiredParams = selectedTool.parameters.filter((p: any) => p.required);
    return requiredParams.every((param: any) => {
      const value = toolParameters[param.name];
      return value !== undefined && value !== null && value !== '';
    });
  };

  // Simular ejecución de herramienta
  const executeOSINTTool = async (tool?: OSINTTool) => {
    const targetTool = tool || selectedTool;
    
    if (!targetTool) {
      alert('Por favor selecciona una herramienta OSINT');
      return;
    }

    if (!isFormValid()) {
      alert('Por favor completa todos los campos requeridos correctamente');
      return;
    }

    const executionId = Date.now().toString();
    
    setExecutionQueue(prev => [...prev, executionId]);
    
    const execution: ToolExecutionState = {
      id: executionId,
      toolId: targetTool.id,
      status: 'pending',
      progress: 0,
      startTime: new Date()
    };

    setExecutions(prev => [...prev, execution]);
    setToolParameters({});
    setSelectedTool(null);

    if (!isExecuting) {
      processExecutionQueue();
    }
  };

  const processExecutionQueue = async () => {
    if (isExecuting || executionQueue.length === 0) return;
    
    setIsExecuting(true);
    
    while (executionQueue.length > 0) {
      const currentId = executionQueue[0];
      setExecutionQueue(prev => prev.slice(1));
      
      setExecutions(prev => prev.map(exec => 
        exec.id === currentId ? { ...exec, status: 'running' } : exec
      ));
      
      await simulateToolExecution(currentId);
    }
    
    setIsExecuting(false);
  };

  const simulateToolExecution = (executionId: string): Promise<void> => {
    return new Promise((resolve) => {
      const execution = executions.find(e => e.id === executionId);
      if (!execution) {
        resolve();
        return;
      }
      
      const duration = Math.random() * 8000 + 2000;
      const steps = 20;
      const stepDuration = duration / steps;
      
      let currentStep = 0;
      
      const interval = setInterval(() => {
        currentStep++;
        const progress = Math.min((currentStep / steps) * 100, 100);
        
        setExecutions(prev => prev.map(exec => {
          if (exec.id === executionId) {
            if (progress >= 100) {
              clearInterval(interval);
              resolve();
              return {
                ...exec,
                status: Math.random() > 0.1 ? 'completed' : 'failed',
                progress: 100,
                endTime: new Date(),
                results: Math.random() > 0.1 ? [
                  { type: 'info', message: 'Ejecución completada exitosamente' },
                  { type: 'data', count: Math.floor(Math.random() * 20) + 1 }
                ] : undefined,
                error: Math.random() > 0.1 ? undefined : 'Error simulado en la ejecución'
              };
            }
            return { ...exec, progress };
          }
          return exec;
        }));
      }, stepDuration);
    });
  };

  const handleDeleteEntity = (entityId: string) => {
    setEntities(prev => prev.filter(e => e.id !== entityId));
    setShowDeleteConfirm(null);
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
    const matchesSearch = (entity.value && entity.value.toLowerCase().includes(entityFilter.toLowerCase())) ||
                         (entity.description && entity.description.toLowerCase().includes(entityFilter.toLowerCase()));
    const matchesType = !entityTypeFilter || entity.type === entityTypeFilter;
    const matchesSource = !entitySourceFilter || entity.properties?.source === entitySourceFilter;
    
    return matchesSearch && matchesType && matchesSource;
  });

  const getStatusVariant = (status: ExecutionStatus) => {
    switch (status) {
      case 'completed': return 'success';
      case 'running': return 'primary';
      case 'failed': return 'danger';
      default: return 'secondary';
    }
  };

  const getStatusIcon = (status: ExecutionStatus) => {
    switch (status) {
      case 'completed': return <CheckCircle size={16} />;
      case 'running': return <Spinner animation="border" size="sm" />;
      case 'failed': return <AlertCircle size={16} />;
      default: return <Clock size={16} />;
    }
  };

  // Mock user data for Header component
  const mockUser = {
    id: '1',
    username: 'admin',
    email: 'admin@osint.local',
    role: 'admin' as const,
    isActive: true,
    createdAt: new Date().toISOString()
  };

  const handleLogout = () => {
    // Handle logout logic here
    navigate('/login');
  };

  return (
    <div className="bg-dark text-light min-vh-100">
      <Header user={mockUser} onLogout={handleLogout} />
      
      {/* Header de la investigación */}
      <Container fluid className="py-3 border-bottom border-secondary">
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
                <h2 className="h4 mb-1 text-light">{investigation.title}</h2>
                <div className="d-flex align-items-center gap-3 text-muted small">
                  <span>{investigation.case_number} • {investigation.jurisdiction}</span>
                  <Badge bg={investigation.priority === 'high' ? 'danger' : investigation.priority === 'medium' ? 'warning' : 'success'}>
                    {investigation.priority === 'high' ? 'CRÍTICA' : investigation.priority === 'medium' ? 'ACTIVA' : 'BAJA'}
                  </Badge>
                  <Button variant="outline-primary" size="sm" className="d-flex align-items-center gap-1">
                    <Eye size={14} />
                    Ver en Grafo
                  </Button>
                </div>
              </div>
            </div>
          </Col>
          
          <Col xs="auto">
            <div className="text-end">
              <div className="h5 mb-0 text-danger">{investigation.estimated_loss}</div>
              <div className="small text-muted">{investigation.victim_count} víctimas</div>
            </div>
          </Col>
        </Row>
      </Container>

      {/* Panel de métricas en tiempo real */}
      <Container fluid className="py-3 bg-dark">
          <Row className="g-4 justify-content-center">
            <Col md={3}>
              <Card className="bg-dark border-secondary h-100">
                <Card.Body className="text-center py-4">
                  <div className="d-flex align-items-center justify-content-center mb-3">
                    <Shield className="me-2" size={24} style={{color: '#dc3545'}} />
                    <span className="small" style={{color: '#6c757d'}}>CRÍTICO</span>
                  </div>
                  <div className="h3 mb-1" style={{color: '#dc3545'}}>{mockMetrics.threatLevel}/10</div>
                  <div className="small text-muted">Nivel de Amenaza</div>
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={3}>
              <Card className="bg-dark border-secondary h-100">
                <Card.Body className="text-center py-4">
                  <div className="d-flex align-items-center justify-content-center mb-3">
                    <Target className="me-2" size={24} style={{color: '#fd7e14'}} />
                    <span className="small" style={{color: '#6c757d'}}>ALTO</span>
                  </div>
                  <div className="h3 mb-1" style={{color: '#fd7e14'}}>{mockMetrics.riskScore}%</div>
                  <div className="small text-muted">Puntuación de Riesgo</div>
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={3}>
              <Card className="bg-dark border-secondary h-100">
                <Card.Body className="text-center py-4">
                  <div className="d-flex align-items-center justify-content-center mb-3">
                    <Database className="me-2" size={24} style={{color: '#0dcaf0'}} />
                    <span className="small" style={{color: '#6c757d'}}>+{entities.length - 10}</span>
                  </div>
                  <div className="h3 mb-1" style={{color: '#0dcaf0'}}>{entities.length}</div>
                  <div className="small text-muted">Entidades Totales</div>
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={3}>
              <Card className="bg-dark border-secondary h-100">
                <Card.Body className="text-center py-4">
                  <div className="d-flex align-items-center justify-content-center mb-3">
                    <Activity className="me-2" size={24} style={{color: '#ffc107'}} />
                    <span className="small" style={{color: '#6c757d'}}>ACTIVO</span>
                  </div>
                  <div className="h3 mb-1" style={{color: '#ffc107'}}>{mockMetrics.suspiciousActivities}</div>
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
                    variant="outline-success" 
                    size="sm" 
                    className="d-flex align-items-center gap-1"
                  >
                    <RefreshCw size={14} />
                    Auto-refresh
                  </Button>
                  <span className="small text-muted">Últimas actualizaciones</span>
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
              <Nav variant="tabs" className="mb-3 border-bottom border-secondary">
                <Nav.Item>
                  <Nav.Link eventKey="overview" className="text-light">
                    <Home size={16} className="me-2" />
                    Vista General
                  </Nav.Link>
                </Nav.Item>
                <Nav.Item>
                  <Nav.Link eventKey="analysis" className="text-light">
                    <BarChart3 size={16} className="me-2" />
                    Análisis de Amenazas
                  </Nav.Link>
                </Nav.Item>
                <Nav.Item>
                  <Nav.Link eventKey="timeline" className="text-light">
                    <Calendar size={16} className="me-2" />
                    Línea de Tiempo
                  </Nav.Link>
                </Nav.Item>
                <Nav.Item>
                  <Nav.Link eventKey="geography" className="text-light">
                    <MapPin size={16} className="me-2" />
                    Análisis Geográfico
                  </Nav.Link>
                </Nav.Item>
                <Nav.Item>
                  <Nav.Link eventKey="network" className="text-light">
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
                      <Card className="bg-dark border-secondary h-100">
                        <Card.Header className="bg-dark border-secondary d-flex justify-content-between align-items-center">
                          <h6 className="mb-0 text-light">Entidades ({filteredEntities.length})</h6>
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
                            <div className="p-3 border-bottom border-secondary">
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
                              <InputGroup.Text className="bg-dark border-secondary text-light">
                                <Search size={14} />
                              </InputGroup.Text>
                              <Form.Control
                                placeholder="Buscar entidades..."
                                value={entityFilter}
                                onChange={(e) => setEntityFilter(e.target.value)}
                                className="bg-dark border-secondary text-light"
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
                                  <ListGroup.Item key={entity.id} className="bg-dark border-secondary text-light">
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
                                        <Dropdown.Menu className="bg-dark border-secondary">
                                          <Dropdown.Item 
                                            className="text-light" 
                                            onClick={() => handleEditEntity(entity)}
                                          >
                                            <Edit size={14} className="me-2" />
                                            Editar
                                          </Dropdown.Item>
                                          <Dropdown.Item 
                                            className="text-danger" 
                                            onClick={() => setShowDeleteConfirm(entity.id)}
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
                      <Card className="bg-dark border-secondary h-100">
                        <Card.Header className="bg-dark border-secondary d-flex justify-content-between align-items-center">
                          <h6 className="mb-0 text-light">Ejecuciones OSINT ({executions.length})</h6>
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
                                  return (
                                    <Card key={execution.id} className="bg-dark border-secondary mb-3">
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
                                            <h6 className="mb-0 text-light small">{tool?.name}</h6>
                                          </div>
                                          <Badge bg={getStatusVariant(execution.status)} className="small">
                                            {getStatusIcon(execution.status)}
                                            <span className="ms-1">
                                              {execution.status === 'completed' ? 'Completado' :
                                               execution.status === 'running' ? 'Ejecutando' :
                                               execution.status === 'failed' ? 'Fallido' : 'Pendiente'}
                                            </span>
                                          </Badge>
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
                  </Row>
                </Tab.Pane>
                
                <Tab.Pane eventKey="analysis">
                  <Row>
                    <Col md={6}>
                      <Card className="bg-dark border-secondary mb-3">
                        <Card.Header className="bg-dark border-secondary">
                          <h6 className="mb-0 text-light">Nivel de Amenaza por Categoría</h6>
                        </Card.Header>
                        <Card.Body>
                          <div className="mb-3">
                            <div className="d-flex justify-content-between mb-1">
                              <span className="small text-muted">Malware</span>
                              <span className="small text-danger">Alto (85%)</span>
                            </div>
                            <ProgressBar variant="danger" now={85} style={{ height: '8px' }} />
                          </div>
                          <div className="mb-3">
                            <div className="d-flex justify-content-between mb-1">
                              <span className="small text-muted">Phishing</span>
                              <span className="small text-warning">Medio (65%)</span>
                            </div>
                            <ProgressBar variant="warning" now={65} style={{ height: '8px' }} />
                          </div>
                          <div className="mb-3">
                            <div className="d-flex justify-content-between mb-1">
                              <span className="small text-muted">Botnet</span>
                              <span className="small text-info">Bajo (30%)</span>
                            </div>
                            <ProgressBar variant="info" now={30} style={{ height: '8px' }} />
                          </div>
                          <div className="mb-3">
                            <div className="d-flex justify-content-between mb-1">
                              <span className="small text-muted">APT</span>
                              <span className="small text-danger">Crítico (95%)</span>
                            </div>
                            <ProgressBar variant="danger" now={95} style={{ height: '8px' }} />
                          </div>
                        </Card.Body>
                      </Card>
                    </Col>
                    <Col md={6}>
                      <Card className="bg-dark border-secondary mb-3">
                        <Card.Header className="bg-dark border-secondary">
                          <h6 className="mb-0 text-light">Indicadores de Compromiso (IoCs)</h6>
                        </Card.Header>
                        <Card.Body>
                          <ListGroup variant="flush">
                            <ListGroup.Item className="bg-dark border-secondary text-light d-flex justify-content-between">
                              <span className="small">IPs Maliciosas</span>
                              <Badge bg="danger">12</Badge>
                            </ListGroup.Item>
                            <ListGroup.Item className="bg-dark border-secondary text-light d-flex justify-content-between">
                              <span className="small">Dominios Sospechosos</span>
                              <Badge bg="warning">8</Badge>
                            </ListGroup.Item>
                            <ListGroup.Item className="bg-dark border-secondary text-light d-flex justify-content-between">
                              <span className="small">Hashes Maliciosos</span>
                              <Badge bg="danger">15</Badge>
                            </ListGroup.Item>
                            <ListGroup.Item className="bg-dark border-secondary text-light d-flex justify-content-between">
                              <span className="small">URLs Phishing</span>
                              <Badge bg="warning">6</Badge>
                            </ListGroup.Item>
                          </ListGroup>
                        </Card.Body>
                      </Card>
                    </Col>
                  </Row>
                  <Card className="bg-dark border-secondary">
                    <Card.Header className="bg-dark border-secondary">
                      <h6 className="mb-0 text-light">Análisis de Riesgo Detallado</h6>
                    </Card.Header>
                    <Card.Body>
                      <Table variant="dark" size="sm">
                        <thead>
                          <tr>
                            <th>Entidad</th>
                            <th>Tipo</th>
                            <th>Nivel de Riesgo</th>
                            <th>Última Actividad</th>
                            <th>Acciones</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td>192.168.1.100</td>
                            <td><Badge bg="info">IP</Badge></td>
                            <td><Badge bg="danger">Crítico</Badge></td>
                            <td>Hace 2 horas</td>
                            <td><Button size="sm" variant="outline-primary">Analizar</Button></td>
                          </tr>
                          <tr>
                            <td>malicious-domain.com</td>
                            <td><Badge bg="warning">Dominio</Badge></td>
                            <td><Badge bg="warning">Alto</Badge></td>
                            <td>Hace 1 día</td>
                            <td><Button size="sm" variant="outline-primary">Analizar</Button></td>
                          </tr>
                          <tr>
                            <td>suspicious@email.com</td>
                            <td><Badge bg="success">Email</Badge></td>
                            <td><Badge bg="info">Medio</Badge></td>
                            <td>Hace 3 días</td>
                            <td><Button size="sm" variant="outline-primary">Analizar</Button></td>
                          </tr>
                        </tbody>
                      </Table>
                    </Card.Body>
                  </Card>
                </Tab.Pane>
                
                <Tab.Pane eventKey="timeline">
                  <Row>
                    <Col md={8}>
                      <Card className="bg-dark border-secondary">
                        <Card.Header className="bg-dark border-secondary d-flex justify-content-between align-items-center">
                          <h6 className="mb-0 text-light">Cronología de Eventos</h6>
                          <Form.Select size="sm" style={{ width: 'auto' }} className="bg-dark text-light border-secondary">
                            <option>Últimas 24 horas</option>
                            <option>Última semana</option>
                            <option>Último mes</option>
                            <option>Todo el tiempo</option>
                          </Form.Select>
                        </Card.Header>
                        <Card.Body>
                          <div className="timeline">
                            <div className="timeline-item mb-4">
                              <div className="timeline-marker bg-success"></div>
                              <div className="timeline-content">
                                <div className="d-flex justify-content-between align-items-start mb-2">
                                  <h6 className="text-light mb-1">Investigación Iniciada</h6>
                                  <small className="text-muted">Hace 2 días</small>
                                </div>
                                <p className="small text-muted mb-1">Se creó la investigación y se agregaron las primeras entidades objetivo.</p>
                                <Badge bg="success" className="small">Sistema</Badge>
                              </div>
                            </div>
                            
                            <div className="timeline-item mb-4">
                              <div className="timeline-marker bg-primary"></div>
                              <div className="timeline-content">
                                <div className="d-flex justify-content-between align-items-start mb-2">
                                  <h6 className="text-light mb-1">Escaneo Nmap Completado</h6>
                                  <small className="text-muted">Hace 1 día</small>
                                </div>
                                <p className="small text-muted mb-1">Se identificaron 15 puertos abiertos en el objetivo 192.168.1.100</p>
                                <Badge bg="primary" className="small">OSINT</Badge>
                              </div>
                            </div>
                            
                            <div className="timeline-item mb-4">
                              <div className="timeline-marker bg-warning"></div>
                              <div className="timeline-content">
                                <div className="d-flex justify-content-between align-items-start mb-2">
                                  <h6 className="text-light mb-1">Amenaza Detectada</h6>
                                  <small className="text-muted">Hace 18 horas</small>
                                </div>
                                <p className="small text-muted mb-1">Se detectó actividad sospechosa en malicious-domain.com</p>
                                <Badge bg="warning" className="small">Alerta</Badge>
                              </div>
                            </div>
                            
                            <div className="timeline-item mb-4">
                              <div className="timeline-marker bg-info"></div>
                              <div className="timeline-content">
                                <div className="d-flex justify-content-between align-items-start mb-2">
                                  <h6 className="text-light mb-1">Análisis TheHarvester</h6>
                                  <small className="text-muted">Hace 12 horas</small>
                                </div>
                                <p className="small text-muted mb-1">Se recopilaron 25 emails y 8 subdominios del dominio objetivo</p>
                                <Badge bg="info" className="small">OSINT</Badge>
                              </div>
                            </div>
                            
                            <div className="timeline-item mb-4">
                              <div className="timeline-marker bg-danger"></div>
                              <div className="timeline-content">
                                <div className="d-flex justify-content-between align-items-start mb-2">
                                  <h6 className="text-light mb-1">IoC Crítico Identificado</h6>
                                  <small className="text-muted">Hace 6 horas</small>
                                </div>
                                <p className="small text-muted mb-1">Hash malicioso confirmado en base de datos de amenazas</p>
                                <Badge bg="danger" className="small">Crítico</Badge>
                              </div>
                            </div>
                            
                            <div className="timeline-item">
                              <div className="timeline-marker bg-secondary"></div>
                              <div className="timeline-content">
                                <div className="d-flex justify-content-between align-items-start mb-2">
                                  <h6 className="text-light mb-1">Entidad Agregada</h6>
                                  <small className="text-muted">Hace 2 horas</small>
                                </div>
                                <p className="small text-muted mb-1">Nueva IP sospechosa agregada para análisis: 10.0.0.50</p>
                                <Badge bg="secondary" className="small">Manual</Badge>
                              </div>
                            </div>
                          </div>
                        </Card.Body>
                      </Card>
                    </Col>
                    <Col md={4}>
                      <Card className="bg-dark border-secondary mb-3">
                        <Card.Header className="bg-dark border-secondary">
                          <h6 className="mb-0 text-light">Estadísticas de Actividad</h6>
                        </Card.Header>
                        <Card.Body>
                          <div className="mb-3">
                            <div className="d-flex justify-content-between mb-1">
                              <span className="small text-muted">Eventos Hoy</span>
                              <span className="small text-light">8</span>
                            </div>
                            <div className="d-flex justify-content-between mb-1">
                              <span className="small text-muted">Esta Semana</span>
                              <span className="small text-light">24</span>
                            </div>
                            <div className="d-flex justify-content-between mb-1">
                              <span className="small text-muted">Total</span>
                              <span className="small text-light">156</span>
                            </div>
                          </div>
                        </Card.Body>
                      </Card>
                      
                      <Card className="bg-dark border-secondary">
                        <Card.Header className="bg-dark border-secondary">
                          <h6 className="mb-0 text-light">Filtros</h6>
                        </Card.Header>
                        <Card.Body>
                          <Form.Check 
                            type="checkbox" 
                            label="Eventos del Sistema" 
                            className="text-light mb-2" 
                            defaultChecked
                          />
                          <Form.Check 
                            type="checkbox" 
                            label="Herramientas OSINT" 
                            className="text-light mb-2" 
                            defaultChecked
                          />
                          <Form.Check 
                            type="checkbox" 
                            label="Alertas de Seguridad" 
                            className="text-light mb-2" 
                            defaultChecked
                          />
                          <Form.Check 
                            type="checkbox" 
                            label="Acciones Manuales" 
                            className="text-light" 
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
                      <Card className="bg-dark border-secondary">
                        <Card.Header className="bg-dark border-secondary d-flex justify-content-between align-items-center">
                          <h6 className="mb-0 text-light">Mapa de Amenazas Globales</h6>
                          <div className="d-flex gap-2">
                            <Form.Select size="sm" style={{ width: 'auto' }} className="bg-dark text-light border-secondary">
                              <option>Todas las amenazas</option>
                              <option>IPs maliciosas</option>
                              <option>Dominios sospechosos</option>
                              <option>Ataques recientes</option>
                            </Form.Select>
                            <Button variant="outline-secondary" size="sm">
                              <RefreshCw size={14} />
                            </Button>
                          </div>
                        </Card.Header>
                        <Card.Body>
                          <div className="position-relative" style={{ height: '400px', backgroundColor: '#1a1a1a', borderRadius: '8px' }}>
                            <div className="position-absolute top-50 start-50 translate-middle text-center">
                              <MapPin size={48} className="mb-3 text-muted opacity-50" />
                              <h6 className="text-muted">Mapa Interactivo</h6>
                              <p className="small text-muted">Integración con servicio de mapas en desarrollo</p>
                            </div>
                            
                            {/* Simulación de marcadores en el mapa */}
                            <div className="position-absolute" style={{ top: '20%', left: '15%' }}>
                              <div className="bg-danger rounded-circle" style={{ width: '12px', height: '12px' }} title="Rusia - 15 amenazas"></div>
                            </div>
                            <div className="position-absolute" style={{ top: '35%', left: '25%' }}>
                              <div className="bg-warning rounded-circle" style={{ width: '8px', height: '8px' }} title="China - 8 amenazas"></div>
                            </div>
                            <div className="position-absolute" style={{ top: '45%', left: '45%' }}>
                              <div className="bg-danger rounded-circle" style={{ width: '10px', height: '10px' }} title="Irán - 12 amenazas"></div>
                            </div>
                            <div className="position-absolute" style={{ top: '60%', left: '70%' }}>
                              <div className="bg-warning rounded-circle" style={{ width: '6px', height: '6px' }} title="Brasil - 4 amenazas"></div>
                            </div>
                          </div>
                        </Card.Body>
                      </Card>
                    </Col>
                    <Col md={4}>
                      <Card className="bg-dark border-secondary mb-3">
                        <Card.Header className="bg-dark border-secondary">
                          <h6 className="mb-0 text-light">Top Países por Amenazas</h6>
                        </Card.Header>
                        <Card.Body>
                          <div className="mb-3">
                            <div className="d-flex justify-content-between align-items-center mb-2">
                              <div className="d-flex align-items-center">
                                <div className="bg-danger rounded-circle me-2" style={{ width: '8px', height: '8px' }}></div>
                                <span className="small text-light">Rusia</span>
                              </div>
                              <span className="small text-muted">15 (38%)</span>
                            </div>
                            <div className="progress mb-3" style={{ height: '4px' }}>
                              <div className="progress-bar bg-danger" style={{ width: '38%' }}></div>
                            </div>
                            
                            <div className="d-flex justify-content-between align-items-center mb-2">
                              <div className="d-flex align-items-center">
                                <div className="bg-danger rounded-circle me-2" style={{ width: '8px', height: '8px' }}></div>
                                <span className="small text-light">Irán</span>
                              </div>
                              <span className="small text-muted">12 (30%)</span>
                            </div>
                            <div className="progress mb-3" style={{ height: '4px' }}>
                              <div className="progress-bar bg-danger" style={{ width: '30%' }}></div>
                            </div>
                            
                            <div className="d-flex justify-content-between align-items-center mb-2">
                              <div className="d-flex align-items-center">
                                <div className="bg-warning rounded-circle me-2" style={{ width: '8px', height: '8px' }}></div>
                                <span className="small text-light">China</span>
                              </div>
                              <span className="small text-muted">8 (20%)</span>
                            </div>
                            <div className="progress mb-3" style={{ height: '4px' }}>
                              <div className="progress-bar bg-warning" style={{ width: '20%' }}></div>
                            </div>
                            
                            <div className="d-flex justify-content-between align-items-center mb-2">
                              <div className="d-flex align-items-center">
                                <div className="bg-warning rounded-circle me-2" style={{ width: '8px', height: '8px' }}></div>
                                <span className="small text-light">Brasil</span>
                              </div>
                              <span className="small text-muted">4 (10%)</span>
                            </div>
                            <div className="progress" style={{ height: '4px' }}>
                              <div className="progress-bar bg-warning" style={{ width: '10%' }}></div>
                            </div>
                          </div>
                        </Card.Body>
                      </Card>
                      
                      <Card className="bg-dark border-secondary mb-3">
                        <Card.Header className="bg-dark border-secondary">
                          <h6 className="mb-0 text-light">Ubicaciones Recientes</h6>
                        </Card.Header>
                        <Card.Body>
                          <div className="mb-2">
                            <div className="d-flex justify-content-between align-items-center mb-1">
                              <span className="small text-light">185.220.101.42</span>
                              <Badge bg="danger" className="small">Alto</Badge>
                            </div>
                            <div className="small text-muted">Moscú, Rusia</div>
                          </div>
                          <hr className="border-secondary" />
                          
                          <div className="mb-2">
                            <div className="d-flex justify-content-between align-items-center mb-1">
                              <span className="small text-light">malicious-domain.com</span>
                              <Badge bg="warning" className="small">Medio</Badge>
                            </div>
                            <div className="small text-muted">Teherán, Irán</div>
                          </div>
                          <hr className="border-secondary" />
                          
                          <div className="mb-2">
                            <div className="d-flex justify-content-between align-items-center mb-1">
                              <span className="small text-light">123.45.67.89</span>
                              <Badge bg="warning" className="small">Medio</Badge>
                            </div>
                            <div className="small text-muted">Beijing, China</div>
                          </div>
                        </Card.Body>
                      </Card>
                      
                      <Card className="bg-dark border-secondary">
                        <Card.Header className="bg-dark border-secondary">
                          <h6 className="mb-0 text-light">Estadísticas Geográficas</h6>
                        </Card.Header>
                        <Card.Body>
                          <div className="d-flex justify-content-between mb-2">
                            <span className="small text-muted">Países Únicos</span>
                            <span className="small text-light">12</span>
                          </div>
                          <div className="d-flex justify-content-between mb-2">
                            <span className="small text-muted">Ciudades Únicas</span>
                            <span className="small text-light">28</span>
                          </div>
                          <div className="d-flex justify-content-between mb-2">
                            <span className="small text-muted">IPs Geolocalizadas</span>
                            <span className="small text-light">156/180</span>
                          </div>
                          <div className="d-flex justify-content-between">
                            <span className="small text-muted">Precisión Promedio</span>
                            <span className="small text-light">87%</span>
                          </div>
                        </Card.Body>
                      </Card>
                    </Col>
                  </Row>
                </Tab.Pane>
                
                <Tab.Pane eventKey="network">
                  <Row>
                    <Col md={8}>
                      <Card className="bg-dark border-secondary">
                        <Card.Header className="bg-dark border-secondary d-flex justify-content-between align-items-center">
                          <h6 className="mb-0 text-light">Grafo de Relaciones</h6>
                          <div className="d-flex gap-2">
                            <Form.Select size="sm" style={{ width: 'auto' }} className="bg-dark text-light border-secondary">
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
                              <h6 className="text-muted">Visualización de Red</h6>
                              <p className="small text-muted">Gráfico interactivo de conexiones</p>
                            </div>
                            
                            {/* Simulación de nodos y conexiones */}
                            <svg width="100%" height="100%" className="position-absolute top-0 start-0">
                              {/* Conexiones */}
                              <line x1="150" y1="100" x2="300" y2="150" stroke="#6c757d" strokeWidth="2" opacity="0.6" />
                              <line x1="300" y1="150" x2="450" y2="120" stroke="#dc3545" strokeWidth="3" opacity="0.8" />
                              <line x1="300" y1="150" x2="350" y2="280" stroke="#ffc107" strokeWidth="2" opacity="0.6" />
                              <line x1="150" y1="100" x2="200" y2="250" stroke="#28a745" strokeWidth="2" opacity="0.6" />
                              <line x1="450" y1="120" x2="500" y2="300" stroke="#17a2b8" strokeWidth="2" opacity="0.6" />
                              
                              {/* Nodos principales */}
                              <circle cx="150" cy="100" r="15" fill="#28a745" opacity="0.9" />
                              <circle cx="300" cy="150" r="20" fill="#dc3545" opacity="0.9" />
                              <circle cx="450" cy="120" r="12" fill="#ffc107" opacity="0.9" />
                              <circle cx="350" cy="280" r="10" fill="#17a2b8" opacity="0.9" />
                              <circle cx="200" cy="250" r="8" fill="#6c757d" opacity="0.9" />
                              <circle cx="500" cy="300" r="8" fill="#6f42c1" opacity="0.9" />
                              
                              {/* Etiquetas */}
                              <text x="150" y="85" textAnchor="middle" fill="#fff" fontSize="10">Target IP</text>
                              <text x="300" y="135" textAnchor="middle" fill="#fff" fontSize="10">Malicious</text>
                              <text x="450" y="105" textAnchor="middle" fill="#fff" fontSize="10">Suspicious</text>
                              <text x="350" y="295" textAnchor="middle" fill="#fff" fontSize="8">Related</text>
                              <text x="200" y="265" textAnchor="middle" fill="#fff" fontSize="8">Clean</text>
                              <text x="500" y="315" textAnchor="middle" fill="#fff" fontSize="8">Unknown</text>
                            </svg>
                          </div>
                        </Card.Body>
                      </Card>
                    </Col>
                    <Col md={4}>
                      <Card className="bg-dark border-secondary mb-3">
                        <Card.Header className="bg-dark border-secondary">
                          <h6 className="mb-0 text-light">Métricas de Red</h6>
                        </Card.Header>
                        <Card.Body>
                          <div className="mb-3">
                            <div className="d-flex justify-content-between mb-2">
                              <span className="small text-muted">Nodos Totales</span>
                              <span className="small text-light">24</span>
                            </div>
                            <div className="d-flex justify-content-between mb-2">
                              <span className="small text-muted">Conexiones</span>
                              <span className="small text-light">18</span>
                            </div>
                            <div className="d-flex justify-content-between mb-2">
                              <span className="small text-muted">Densidad</span>
                              <span className="small text-light">0.65</span>
                            </div>
                            <div className="d-flex justify-content-between">
                              <span className="small text-muted">Componentes</span>
                              <span className="small text-light">3</span>
                            </div>
                          </div>
                        </Card.Body>
                      </Card>
                      
                      <Card className="bg-dark border-secondary mb-3">
                        <Card.Header className="bg-dark border-secondary">
                          <h6 className="mb-0 text-light">Nodos Centrales</h6>
                        </Card.Header>
                        <Card.Body>
                          <div className="mb-2">
                            <div className="d-flex justify-content-between align-items-center mb-1">
                              <div className="d-flex align-items-center">
                                <div className="bg-danger rounded-circle me-2" style={{ width: '8px', height: '8px' }}></div>
                                <span className="small text-light">185.220.101.42</span>
                              </div>
                              <Badge bg="danger" className="small">Hub</Badge>
                            </div>
                            <div className="small text-muted">12 conexiones</div>
                          </div>
                          <hr className="border-secondary" />
                          
                          <div className="mb-2">
                            <div className="d-flex justify-content-between align-items-center mb-1">
                              <div className="d-flex align-items-center">
                                <div className="bg-warning rounded-circle me-2" style={{ width: '8px', height: '8px' }}></div>
                                <span className="small text-light">malicious-domain.com</span>
                              </div>
                              <Badge bg="warning" className="small">Bridge</Badge>
                            </div>
                            <div className="small text-muted">8 conexiones</div>
                          </div>
                          <hr className="border-secondary" />
                          
                          <div className="mb-2">
                            <div className="d-flex justify-content-between align-items-center mb-1">
                              <div className="d-flex align-items-center">
                                <div className="bg-success rounded-circle me-2" style={{ width: '8px', height: '8px' }}></div>
                                <span className="small text-light">192.168.1.100</span>
                              </div>
                              <Badge bg="success" className="small">Target</Badge>
                            </div>
                            <div className="small text-muted">6 conexiones</div>
                          </div>
                        </Card.Body>
                      </Card>
                      
                      <Card className="bg-dark border-secondary">
                        <Card.Header className="bg-dark border-secondary">
                          <h6 className="mb-0 text-light">Tipos de Conexión</h6>
                        </Card.Header>
                        <Card.Body>
                          <div className="mb-2">
                            <div className="d-flex justify-content-between align-items-center mb-1">
                              <div className="d-flex align-items-center">
                                <div className="bg-danger" style={{ width: '12px', height: '2px' }}></div>
                                <span className="small text-light ms-2">Maliciosa</span>
                              </div>
                              <span className="small text-muted">8</span>
                            </div>
                          </div>
                          
                          <div className="mb-2">
                            <div className="d-flex justify-content-between align-items-center mb-1">
                              <div className="d-flex align-items-center">
                                <div className="bg-warning" style={{ width: '12px', height: '2px' }}></div>
                                <span className="small text-light ms-2">Sospechosa</span>
                              </div>
                              <span className="small text-muted">6</span>
                            </div>
                          </div>
                          
                          <div className="mb-2">
                            <div className="d-flex justify-content-between align-items-center mb-1">
                              <div className="d-flex align-items-center">
                                <div className="bg-success" style={{ width: '12px', height: '2px' }}></div>
                                <span className="small text-light ms-2">Legítima</span>
                              </div>
                              <span className="small text-muted">4</span>
                            </div>
                          </div>
                        </Card.Body>
                      </Card>
                    </Col>
                  </Row>
                </Tab.Pane>
              </Tab.Content>
            </Tab.Container>
          </Col>
          
          {/* Panel lateral de información */}
          <Col lg={3} className="border-start border-secondary p-3">
            <Card className="bg-dark border-secondary mb-3">
              <Card.Header className="bg-dark border-secondary">
                <h6 className="mb-0 text-light">Información de la Investigación</h6>
              </Card.Header>
              <Card.Body>
                <div className="small">
                  <div className="mb-2">
                    <strong className="text-muted">Estado:</strong>
                    <Badge bg="success" className="ms-2">Activa</Badge>
                  </div>
                  <div className="mb-2">
                    <strong className="text-muted">Prioridad:</strong>
                    <Badge bg="danger" className="ms-2">Alta</Badge>
                  </div>
                  <div className="mb-2">
                    <strong className="text-muted">Creada:</strong>
                    <span className="ms-2 text-light">{new Date(investigation.createdAt).toLocaleDateString()}</span>
                  </div>
                  <div className="mb-2">
                    <strong className="text-muted">Actualizada:</strong>
                    <span className="ms-2 text-light">{new Date(investigation.updatedAt).toLocaleDateString()}</span>
                  </div>
                  <div className="mb-2">
                    <strong className="text-muted">Entidades:</strong>
                    <span className="ms-2 text-light">{entities.length}</span>
                  </div>
                </div>
              </Card.Body>
            </Card>
            
            <Card className="bg-dark border-secondary">
              <Card.Header className="bg-dark border-secondary">
                <h6 className="mb-0 text-light">Acciones Rápidas</h6>
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
        className="bg-dark text-light"
        style={{ width: '400px' }}
      >
        <Offcanvas.Header closeButton className="border-bottom border-secondary">
          <Offcanvas.Title>Herramientas OSINT</Offcanvas.Title>
        </Offcanvas.Header>
        <Offcanvas.Body>
          {!selectedTool ? (
            <div>
              <h6 className="mb-3">Seleccionar Herramienta</h6>
              <div className="d-grid gap-2">
                {osintTools.map((tool) => (
                  <Card 
                    key={tool.id} 
                    className="bg-dark border-secondary cursor-pointer"
                    onClick={() => setSelectedTool(tool)}
                    style={{ cursor: 'pointer' }}
                  >
                    <Card.Body className="p-3">
                      <h6 className="text-light mb-1">{tool.name}</h6>
                      <p className="small text-muted mb-1">{tool.description}</p>
                      <Badge bg="secondary" className="small">{tool.category}</Badge>
                    </Card.Body>
                  </Card>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <div className="d-flex align-items-center justify-content-between mb-3">
                <h6 className="mb-0">{selectedTool.name}</h6>
                <Button 
                  variant="outline-secondary" 
                  size="sm" 
                  onClick={() => setSelectedTool(null)}
                >
                  <X size={14} />
                </Button>
              </div>
              
              <p className="small text-muted mb-3">{selectedTool.description}</p>
              
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
                        className="bg-dark border-secondary text-light"
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
                        className="bg-dark border-secondary text-light"
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
                        className="text-light"
                      />
                    )}
                    
                    {param.type === 'select' && param.options && (
                      <Form.Select
                        value={toolParameters[param.name] || ''}
                        onChange={(e) => setToolParameters(prev => ({
                          ...prev,
                          [param.name]: e.target.value
                        }))}
                        className="bg-dark border-secondary text-light"
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

      {/* Modal de confirmación de eliminación */}
      <Modal 
        show={!!showDeleteConfirm} 
        onHide={() => setShowDeleteConfirm(null)}
        className="text-light"
      >
        <Modal.Header closeButton className="bg-dark border-secondary">
          <Modal.Title>Confirmar Eliminación</Modal.Title>
        </Modal.Header>
        <Modal.Body className="bg-dark">
          ¿Estás seguro de que deseas eliminar esta entidad? Esta acción no se puede deshacer.
        </Modal.Body>
        <Modal.Footer className="bg-dark border-secondary">
          <Button variant="secondary" onClick={() => setShowDeleteConfirm(null)}>
            Cancelar
          </Button>
          <Button 
            variant="danger" 
            onClick={() => showDeleteConfirm && handleDeleteEntity(showDeleteConfirm)}
          >
            Eliminar
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Modal de formulario de entidad */}
      {showEntityForm && (
        <EntityForm
          entity={selectedEntity || undefined}
          investigationId={investigation.id}
          onSave={(entity) => {
            if (selectedEntity) {
              setEntities(prev => prev.map(e => e.id === entity.id ? entity : e));
            } else {
              setEntities(prev => [...prev, { ...entity, id: Date.now().toString() }]);
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
  );
};

export default InvestigationWorkspace;