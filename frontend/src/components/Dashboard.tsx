import React, { useEffect, useMemo, useState } from 'react';
import { Container, Row, Col, Card, Alert, Spinner, Badge, ProgressBar, Button } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import type { User, DashboardStats } from '../types';
import Header from './Header';
import CyberMapBackground from './CyberMapBackground';

interface ExtendedDashboardStats extends DashboardStats {
  investigationsByStatus: { [key: string]: number };
  investigationsByPriority: { [key: string]: number };
  entitiesByType: { [key: string]: number };
  systemHealth: {
    cpu: number;
    memory: number;
    storage: number;
  };
  monthlyTrends: {
    investigations: number[];
    entities: number[];
  };
}

interface DashboardProps {
  user: User;
  onLogout: () => void;
}

const Dashboard: React.FC<DashboardProps> = ({ user, onLogout }) => {
  const [stats, setStats] = useState<ExtendedDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const kpi = useMemo(() => {
    const total = stats?.totalInvestigations || 0;
    const active = stats?.activeInvestigations || 0;
    const entities = stats?.totalEntities || 0;
    const pulse = Math.max(1, Math.round((active * 9 + entities / 10) / 4));
    const risk = Math.min(99, Math.max(5, Math.round((active / Math.max(1, total)) * 100)));
    return { pulse, risk };
  }, [stats]);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    console.log('🔄 Cargando estadísticas del dashboard...');

    // Simular delay de carga
    await new Promise(resolve => setTimeout(resolve, 1000));

    try {
      // Datos mock extendidos para estadísticas
      const mockStats: ExtendedDashboardStats = {
        totalInvestigations: 24,
        activeInvestigations: 8,
        completedInvestigations: 16,
        totalEntities: 156,
        recentActivity: 12,
        investigationsByStatus: {
          active: 8,
          completed: 16,
          archived: 3,
          pending: 2
        },
        investigationsByPriority: {
          critical: 2,
          high: 5,
          medium: 12,
          low: 8
        },
        entitiesByType: {
          person: 45,
          organization: 32,
          location: 28,
          phone: 23,
          email: 18,
          ip: 15,
          domain: 12
        },
        systemHealth: {
          cpu: 65,
          memory: 78,
          storage: 45
        },
        monthlyTrends: {
          investigations: [12, 15, 18, 22, 19, 24],
          entities: [89, 102, 125, 138, 147, 156]
        }
      };

      setStats(mockStats);
      console.log('✅ Estadísticas del dashboard cargadas correctamente');
      
    } catch (err) {
      console.error('💥 Error al cargar estadísticas del dashboard:', err);
      setError('Error al cargar las estadísticas del dashboard');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, string> = {
      active: 'success',
      completed: 'primary',
      archived: 'secondary'
    };
    return variants[status] || 'secondary';
  };

  const getPriorityBadge = (priority: string) => {
    const variants: Record<string, string> = {
      low: 'success',
      medium: 'warning',
      high: 'danger',
      critical: 'danger'
    };
    return variants[priority] || 'secondary';
  };

  return (
    <div className="cybermap-shell">
      <CyberMapBackground />
      <Header user={user} onLogout={onLogout} />

      <Container fluid className="app-page py-3 cybermap-dashboard">
        {error && (
          <Alert variant="danger" className="mb-4">
            <i className="bi bi-exclamation-triangle me-2"></i>
            {error}
          </Alert>
        )}

        {loading ? (
          <div className="text-center py-5">
            <Spinner animation="border" variant="primary" />
            <p className="text-muted mt-2">Cargando dashboard...</p>
          </div>
        ) : (
          <Row className="g-2 justify-content-between align-items-start">
            <Col xl={3} lg={4}>
              <div className="cybermap-side cybermap-side--left">
                <Card className="cybermap-panel">
                  <Card.Header className="d-flex align-items-center justify-content-between">
                    <div className="fw-semibold">
                      <i className="bi bi-activity me-2"></i>
                      Telemetría
                    </div>
                    <Badge bg="success">Live</Badge>
                  </Card.Header>
                  <Card.Body>
                    <div className="d-flex align-items-center justify-content-between mb-2">
                      <div className="text-muted small">Pulsos/min</div>
                      <div className="fw-semibold">{kpi.pulse}</div>
                    </div>
                    <div className="d-flex align-items-center justify-content-between mb-2">
                      <div className="text-muted small">Riesgo</div>
                      <div className="fw-semibold">{kpi.risk}%</div>
                    </div>
                    <div className="d-flex align-items-center justify-content-between mb-2">
                      <div className="text-muted small">Investigaciones</div>
                      <div className="fw-semibold">{stats?.totalInvestigations || 0}</div>
                    </div>
                    <div className="d-flex align-items-center justify-content-between">
                      <div className="text-muted small">Entidades</div>
                      <div className="fw-semibold">{stats?.totalEntities || 0}</div>
                    </div>
                  </Card.Body>
                </Card>

                <Card className="cybermap-panel">
                  <Card.Header>
                    <div className="fw-semibold">
                      <i className="bi bi-lightning me-2"></i>
                      Acciones
                    </div>
                  </Card.Header>
                  <Card.Body className="d-grid gap-2">
                    <Link to="/investigations" className="btn btn-sm btn-outline-primary">
                      <i className="bi bi-search me-2"></i>
                      Nueva Investigación
                    </Link>
                    <Link to="/entities" className="btn btn-sm btn-outline-info">
                      <i className="bi bi-diagram-3 me-2"></i>
                      Gestionar Entidades
                    </Link>
                    <Link to="/graphs" className="btn btn-sm btn-outline-warning">
                      <i className="bi bi-diagram-2 me-2"></i>
                      Visualizar Grafos
                    </Link>
                    <Button size="sm" variant="outline-secondary" onClick={() => window.location.reload()}>
                      <i className="bi bi-arrow-clockwise me-2"></i>
                      Actualizar
                    </Button>
                  </Card.Body>
                </Card>
              </div>
            </Col>

            <Col xl={3} lg={4} className="ms-xl-auto cybermap-right">
              <div className="cybermap-side cybermap-side--right">
                <Card className="cybermap-panel">
                  <Card.Header>
                    <div className="fw-semibold">
                      <i className="bi bi-pie-chart me-2"></i>
                      Investigaciones por Estado
                    </div>
                  </Card.Header>
                  <Card.Body>
                    {Object.entries(stats?.investigationsByStatus || {}).map(([status, count]) => {
                      const total = stats?.totalInvestigations || 1;
                      const percentage = Math.round((count / total) * 100);
                      return (
                        <div key={status} className="mb-1">
                          <div className="d-flex justify-content-between align-items-center mb-1">
                            <span className="text-capitalize">
                              <Badge bg={getStatusBadge(status)} className="me-2">
                                {status === 'active' ? 'Activo' :
                                  status === 'completed' ? 'Completado' :
                                    status === 'archived' ? 'Archivado' : 'Pendiente'}
                              </Badge>
                              {count}
                            </span>
                            <small className="text-muted">{percentage}%</small>
                          </div>
                          <ProgressBar variant={getStatusBadge(status)} now={percentage} style={{ height: '5px' }} />
                        </div>
                      );
                    })}
                  </Card.Body>
                </Card>

                <Card className="cybermap-panel">
                  <Card.Header>
                    <div className="fw-semibold">
                      <i className="bi bi-exclamation-triangle me-2"></i>
                      Investigaciones por Prioridad
                    </div>
                  </Card.Header>
                  <Card.Body>
                    {Object.entries(stats?.investigationsByPriority || {}).map(([priority, count]) => {
                      const total = stats?.totalInvestigations || 1;
                      const percentage = Math.round((count / total) * 100);
                      return (
                        <div key={priority} className="mb-1">
                          <div className="d-flex justify-content-between align-items-center mb-1">
                            <span className="text-capitalize">
                              <Badge bg={getPriorityBadge(priority)} className="me-2">
                                {priority === 'critical' ? 'Crítica' :
                                  priority === 'high' ? 'Alta' :
                                    priority === 'medium' ? 'Media' : 'Baja'}
                              </Badge>
                              {count}
                            </span>
                            <small className="text-muted">{percentage}%</small>
                          </div>
                          <ProgressBar variant={getPriorityBadge(priority)} now={percentage} style={{ height: '5px' }} />
                        </div>
                      );
                    })}
                  </Card.Body>
                </Card>
              </div>
            </Col>
          </Row>
        )}
      </Container>
    </div>
  );
};

export default Dashboard;
